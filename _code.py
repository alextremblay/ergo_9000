print("Starting...")

# Import all board pins.
import board
import terminalio
import busio
import displayio
from adafruit_display_text import label
from displayio import I2CDisplay
from adafruit_displayio_ssd1306 import SSD1306

display_bus = I2CDisplay(board.I2C(), device_address=0x3c)
display = SSD1306(display_bus, width=128, height=64)

# Make the display context
splash = displayio.Group()
display.show(splash)

color_bitmap = displayio.Bitmap(128, 32, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(118, 24, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x000000  # Black
inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=5, y=4)
splash.append(inner_sprite)

# Draw a label
text = "Hello World!"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFF00, x=28, y=15)
splash.append(text_area)


from kb import Ergo9000
k = Ergo9000()
k.debug_enabled = True
k._init()
from display import *
self = k.display
rg = self.root_group
layer_group = rg[0]
mods_group = rg[1][0]
debug_group = rg[1][1]
os_group = rg[1][2]
boot_mode_group = rg[1][3]
msg_group = rg[2]