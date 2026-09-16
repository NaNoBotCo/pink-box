#!/bin/bash
# Double-click this file to run the Pink Box pipeline from a numbered menu.
# The project folder is wherever this script lives, so moving the folder does not break it.
cd "$(dirname "$0")" || { echo "Cannot find the project folder."; read -p "Press return to close."; exit 1; }
PY=python3

while true; do
  echo
  echo "PINK BOX"
  echo "  1  Validate every record"
  echo "  2  Build (validate + API + search tables)"
  echo "  3  Make the website (build/site)"
  echo "  4  Everything: 1-3 then open the site"
  echo "  5  Serve the site (http://127.0.0.1:8805)"
  echo "  6  Run the tests"
  echo "  7  Refresh places from OpenStreetMap (all fifty states)"
  echo "  8  Fetch free pictures from Commons for records that name them"
  echo " 10  Refresh the USDA donut measurements"
  echo "  9  Publish: build into docs/ for the live site"
  echo "  0  Quit"
  read -p "Number: " n
  case "$n" in
    1) $PY tools/validate.py ;;
    2) $PY tools/build.py ;;
    3) $PY tools/cards.py && $PY tools/site.py ;;
    4) $PY tools/build.py && $PY tools/site.py && open "build/site/index.html" ;;
    5) $PY tools/serve.py ;;
    6) $PY -m unittest discover -s tests -v 2>&1 | tail -25 ;;
    7) $PY tools/harvest_osm.py --resume ;;
    8) $PY tools/harvest_commons.py --harvest --apply ;;
    9) ./publish.sh ;;
    10) $PY tools/fetch_usda.py ;;
    0) exit 0 ;;
    *) echo "Pick a number." ;;
  esac
done
