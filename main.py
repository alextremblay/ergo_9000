# ruff: noqa: E402
print("Importing modules...")
from kb import Ergo9000

print("Initializing keyboard...")
k = Ergo9000()
k.debug_enabled = True

if __name__ == '__main__':
    print("Starting main sequence...")
    k.go()