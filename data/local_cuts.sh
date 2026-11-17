#!/bin/zsh
# Daily, on the one machine that has CLIP (launchd; CI cannot run it): the empty borders and the heads of
# the stock that came in since the last run -> gallery_trim.json, stock_heads.json. It reads the published
# data.json (origin/main), not the working tree's, touches nothing else here and commits nothing: the two
# files go out with the next push, and the build gives the new works their cuts (picture_cuts.py).
cd "$(dirname "$0")" || exit 1
echo "== $(date '+%F %T')"
tmp=$(mktemp -t museaal-data) || exit 1
trap 'rm -f "$tmp"' EXIT
git fetch -q origin main && git show origin/main:data/data.json > "$tmp" || { echo "no published data.json"; exit 1; }
MUSEAAL_DATA="$tmp" .venv-clip/bin/python gallery_trim.py || exit 1
# the heads are looked for inside the trimmed picture: the published works get today's trims first, as a build
# gives them (in the copy only)
.venv-clip/bin/python -c 'import json, sys, picture_cuts
d = json.load(open(sys.argv[1], encoding="utf-8")); picture_cuts.late(d["works"])
json.dump(d, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False)' "$tmp" || exit 1
MUSEAAL_DATA="$tmp" .venv-clip/bin/python stock_heads.py || exit 1
git status --short gallery_trim.json stock_heads.json
