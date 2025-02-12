import board
from storage import getmount
import microcontroller
import time

from display import Display, State
from keymap import get_keymap

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC, Key, make_key
from kmk.scanners import DiodeOrientation
from kmk.modules import Module
from kmk.modules.layers import Layers
from kmk.modules.split import Split, SplitSide
from kmk.modules.serialace import SerialACE
from kmk.modules.mouse_keys import MouseKeys
from kmk.extensions import Extension
from kmk.extensions.media_keys import MediaKeys
from kmk.scheduler import create_task
from kmk.utils import Debug

debug = Debug(__name__)


board_name = str(getmount('/').label)
split_side = SplitSide.LEFT if board_name.endswith('L') else SplitSide.RIGHT


class Ergo9000(KMKKeyboard):
    col_pins = (
        board.D9,
        board.D21,
        board.D23,
        board.D20,
        board.D22,
        board.D26,
        board.D27,
        board.D28,
        board.D29,
    )
    row_pins = (
        board.D0,
        board.D1,
        board.D4,
        board.D5,
        board.D6,
        board.D7,
    )
    diode_orientation = DiodeOrientation.COLUMNS

    coord_mapping = [
        # fmt: off
         0,  1,  2,  3,  4,  5,  6,  7,  8,    54,  55,  56,  57,  58,  59,  60,  61,  62,
         9, 10, 11, 12, 13, 14, 15, 16, 17,    63,  64,  65,  66,  67,  68,  69,  70,  71,
        18, 19, 20, 21, 22, 23, 24, 25, 26,    72,  73,  74,  75,  76,  77,  78,  79,  80,
        27, 28, 29, 30, 31, 32, 33, 34, 35,    81,  82,  83,  84,  85,  86,  87,  88,  89,
        36, 37, 38, 39, 40, 41, 42, 43, 44,    90,  91,  92,  93,  94,  95,  96,  97,  98,
        45, 46, 47, 48, 49, 50, 51, 52, 53,    99, 100, 101, 102, 103, 104, 105, 106, 107,
        # fmt: on
    ]

    display: Display = None  # type: ignore
    split = Split(
        split_side=split_side, data_pin=board.D2, data_pin2=board.D3, use_pio=True
    )
    modules: list[Module] = [split, Layers({(1, 2): 3}), MouseKeys()]
    extensions: list[Extension] = [MediaKeys()]

    def __init__(self) -> None:
        if microcontroller.nvm[0] == 1:  # type: ignore
            # We are in USB write / debug mode
            self.modules.append(SerialACE())
            self.debug_enabled = True
        self.mac_mode = True
        if split_side == SplitSide.LEFT:
            self.display = Display(self)
            self.modules.append(self.display)

        make_key(names=('BOOT',), on_press=self.boot_handler)
        make_key(names=('OS',), on_press=self.os_switch_handler)
        make_key(names=('COPY',), on_press=self.handle_copy, on_release=self.handle_copy_release)
        make_key(names=('CUT',), on_press=self.handle_cut, on_release=self.handle_cut_release)
        make_key(names=('PASTE',), on_press=self.handle_paste, on_release=self.handle_paste_release)

        self.keymap = get_keymap()


    def boot_handler(self, key, keyboard: 'Ergo9000', *args):
        layers = keyboard.active_layers
        State.msg = "Rebooting..."
        if 3 in layers:
            # Adjust layer is active, boot to bootloader mode
            print("Booting to BOOTLOADER...")
            microcontroller.on_next_reset(microcontroller.RunMode.BOOTLOADER)
        else:
            if microcontroller.nvm[0] == 0:  # type: ignore
                print("Booting to USB Write Mode...")
                microcontroller.nvm[0] = 1  # type: ignore
            else:
                print("Booting to NORMAL mode...")
                microcontroller.nvm[0] = 0  # type: ignore
        create_task(lambda: microcontroller.reset(), after_ms=200)  # type: ignore

    def os_switch_handler(self, key, keyboard: 'Ergo9000', *args):
        keyboard.mac_mode = not keyboard.mac_mode
        return keyboard

    def handle_copy(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.add(KC.LGUI)
            keyboard.keys_pressed.add(KC.C)
        else:
            keyboard.keys_pressed.add(KC.LCTL)
            keyboard.keys_pressed.add(KC.C)
        return keyboard
    
    def handle_copy_release(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.remove(KC.LGUI)
            keyboard.keys_pressed.remove(KC.C)
        else:
            keyboard.keys_pressed.remove(KC.LCTL)
            keyboard.keys_pressed.remove(KC.C)
        return keyboard

    def handle_cut(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.add(KC.LGUI)
            keyboard.keys_pressed.add(KC.X)
        else:
            keyboard.keys_pressed.add(KC.LCTL)
            keyboard.keys_pressed.add(KC.X)
        return keyboard
    
    def handle_cut_release(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.remove(KC.LGUI)
            keyboard.keys_pressed.remove(KC.X)
        else:
            keyboard.keys_pressed.remove(KC.LCTL)
            keyboard.keys_pressed.remove(KC.X)
        return keyboard

    def handle_paste(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.add(KC.LGUI)
            keyboard.keys_pressed.add(KC.V)
        else:
            keyboard.keys_pressed.add(KC.LCTL)
            keyboard.keys_pressed.add(KC.V)
        return keyboard
    
    def handle_paste_release(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.remove(KC.LGUI)
            keyboard.keys_pressed.remove(KC.V)
        else:
            keyboard.keys_pressed.remove(KC.LCTL)
            keyboard.keys_pressed.remove(KC.V)
        return keyboard

    def handle_undo(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.add(KC.LGUI)
            keyboard.keys_pressed.add(KC.Z)
        else:
            keyboard.keys_pressed.add(KC.LCTL)
            keyboard.keys_pressed.add(KC.Z)
        return keyboard
    
    def handle_undo_release(self, key, keyboard: 'Ergo9000', *args):
        keyboard.hid_pending = True
        if self.mac_mode:
            keyboard.keys_pressed.remove(KC.LGUI)
            keyboard.keys_pressed.remove(KC.Z)
        else:
            keyboard.keys_pressed.remove(KC.LCTL)
            keyboard.keys_pressed.remove(KC.Z)
        return keyboard

    def go(self, *args, **kwargs) -> None:
            try:
                self._init(*args, **kwargs)
                while True:
                    self._main_loop()
            except Exception as err:
                if self.display:
                    self.display.activate_repl_view()
                import traceback

                traceback.print_exception(err)
            finally:
                debug('cleaning up...')
                self._deinit_hid()
                self.deinit()
                debug('...done')

                if not debug.enabled:
                    import supervisor

                    supervisor.reload()
