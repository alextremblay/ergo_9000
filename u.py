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