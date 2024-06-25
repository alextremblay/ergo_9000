import microcontroller
import supervisor
import storage

if microcontroller.nvm[0] == 1: # type: ignore
    print("USB write mode requested")
    supervisor.runtime.autoreload = False
    storage.enable_usb_drive()
else:
    storage.disable_usb_drive()
