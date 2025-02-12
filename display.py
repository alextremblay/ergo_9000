import board
import microcontroller
import displayio
from vectorio import Rectangle
from typing import TYPE_CHECKING
from terminalio import FONT
from displayio import I2CDisplay # type: ignore

from adafruit_display_text.label import Label
from adafruit_displayio_ssd1306 import SSD1306

from kmk.keys import KC, Key
from kmk.modules import Module
from kmk.scheduler import create_task
from kmk.utils import Debug

if TYPE_CHECKING:
    from kb import Ergo9000

debug = Debug(__name__)

BLACK = displayio.Palette(1)
BLACK[0] = 0x000000
WHITE = displayio.Palette(1)
WHITE[0] = 0xFFFFFF

BITMAP = displayio.OnDiskBitmap(open("glyphs-i.bmp", "rb"))

class State:
    layer = 0
    if microcontroller.nvm[0] == 0:  # type: ignore
        boot_mode = "RO"
    else:
        boot_mode = "RW"
    msg = ""

    # mods
    ctrl = False
    alt = False
    shift = False
    gui = False

class Glyphs:
    @staticmethod
    def create(index, x=0, y=0):
        return displayio.TileGrid(
            BITMAP,
            pixel_shader=BITMAP.pixel_shader,
            tile_width=12,
            tile_height=12,
            default_tile=index,
            x=x,
            y=y,
        )
    ctrl = 0
    alt = 1
    shift = 2
    gui = 3
    win = 4
    mac = 5
    con = 6


def outline_box(group: displayio.Group, width: int, height: int, border: int = 1):
    group.append(Rectangle(pixel_shader=WHITE, width=width, height=height, x=0, y=0))
    group.append(Rectangle(
        pixel_shader=BLACK, 
        width=width - (border * 2),
        height=height - (border * 2),
        x=border,
        y=border,
    ))

def boxed_text(
    group: displayio.Group,
    text: str,
    width: int = 128,
    border: int = 1,
    padding: int = 1,
):
    "Render a box with text in it, returning the x or y coordinates of the next box"
    text_height = 12
    # if width is specified, center the text
    text_width = (width - (padding * 2) - (border * 2)) // 6
    text = f"{text:^{text_width}}"

    height = text_height + (padding * 2) + (border * 2)
    
    outline_box(group, width, height, border)
    text_area = Label(
        font=FONT,  # type: ignore
        text=text,
        color=WHITE[0],
        x=border + padding + 3,
        y=border + padding + 6,
    )
    group.append(text_area)

def boxed_glyphs(group: displayio.Group, glyph_ids: list[int], border: int = 1, padding: int = 1):
    "Render a box with glyphs in it, returning the x or y coordinates of the next box"
    glyph_height = 12
    width = (len(glyph_ids) * 12) + (padding * 2) + (border * 2)
    height = glyph_height + (padding * 2) + (border * 2)
    
    outline_box(group, width, height, border)
    offset = border + padding
    for _id in glyph_ids:
        glyph = Glyphs.create(_id, x=offset, y=border + padding)
        offset += 12
        group.append(glyph)

def layer_text(active_layer):
    "Render the layer name"
    layer_map = {
        0: 'Base',
        1: 'Lower',
        2: 'Raise',
        3: 'Adjust',
    }
    layer_name = layer_map.get(active_layer, 'Unknown')
    return f"{layer_name:^18}"

class Display(Module):
    "Display the current layer and mods"

    def __init__(self, kb: 'Ergo9000', refresh_rate: int = 10):
        self.kb = kb
        self.refresh_rate = refresh_rate
        self.prev_state = None


    def create_layout(self):
        "CReate and return the tree of displayio.Group objects that forms the display layout"
        root_group = displayio.Group()
        layer_group = displayio.Group()
        root_group.append(layer_group)
        # Layer text width incl padding is 18 chars
        boxed_text(layer_group, "Bootup", width=128, border=4, padding=4)
        row_2 = displayio.Group(y=27)
        mods_group = displayio.Group()
        row_2.append(mods_group)
        boxed_glyphs(mods_group, [Glyphs.ctrl, Glyphs.alt, Glyphs.shift, Glyphs.gui], border=2, padding=2)
        debug_group = displayio.Group(x=52)
        row_2.append(debug_group)
        boxed_glyphs(debug_group, [Glyphs.con], border=2, padding=2)
        os_group = displayio.Group(x=68)
        row_2.append(os_group)
        boxed_glyphs(os_group, [Glyphs.mac], border=2, padding=2)
        boot_mode_group = displayio.Group(x=84)
        row_2.append(boot_mode_group)
        boxed_text(boot_mode_group, State.boot_mode, width=44, border=2, padding=2)
        root_group.append(row_2)
        msg_group = displayio.Group(y=44)
        root_group.append(msg_group)
        boxed_text(msg_group, State.msg, width=128, border=2, padding=2)
        self.root = root_group
        self.layer: Label = layer_group[-1] # type: ignore
        self.ctrl: displayio.TileGrid = mods_group[2] # type: ignore
        self.alt: displayio.TileGrid = mods_group[3] # type: ignore
        self.shift: displayio.TileGrid = mods_group[4] # type: ignore
        self.gui: displayio.TileGrid = mods_group[5] # type: ignore
        self.debug: displayio.TileGrid = debug_group[-1] # type: ignore
        self.os: displayio.TileGrid = os_group[-1] # type: ignore
        self.boot_mode: Label = boot_mode_group[-1] # type: ignore
        self.msg: Label = msg_group[-1] # type: ignore
    
    def _update_layout(self):
        "Update the display layout with the current state"
        if State.__dict__ == self.prev_state:
            return
        self.layer.text = layer_text(State.layer)
        self.ctrl.hidden = not State.ctrl
        self.alt.hidden = not State.alt
        self.shift.hidden = not State.shift
        self.gui.hidden = not State.gui
        self.debug.hidden = not debug.enabled
        if self.kb.mac_mode:
            self.os[0] = Glyphs.mac
            self.gui[0] = Glyphs.gui
        else:
            self.os[0] = Glyphs.win
            self.gui[0] = Glyphs.win
        self.boot_mode.text = State.boot_mode
        self.msg.text = State.msg
        self.prev_state = State.__dict__.copy()

    def activate_repl_view(self):
        "set the display to render circuitpython's REPL view"
        repl_view = displayio.CIRCUITPYTHON_TERMINAL  # type: ignore

        # for some reason, passing this SPECIFIC group to self.display.show() silently fails
        # it doesn't crash, it just does nothing -\_(o_o)_/-
        # assinging it to self.driver.root_group works though
        self.driver.root_group = repl_view

    # region Module methods

    def during_bootup(self, keyboard):
        displayio.release_displays()
        display_bus = I2CDisplay(board.I2C(), device_address=0x3C)
        self.driver = SSD1306(display_bus, width=128, height=64)
        self.create_layout()
        self.driver.root_group = self.root
        self._task = create_task(self._update_layout, period_ms=(1000 // self.refresh_rate))
        return

    def before_matrix_scan(self, keyboard):
        return

    def after_matrix_scan(self, keyboard: "Ergo9000"):
        '''
        update all state variables based on the current keyboard state
        '''
        State.layer = keyboard.active_layers[0]
        if KC.MEH in keyboard.keys_pressed:
            State.ctrl = State.alt = State.shift = True
        elif KC.HYPR in keyboard.keys_pressed:
            State.ctrl = State.alt = State.shift = State.gui = True
        else:
            State.ctrl = bool(keyboard.keys_pressed.intersection({KC.LCTL, KC.RCTL}))
            State.alt = bool(keyboard.keys_pressed.intersection({KC.LALT, KC.RALT}))
            State.shift = bool(keyboard.keys_pressed.intersection({KC.LSFT, KC.RSFT}))
            State.gui = bool(keyboard.keys_pressed.intersection({KC.LGUI, KC.RGUI}))
        # boot mode does not change
        # msg does not change on keypress
        return

    def process_key(self, keyboard, key, is_pressed, int_coord):
        return key

    def before_hid_send(self, keyboard):
        return

    def after_hid_send(self, keyboard):
        return

    def on_powersave_enable(self, keyboard):
        return

    def on_powersave_disable(self, keyboard):
        return

    def deinit(self, keyboard):
        displayio.release_displays()


    # endregion