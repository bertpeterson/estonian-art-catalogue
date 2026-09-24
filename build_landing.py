# -*- coding: utf-8 -*-
"""Bake the landing page's first paint into site/index.html: the door of sixteen names
and the opening of the artwall, as plain HTML, so a visitor sees the catalogue before
the 20 MB index has arrived. The app renders the same view when it boots and takes the
baked tile order for its first paint (data-keys), so nothing jumps. The order is the
app's: masterpieces first, each rank slipped up to a dozen places by a seed fixed at
build time (data-seed), then the door's names and everyone else in turn.
"""
import json, re, html, time, os

d = json.load(open("data/data.json", encoding="utf-8")); A, W, V = d["artists"], d["works"], d["vocab"]
_ix = json.load(open("site/data/index.json", encoding="utf-8"))                  # r and rs live here, column by column
L = [{} for _ in range(_ix["n"])]
for _f, _c in _ix["cols"].items():
    if isinstance(_c, list):
        for _i, _v in enumerate(_c):
            if _v is not None: L[_i][_f] = _v
    else:
        _i = 0
        for _g, _v in zip(_c["i"], _c["v"]): _i += _g; L[_i][_f] = _v
I18N = json.load(open("i18n.json", encoding="utf-8"))
e = html.escape
name = lambda f, v: V[f][v] if isinstance(v, int) and f in V else v
CANON = re.search(r"const CANON = \[(.*?)\];", open("tpl_app.html", encoding="utf-8").read(), re.S).group(1)
CANON = re.findall(r'"([^"]+)"', CANON)
byname = {a["n"]: i for i, a in enumerate(A)}
canon = [byname[n] for n in CANON if n in byname]
MRANK = {"Painting": 0, "Watercolour": 1, "Sculpture": 2, "Mixed media": 3, "Installation": 3, "Drawing": 4, "Sketch": 5, "Photograph": 6, "Print": 7}

def fnv(s):
    h = 2166136261
    for c in s: h = ((h ^ ord(c)) * 16777619) & 0xFFFFFFFF
    return h
SEED = str(int(time.time()))[-6:]
key = lambda w: w.get("k") or re.sub(r"[^A-Z0-9:]", "", (w.get("nu") or "").upper())
counts = {}
for w in W: counts[w["a"]] = counts.get(w["a"], 0) + 1

# the doors
import unicodedata
def slug(n):    # the same slug build_pages.py gives the artist's page
    n = unicodedata.normalize("NFKD", n or "").encode("ascii", "ignore").decode()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", n.lower())) or "artist"
num = lambda n: f"{n:,}"
door = ('<div class="d-names"><h2>' + e(I18N["EN"]["doors_name"]) + '</h2><ul>'
        # a link each, to the artist's own page: what a crawler follows from the landing
        # page, and what a reader gets before the app is here; the app intercepts the click
        + "".join(f'<li><a href="a/{slug(A[i]["n"])}.html" data-door="a" data-v="{i}"><span>{e(A[i]["n"])}</span></a></li>' for i in canon) + "</ul></div>")

# the wall: pictured works, masterpieces first (rank slipped by the seed), then the
# door's names and the highlights, then the rest -- artists taking turns within a medium
light = {key(w): lw for w, lw in zip(W, L)}
pics = [w for w in W if w.get("im")]
pics.sort(key=lambda w: (w.get("y") is None, w.get("y") or 0))
MULTI = {"Print", "Sculpture", "Relief", "Illustration", "Bookplate", "Poster"}
seen, uniq = set(), []
for w in sorted(pics, key=lambda w: ((w.get("mp") or 10**9), (w.get("hl") if w.get("hl") is not None else 10**9))):
    ev = name("e", w.get("e"))
    if ev in MULTI or (w.get("hl") is not None and ev != "Painting"):
        k = (w["a"], re.sub(r"[\s.,;:\"'«»„“”]+", " ", w["t"].lower()).strip(), "" if w.get("hl") is not None else (w.get("y") or ""))
        if k in seen: continue
        seen.add(k)
    uniq.append(w)
turns = {}
def turn(w):
    t = turns.get(w["a"], 0); turns[w["a"]] = t + 1; return t
canon_set = set(canon)
rows = []
for i, w in enumerate(sorted(uniq, key=lambda w: (w.get("y") is None, w.get("y") or 0))):
    mp = (w["mp"] + fnv(key(w) + SEED) % 12) if w.get("mp") else 10**9
    tier = 0 if (w.get("hl") is not None or w["a"] in canon_set) else 1
    rows.append((mp, tier, turn(w), MRANK.get(name("e", w.get("e")), 8), fnv(key(w)), i, w))
rows.sort(key=lambda r: r[:6])
shown = [r[6] for r in rows[:72]]

SMALL = {k: v for k, v in (json.load(open("data/img_small.json", encoding="utf-8")) if os.path.exists("data/img_small.json") else {}).items() if v}   # data/img_small.py
def imsrc(im):
    im = SMALL.get(im, im)
    if im.startswith("m:"): return f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={im[2:]}"
    if im.startswith("e:"): return "https://digikogu.ekm.ee/static/preview/image/" + re.sub(r"/([^/]+)$", r"/t2_\1", im[2:])
    return im[2:]
cols = [{"h": 0, "t": []} for _ in range(6)]
for w in shown:
    lw = light.get(key(w), {}); r = (lw.get("r") or 100) / 100
    c = min(cols, key=lambda c: c["h"]); c["h"] += r + 0.32; c["t"].append((w, r, lw.get("rs")))
POS = {"l": "100% 50%", "r": "0% 50%", "t": "50% 100%", "b": "50% 0%"}   # the chart's side is the side cropped away
def tile(w, r, rs, j):
    lab = f'{w.get("y") if w.get("y") else "n.d."} · {e(name("mu", w["mu"]))}'
    zm = f';object-position:{POS[rs]}' if rs else ""
    # the first tile of each column loads at once; the rest as they come near the screen
    # (window.__lz in tpl_head.html), so the pictures in view and the catalogue's data
    # are not queued behind forty that are not
    src = f'src="{e(imsrc(w["im"]))}"' if j < 1 else f'src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" data-src="{e(imsrc(w["im"]))}"'
    return (f'<a class="wt" data-wt="{e(key(w))}" href="#artist={slug(A[w["a"]]["n"])}&open={e(key(w))}" title="{e(w["t"])} · {e(A[w["a"]]["n"])}">'
            f'<img {src} alt="{e(w["t"])}, {e(A[w["a"]]["n"])}" style="aspect-ratio:1/{r:.3f}{zm}" referrerpolicy="no-referrer-when-downgrade">'
            f'<span class="wt-cap"><i>{e(w["t"])}</i><span>{e(A[w["a"]]["n"])} · {lab}</span></span></a>')
npics = len(pics)
bar = I18N["EN"]["wall_line_home"].replace("{p}", f"{npics:,}") + " · " + I18N["EN"]["wall_imgs"]
wall = (f'<div class="wall" data-cols="6" data-seed="{SEED}" data-keys="{e(",".join(key(w) for w in shown))}">'
        + "".join('<div class="wcol">' + "".join(tile(*t, j) for j, t in enumerate(c["t"])) + "</div>" for c in cols) + "</div>")
json.dump({"doors": door, "register": wall, "seed": SEED}, open("site/landing.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"  landing baked   {len(shown)} tiles, seed {SEED}, first: {shown[0]['t']} · {A[shown[0]['a']]['n']}")
