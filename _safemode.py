#TODO: revisit this and try to get it working
import microcontroller
import board
import keypad
import supervisor

print("Running in safe mode...")

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

if supervisor.runtime.safe_mode_reason == supervisor.SafeModeReason.PROGRAMMATIC:
    print("Press any key to reboot into normal mode...")
    keys = keypad.KeyMatrix(col_pins, row_pins)

    while True:
        event = keys.events.get()
        # event will be None if nothing has happened.
        if event:
            print("Rebooting into normal mode...")
            microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
            microcontroller.reset()
