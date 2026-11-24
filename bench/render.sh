#!/usr/bin/env bash
# Re-render the README charts from their HTML sources with headless Chrome (macOS path; set CHROME elsewhere).
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
shot() { "$CHROME" --headless=new --disable-gpu --user-data-dir="$TMP/profile" --hide-scrollbars \
  --allow-file-access-from-files --virtual-time-budget=3000 "$@" >/dev/null 2>&1; }
# media/header.jpg is the announcement image, not rendered here (bench/header.html is the old header, kept for reference).
for chart in speed quality; do H=900; [ "$chart" = quality ] && H=1500; for theme in light dark; do
  sed -e "s/<html lang=\"en\">/<html lang=\"en\" data-theme=\"$theme\">/" -e 's#</head>#<style>details{display:none}</style></head>#' \
    "bench/$chart-chart.html" > "bench/_render.html"
  shot --window-size=1180,$H --force-device-scale-factor=2 --screenshot="$PWD/media/$chart-chart-$theme.png" "file://$PWD/bench/_render.html"
  rm bench/_render.html
  python3 - "media/$chart-chart-$theme.png" <<'PY'
import sys
from PIL import Image, ImageChops
f = sys.argv[1]; im = Image.open(f).convert("RGB")
bg = Image.new("RGB", im.size, im.getpixel((2, im.size[1] - 2)))
box = ImageChops.difference(im, bg).getbbox()
im.crop((0, 0, im.size[0], min(im.size[1], box[3] + 70))).save(f)
PY
done; done
echo rendered
