import board
import microcontroller
import displayio
import vectorio
from supervisor import ticks_ms
from typing import TYPE_CHECKING
from terminalio import FONT
from adafruit_display_text.label import Label
from displayio import I2CDisplay
from adafruit_displayio_ssd1306 import SSD1306
from kmk.kmktime import ticks_diff, PeriodicTimer

from kmk.keys import KC, Key
from kmk.extensions import Extension

if TYPE_CHECKING:
    from kb import Ergo9000

BLACK = displayio.Palette(1)
BLACK[0] = 0x000000
WHITE = displayio.Palette(1)
WHITE[0] = 0xFFFFFF



class glyphs:
    bitmap = displayio.OnDiskBitmap(open("glyphs-i.bmp", "rb"))

    @classmethod
    def get_glyph(cls, index, x=0, y=0):
        if index == -1:
            return vectorio.Rectangle(
                pixel_shader=BLACK, width=12, height=12, x=x, y=y
            )
        return displayio.TileGrid(
            cls.bitmap,
            pixel_shader=cls.bitmap.pixel_shader,
            tile_width=12,
            tile_height=12,
            x=x,
            y=y,
            default_tile=index,
        )
    ctrl = 0
    alt = 1
    shift = 2
    gui = 3
    win = 4
    mac = 5
    con = 6
    blank = -1

class Display(Extension):
    "Display the current layer and mods"

    def __init__(self, kb: 'Ergo9000'):
        displayio.release_displays()
        display_bus = I2CDisplay(board.I2C(), device_address=0x3C)
        self.driver = SSD1306(display_bus, width=128, height=64)
        self.kb = kb
        self.prev_layer = 0
        self.should_render = False
        self.fallback_timer = ticks_ms()
        if microcontroller.nvm[0] == 0:  # type: ignore
            self.boot_mode = "RO"
        else:
            self.boot_mode = "RW"
        self.mac_mode = True
        self.msg = ""

        class mods:
            ctrl = False
            alt = False
            shift = False
            gui = False

        self.mods = mods
        self.timer_start = ticks_ms()
        self.powersave = False
        self.dim_period = PeriodicTimer(50)
        self.root_group = None
        self.root_group = displayio.Group()
        self.layer_group = displayio.Group()
        self.root_group.append(self.layer_group)
        # Layer text width incl padding is 18 chars
        self.render_boxed_text(self.layer_group, "Bootup", width=128, border=4, padding=4)
        row_2 = displayio.Group(y=27)
        self.mods_group = displayio.Group()
        row_2.append(self.mods_group)
        self.render_boxed_glyphs(self.mods_group, [glyphs.ctrl, glyphs.alt, glyphs.shift, glyphs.gui], border=2, padding=2)
        self.debug_group = displayio.Group(x=52)
        row_2.append(self.debug_group)
        self.render_boxed_glyphs(self.debug_group, [glyphs.con], border=2, padding=2)
        self.os_group = displayio.Group(x=68)
        row_2.append(self.os_group)
        self.render_boxed_glyphs(self.os_group, [glyphs.mac], border=2, padding=2)
        self.boot_mode_group = displayio.Group(x=84)
        row_2.append(self.boot_mode_group)
        self.render_boxed_text(self.boot_mode_group, self.boot_mode, width=44, border=2, padding=2)
        self.root_group.append(row_2)
        self.msg_group = displayio.Group(y=44)
        self.root_group.append(self.msg_group)
        self.render_boxed_text(self.msg_group, self.msg, width=128, border=2, padding=2)

    def update(self, active_layer):
        "Update the display"
        self.layer_group[-1].text = self.layer_text(active_layer)
        self.mods_group[2].hidden = not self.mods.ctrl
        self.mods_group[3].hidden = not self.mods.alt
        self.mods_group[4].hidden = not self.mods.shift
        self.mods_group[5].hidden = not self.mods.gui
        self.debug_group[-1].hidden = not self.kb.debug_enabled
        self.os_group[-1][0] = glyphs.mac if self.kb.mac_mode else glyphs.win
        self.msg_group[-1].text = self.msg
        self.driver.show(self.root_group)

    # region Extension methods

    def during_bootup(self, keyboard):
        self.driver.show(self.root_group)


    def on_runtime_enable(self, keyboard):
        pass

    def on_runtime_disable(self, keyboard):
        pass

    def before_matrix_scan(self, keyboard):
        if self.dim_period.tick():
            self.dim()

    def after_matrix_scan(self, keyboard):
        active_layer = keyboard.active_layers[0]
        if keyboard.matrix_update or keyboard.secondary_matrix_update:
            self.timer_start = ticks_ms()
        # We don't want to render after every matrix scan, as that would produce significant lag
        if active_layer != self.prev_layer:
            self.prev_layer = active_layer
            self.update(active_layer)
        else:
            # the above logic *should* capture all instances where we need to render
            # but just in case, we'll render every half second
            if ticks_ms() - self.fallback_timer > 100:
                self.fallback_timer = ticks_ms()
                self.update(active_layer)

    def before_hid_send(self, keyboard):
        pass

    def after_hid_send(self, keyboard):
        pass

    def on_powersave_enable(self, sandbox):
        pass

    def on_powersave_disable(self, sandbox):
        pass

    
    def dim(self):
        "Dim the display after 20s"
        if (
            ticks_diff(ticks_ms(), self.timer_start) > 20_000
        ):
            self.driver.brightness = 0.1

        else:
            self.driver.brightness = 0.8
            self.driver.wake()


    # endregion
    #!SECTION Display methods

    def activate_repl_view(self):
        "set the display to render circuitpython's REPL view"
        repl_view = displayio.CIRCUITPYTHON_TERMINAL  # type: ignore

        # for some reason, passing this SPECIFIC group to self.display.show() silently fails
        # it doesn't crash, it just does nothing -\_(o_o)_/-
        # assinging it to self.driver.root_group works though
        self.driver.root_group = repl_view
        self.driver.show(repl_view)


    def render_box(self, group: displayio.Group, x: int, y: int, width: int, height: int, border: int = 1):
        white_box = vectorio.Rectangle(
            pixel_shader=WHITE, width=width, height=height, x=x, y=y
        )
        group.append(white_box)
        inset_black_box = vectorio.Rectangle(
            pixel_shader=BLACK,
            width=width - (border * 2),
            height=height - (border * 2),
            x=x + border,
            y=y + border,
        )
        group.append(inset_black_box)

    def render_boxed_text(
        self,
        group: displayio.Group,
        text: str,
        x: int = 0,
        y: int = 0,
        width: int = None,  # type: ignore
        border: int = 1,
        padding: int = 1,
    ):
        "Render a box with text in it, returning the x or y coordinates of the next box"
        text_height = 12
        if width is None:
            width = (len(text) * 6) + (padding * 2) + (border * 2)
        else:
            # if width is specified, center the text
            text_width = (width - (padding * 2) - (border * 2)) // 6
            text = f"{text:^{text_width}}"

        height = text_height + (padding * 2) + (border * 2)
        
        self.render_box(group, x, y, width, height, border)
        text_area = Label(
            font=FONT,  # type: ignore
            text=text,
            color=WHITE[0],
            x=x + border + padding + 3,
            y=y + border + padding + 6,
        )
        group.append(text_area)

        width = x + width
        height = y + height
        return width, height
    
    def render_boxed_glyphs(self, group: displayio.Group, glyph_ids: list[int], border: int = 1, padding: int = 1):
        "Render a box with glyphs in it, returning the x or y coordinates of the next box"
        glyph_height = 12
        width = (len(glyph_ids) * 12) + (padding * 2) + (border * 2)
        height = glyph_height + (padding * 2) + (border * 2)
        
        self.render_box(group, 0, 0, width, height, border)
        offset = border + padding
        for _id in glyph_ids:
            glyph = glyphs.get_glyph(_id, x=offset, y=border + padding)
            offset += 12
            group.append(glyph)

        return width, height
        
    def layer_text(self, active_layer):
        "Render the layer name"
        layer_map = {
            0: 'Base',
            1: 'Lower',
            2: 'Raise',
            3: 'Adjust',
        }
        layer_name = layer_map.get(active_layer, 'Unknown')
        return f"{layer_name:^18}"


    # region Mod handling

    @property
    def ctrl(self):
        return not self.mods_group[2].hidden
    
    @ctrl.setter
    def ctrl(self, value):
        self.mods.ctrl = value
        self.mods_group[2].hidden = not value

    @property
    def alt(self):
        return not self.mods_group[3].hidden
    
    @alt.setter
    def alt(self, value):
        self.mods.alt = value
        self.mods_group[3].hidden = not value

    @property
    def shift(self):
        return not self.mods_group[4].hidden
    
    @shift.setter
    def shift(self, value):
        self.mods.shift = value
        self.mods_group[4].hidden = not value

    @property
    def gui(self):
        return not self.mods_group[5].hidden
    
    @gui.setter
    def gui(self, value):
        self.mods.gui = value
        # glyphs.gui is the mac command symbol, glyphs.win is the windows key
        self.mods_group[5][0] = glyphs.gui if self.mac_mode else glyphs.win
        self.mods_group[5].hidden = not value

    @property
    def debug(self):
        return not self.debug_group[-1].hidden
    
    @debug.setter
    def debug(self, value):
        self.debug_group[-1].hidden = not value

    @property
    def os_mode(self):
        return not self.os_group[-1].hidden
    
    @os_mode.setter
    def os_mode(self, value):
        self.os_group[-1][0] = glyphs.mac if value else glyphs.win

    def handle_mods(self, key: Key, keyboard: 'Ergo9000', pressed: bool, *args):
        "Update the mods display"
        if key in [KC.LSFT, KC.RSFT]:
            self.shift = pressed
        elif key in [KC.LCTL, KC.RCTL]:
            self.ctrl = pressed
        elif key in [KC.LALT, KC.RALT]:
            self.alt = pressed
        elif key in [KC.LGUI, KC.RGUI]:
            self.gui = pressed
        elif key == KC.MEH:
            self.shift = self.ctrl = self.alt = pressed
        elif key == KC.HYPR:
            self.shift = self.ctrl = self.alt = self.gui = pressed
        return True

    # endregion
