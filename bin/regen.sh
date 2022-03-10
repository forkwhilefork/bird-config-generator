#!/usr/bin/sh
MYDIR="$(dirname "$(readlink -f "$0")")"
python3 $MYDIR/generate.py --config $MYDIR/../config.json --outputPath $MYDIR/../output
