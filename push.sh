#!/usr/bin/env bash

for board in BFO9000L BFO9000R; do

    target="/Volumes/$board"

    if [ ! -d "$target" ]; then
        echo "Target $target does not exist, skipping $board"
        continue
    fi

    rsync -rvhu --exclude kle_to_keymap.py lib kmk_firmware/.compiled/kmk *.bmp ./*.py $target
    cp _typing.py $target/typing.py

    echo "Done $target"

done