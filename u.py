# utility functions, used in the REPL
import microcontroller
from kb import Ergo9000


def reboot():
    microcontroller.nvm[0] = 1  # tell boot.py to enable USB drive  # type: ignore
    microcontroller.reset()


def safe_mode():
    microcontroller.nvm[0] = 0  # tell boot.py to boot normally  # type: ignore
    microcontroller.reset()


_kb = None


def kb():
    global _kb
    if _kb is None:
        _kb = Ergo9000()
    return _kb


import displayio
import time

glyphs = displayio.OnDiskBitmap(open("glyphs-i.bmp", "rb"))


def tile(index):
    return displayio.TileGrid(
        glyphs,
        pixel_shader=glyphs.pixel_shader,
        tile_width=12,
        tile_height=12,
        default_tile=index,
    )


ctrl = tile(0)
alt = tile(1)
shift = tile(2)
gui = tile(3)
win = tile(4)
mac = tile(5)
con = tile(6)


k = kb()
g = displayio.Group()
g.append(displayio.Group())
k.display.driver.root_group = g

# Loop through each sprite in the sprite sheet
import time
k.display.render(0)
time.sleep(1)
k.display.mods.ctrl = True
k.display.render(0)
time.sleep(1)
k.display.mods.alt = True
k.display.render(0)
time.sleep(1)
k.display.mods.shift = True
k.display.render(0)
time.sleep(1)
k.display.mods.gui = True
k.display.render(0)
time.sleep(1)
k.display.mac_mode = True
k.display.render(0)
time.sleep(1)
k.display.mac_mode = False
k.display.render(0)
time.sleep(1)
k.display.msg = "Hello, world!"
k.display.render(0)
time.sleep(5)
