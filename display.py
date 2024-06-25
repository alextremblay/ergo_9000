import board
import microcontroller
import displayio
import vectorio
from supervisor import ticks_ms
from typing import TYPE_CHECKING
from terminalio import FONT
from adafruit_display_text.label import Label
from kmk.extensions.display import Display as Base
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
        self.display = SSD1306(display_bus, width=128, height=64)
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

    # region Extension methods

    def during_bootup(self, keyboard):
        self.render(0)

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
            self.should_render = True
        if self.should_render:
            self.render(active_layer)
            self.should_render = False
        else:
            # the above logic *should* capture all instances where we need to render
            # but just in case, we'll render every half second
            if ticks_ms() - self.fallback_timer > 500:
                self.fallback_timer = ticks_ms()
                self.render(active_layer)

    def before_hid_send(self, keyboard):
        pass

    def after_hid_send(self, keyboard):
        pass

    def on_powersave_enable(self, sandbox):
        pass

    def on_powersave_disable(self, sandbox):
        pass

    
    def dim(self):
        "Dim the display after 20s, turn it off after 60s"
        if (
            ticks_diff(ticks_ms(), self.timer_start) > 60_000
        ):
            self.display.sleep()

        elif (
            ticks_diff(ticks_ms(), self.timer_start) > 20_000
        ):
            self.display.brightness = 0.1

        else:
            self.display.brightness = 0.8
            self.display.wake()


    # endregion
    #!SECTION Display methods

    def activate_repl_view(self):
        "set the display to render circuitpython's REPL view"
        repl_view = displayio.CIRCUITPYTHON_TERMINAL  # type: ignore

        # for some reason, passing this SPECIFIC group to self.display.show() silently fails
        # it doesn't crash, it just does nothing -\_(o_o)_/-
        # assinging it to self.display.root_group works though
        self.display.root_group = repl_view
        self.display.show(repl_view)

    def render(self, active_layer):
        "Render the display"
        group = displayio.Group()
        _, y = self.render_layer(group, active_layer)
        _, y = self.render_icon_bar(group, y=y)
        self.render_msg(group, y=y)
        self.display.show(group)

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
        x: int,
        y: int,
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

        new_x = x + width
        new_y = y + height
        return new_x, new_y
    
    def render_boxed_glyphs(self, group: displayio.Group, glyph_ids: list[int], x: int, y: int, border: int = 1, padding: int = 1):
        "Render a box with glyphs in it, returning the x or y coordinates of the next box"
        box = displayio.Group(x=x, y=y)
        glyph_height = 12
        width = (len(glyph_ids) * 12) + (padding * 2) + (border * 2)
        height = glyph_height + (padding * 2) + (border * 2)
        
        self.render_box(box, 0, 0, width, height, border)
        offset = border + padding
        for _id in glyph_ids:
            glyph = glyphs.get_glyph(_id, x=offset, y=y + border + padding)
            offset += 12
            box.append(glyph)

        new_x = x + width
        new_y = y + height
        group.append(box)
        return new_x, new_y
        
    def render_layer(self, group: displayio.Group, active_layer):
        "Render the layer name"
        layer_map = {
            0: 'Base',
            1: 'Lower',
            2: 'Raise',
            3: 'Adjust',
        }
        layer_name = layer_map.get(active_layer, 'Unknown')
        return self.render_boxed_text(
            group, layer_name, 0, 0, width=128, border=4, padding=4
        )

    def render_icon_bar(self, group: displayio.Group, x: int = 0, y: int = 32):
        "render a series of icons for the current mods and boot mode"
        # draw a row of boxes for all the different status icons
        icon_bar = displayio.Group(x=x, y=y)
        x, _ = self.render_boxed_glyphs(icon_bar, [self.ctrl, self.alt, self.shift, self.gui], x, 0)
        for icon in [self.debug, self.os_mode]:
            x, _ = self.render_boxed_glyphs(icon_bar, [icon], x, y=0)

        # draw the boot mode
        remaining_width = 128 - x
        x, y_offset = self.render_boxed_text(
            icon_bar, self.boot_mode, x, 0, width=remaining_width
        )
        group.append(icon_bar)
        return x, y+y_offset

    def render_msg(self, group: displayio.Group, x: int = 0, y: int = 32):
        "Render the status msg"
        return self.render_boxed_text(group, self.msg, x, y, width=128)

    # region Mod handling

    @property
    def ctrl(self):
        return glyphs.ctrl if self.mods.ctrl else glyphs.blank

    @property
    def alt(self):
        return glyphs.alt if self.mods.alt else glyphs.blank

    @property
    def shift(self):
        return glyphs.shift if self.mods.shift else glyphs.blank

    @property
    def gui(self):
        # glyphs.gui is the mac command symbol, glyphs.win is the windows key
        if self.mods.gui:
            return glyphs.gui if self.mac_mode else glyphs.win
        else:
            return glyphs.blank

    @property
    def debug(self):
        return glyphs.con if self.kb.debug_enabled else glyphs.blank

    @property
    def os_mode(self):
        return glyphs.mac if self.kb.mac_mode else glyphs.win

    def handle_mods(self, key: Key, keyboard: 'Ergo9000', pressed: bool, *args):
        "Update the mods display"
        if key in [KC.LSFT, KC.RSFT]:
            self.mods.shift = pressed
        elif key in [KC.LCTL, KC.RCTL]:
            self.mods.ctrl = pressed
        elif key in [KC.LALT, KC.RALT]:
            self.mods.alt = pressed
        elif key in [KC.LGUI, KC.RGUI]:
            self.mods.gui = pressed
        elif key == KC.MEH:
            self.mods.shift = self.mods.ctrl = self.mods.alt = pressed
        elif key == KC.HYPR:
            self.mods.shift = self.mods.ctrl = self.mods.alt = self.mods.gui = pressed

        self.should_render = True
        return True

    # endregion
