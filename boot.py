import microcontroller
import board
from kmk.bootcfg import bootcfg

storage = False
cdc_data = False
cdc_console = False

if microcontroller.nvm[0] == 1: # type: ignore
    print("USB write mode requested")
    storage = True
    cdc_data = True
    cdc_console = True

bootcfg(
    sense=board.D9, # first column pin
    source=board.D0, # first row pin
    autoreload=False,
    cdc_console=cdc_console,
    cdc_data=cdc_data,
    storage=storage,
    usb_id=('KMK Keyboards', 'Ergo9000')
)