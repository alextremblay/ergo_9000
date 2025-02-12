# ruff: noqa: E402
print("Importing modules...")
from kb import Ergo9000

print("Initializing keyboard...")
k = Ergo9000()

if __name__ == '__main__':
    print("Starting main sequence...")
    k.go()
