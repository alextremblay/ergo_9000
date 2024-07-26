#!/usr/bin/env python3
"""
This tool takes in a http://www.keyboard-layout-editor.com/ JSON file and outputs a keymap.py file.
Legends on corners are used to indicate layers, and legends on keys are used to indicate keycodes.
This current implementation is designed for QMK-style "TRI-LAYER" keymaps (aka combo layers), 
where the layer names are assumed to be "base", "lower", "raise", and "adjust".
for each key in KLE:
the bottom-left legend is mapped to the "base" layer,
the bottom-right legend is mapped to the "lower" layer,
the top-left legend is mapped to the "raise" layer, 
the top-right legend is mapped to the "adjust" layer,
"""
import json
from pathlib import Path
from textwrap import dedent
import sys
import subprocess
import pprint

import requests

token = subprocess.run('pass show github-gist-token'.split(), capture_output=True, text=True).stdout.strip()

def get_gist(gist_id):
    url = f'https://api.github.com/gists/{gist_id}'
    r = requests.get(url, headers={'Authorization': f'token {token}'})
    r.raise_for_status()
    return r.json()

kle_data = get_gist('243f9603668444a00b277037db219554')['files']['BFO-9000.kbd.json']['content']


def calculate_row_width():
    for row in json.loads(kle_data):
        if not isinstance(row, list):
            continue
        return len([key for key in row if isinstance(key, str)])
    raise ValueError('Could not determine row width')

row_width = calculate_row_width()

tmpdir = Path('/tmp/kle_to_keymap')
tmpdir.mkdir(exist_ok=True)
tmpdir.joinpath('package.json').write_text(dedent("""
    {
    "name": "kle-parser",
    "version": "1.0.0",
    "main": "index.js",
    "scripts": {
        "index.js": "node index.js"
    },
    "dependencies": {
        "@ijprest/kle-serial": "^0.15.1"
    }
    }
    """))
tmpdir.joinpath('index.js').write_text(dedent("""
    var kle = require("@ijprest/kle-serial");
    var fs = require('fs');
    var data = fs.readFileSync(0, 'utf-8');
    var keyboard = kle.Serial.parse(data);

    console.log(JSON.stringify(keyboard.keys));
    """))

try:
    if not tmpdir.joinpath('node_modules').exists():
        subprocess.run(["npm", "install"], check=True, cwd=tmpdir)
    normalized_json = subprocess.run(
        ["npm", "run", "index.js"],
        input=kle_data,
        capture_output=True,
        text=True,
        check=True,
        cwd=tmpdir,
    ).stdout
    normalized_json = normalized_json.splitlines()[-1]
except subprocess.CalledProcessError as e:
    print(e.stderr)
    sys.exit(1)

keys = json.loads(normalized_json)

keys = (key['labels'] for key in keys)

def normalize_labels(keys):
    for key in keys:
        # pad each list of labels out to 12 elements
        key.extend([''] * (12 - len(key)))
        # replace each None with an empty string
        key = [x if x is not None else '' for x in key]
        yield key

keys = normalize_labels(keys)

layer_map = {
    # maps layer names to the legend index from which they pull their keys
    # legends are indexed as follows:
    # +-----------+
    # | 0 | 1 | 2 | Top row
    # | 3 | 4 | 5 | Middle row
    # | 6 | 7 | 8 | Bottom row
    # | 9 |10 |11 | Front face
    # +-----------+
    'base': 4, # center legend 
    'lower': 6, # bottom-left legend
    'raise': 2, # top-right legend
    'adjust': 8, # bottom-right legend
}

layers = {
    "base": [],
    "lower": [],
    "raise": [],
    "adjust": [],
}
        

def map_key(lkey, layer, index, extra_info):
    """Map each key string from KLE into a valid KC keycode"""
    _row_offset = index % row_width
    if _row_offset <= (row_width / 2):
        # left hand
        side = "L"
    else:
        # right hand
        side = "R"
    match lkey:
        case "":
            if layer == 'base':
                return "NO"
            else:
                return "TRNS"
        case "Lower":
            return "MO(1)"
        case "Raise":
            return "MO(2)"
        case "Dbg":
            return "DEBUG"
        case "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "0":
            # the only difference in kle between numpad and regular numbers is that
            # numpad numbers are in the first 3 columns of a given row, and regular
            # numbers are not
            if 'numpad' in extra_info:
                return f"KP_{lkey}"
            return f"N{lkey}"
        case "Ctrl" | "Control" | "⌃" | "^":
            return f"{side}CTL"
        case "Alt" | "Option" | "Opt" | "⌥":
            return f"{side}ALT"
        case "Shift" | "⇧" | "⇪":
            return f"{side}SFT"
        case "GUI" | "Cmd" | "⌘" | "Win" | "❖":
            return f"{side}GUI"
        case "Hyper" | "⌃⌥⇧⌘" | "✦" | "✧":
            return "HYPR"
        case "Meh" | "⌃⌥⇧" | "◆":
            return "MEH"
        case "App" | "Menu" | "▤" | "☰":
            return "APP"
        case "Tab" | "⇥" | "↹":
            return "TAB"
        case "Bksp" | "⌫":
            return "BSPC"
        case "Del" | "⌦":
            return "DEL"
        case "Enter" | "⏎" | "↩":
            if 'numpad' in extra_info:
                return 'PENT' # KP_ENTER
            return "ENTER"
        case "Esc" | "⎋":
            return "ESC"
        case "Space" | "␣":
            return "SPC"
        case "PgUp" | "⇞":
            return "PGUP"
        case "PgDn" | "⇟":
            return "PGDN"
        case "Home" | "↖" | "⤒":
            return "HOME"
        case "End" | "↘" | "⤓":
            return "END"
        case "Left" | "←" | "⇠":
            return "LEFT"
        case "Right" | "→" | "⇢":
            return "RIGHT"
        case "Up" | "↑" | "⇡":
            return "UP"
        case "Down" | "↓" | "⇣":
            return "DOWN"
        case "-":
            if 'numpad' in extra_info:
                return "PMNS" # KP_MINUS
            return "MINS"
        case "=":
            if 'numpad' in extra_info:
                return "PEQL" # KP_EQUAL
            return "EQL"
        case "[":
            return "LBRC"
        case "]":
            return "RBRC"
        case "\\":
            return "BSLS"
        case ";":
            return "SCLN"
        case "'":
            return "QUOT"
        case ",":
            return "COMM"
        case ".":
            if 'numpad' in extra_info:
                return "PDOT" # KP_DOT
            return "DOT"
        case "`":
            return "GRV"
        case "/":
            if 'numpad' in extra_info:
                return "PSLS" # KP_SLASH
            return "SLSH"
        case "PrtSc":
            return "PSCR"
        case "Reset":
            return "RST"
        # ANSI Shifted Symbols
        case "~":
            return "TILD"
        case "!":
            return "EXLM"
        case "@":
            return "AT"
        case "#":
            return "HASH"
        case "$":
            return "DLR"
        case "%":
            return "PERC"
        case "^":
            return "CIRC"
        case "&":
            return "AMPR"
        case "*":
            if 'numpad' in extra_info:
                return "PAST" # KP_ASTERISK
            return "ASTR"
        case "(":
            return "LPRN"
        case ")":
            return "RPRN"
        case "_":
            return "UNDS"
        case "+":
            if 'numpad' in extra_info:
                return "PPLS" # KP_PLUS
            return "PLUS"
        case "{":
            return "LCBR"
        case "}":
            return "RCBR"
        case "|":
            return "PIPE"
        case ":":
            return "COLN"
        case '"':
            return "DQUO"
        case "<":
            return "LABK"
        case ">":
            return "RABK"
        case "?":
            return "QUES"

        # Media Keys
        case "Mute" | "🔇" | "":
            return "MUTE"
        case "Vol-" | "🔉" | "":
            return "VOLD"
        case "Vol+" | "🔊" | "":
            return "VOLU"
        case "Play" | "▶" | "⏯":
            return "MPLY"
        case "Stop" | "⏹":
            return "MSTP"
        case "Prev" | "⏮":
            return "MPRV"
        case "Next" | "⏭":
            return "MNXT"
        case "Rew" | "⏪":
            return "MREW"
        case "Ffwd" | "⏩":
            return "MFFD"
        case "Eject" | "⏏":
            return "EJCT"
        case "🔅":
            return "BRID"
        case "🔆":
            return "BRIU"
        case "Workspace Next" | "⇸": 
            return "WSP_NXT"
        case "Workspace Prev" | "⇷":
            return "WSP_PRV"
        case "Display Next" | "⇻":
            return "DSP_NXT"
        case "Display Prev" | "⇺":
            return "DSP_PRV"
        case "Mission Control" | "⑆":
            return "MSN_CTL"
        case "Cut" | "":
            return "CUT"
        case "Copy" | "":
            return "COPY"
        case "Paste" | "":
            return "PASTE"
        case _:
            # as a fallback, and KMK keycode can be specficied directly
            return lkey.upper()


for index, labels in enumerate(keys):
    for layer in layer_map:
        key = labels[layer_map[layer]]
        extra_info = labels[11]
        key = map_key(key, layer, index, extra_info=extra_info)
        layers[layer].append(key)

# Now we render this data into a keymap.py file
layers_s = "\n"
for layer in layers:
    layers_s += f"        [ # {layer}\n"
    for index, key in enumerate(layers[layer]):
        _row_offset = index % row_width
        if _row_offset == 0:
            layers_s += "            "
        if _row_offset == (row_width / 2):
            layers_s += "            "
        if key == "TRNS":
            layers_s += "___,      "
        elif key in ["WSP_NXT", "WSP_PRV", "DSP_NXT", "DSP_PRV", "MSN_CTL"]:
            layers_s += "{:10}".format(f"{key}, ")
        else:
            layers_s += "{:10}".format(f"KC.{key}, ")
        if _row_offset == row_width-1:
            layers_s += "\n"
    layers_s += "        ],\n"
keymap_s = f"""
from kmk.keys import KC

def get_keymap():
    ___ = KC.TRNS
    WSP_NXT = KC.HYPR(KC.RIGHT)
    WSP_PRV = KC.HYPR(KC.LEFT)
    DSP_NXT = KC.MEH(KC.RIGHT)
    DSP_PRV = KC.MEH(KC.LEFT)
    MSN_CTL = KC.HYPR(KC.UP)
    return [
        # fmt: off
        {layers_s}
        # fmt: on
    ]
"""
Path('keymap.py').write_text(keymap_s)
print("Done!")
