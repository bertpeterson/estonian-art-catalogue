# -*- coding: utf-8 -*-
"""The colour chart in a museum photograph: which side, how wide -> chart_sides.json
{picture id: [side l|r|t|b, fraction of the width or height it takes]}

A museum's photograph often has a colour chart or a grey scale standing beside the
painting, above it or beneath it. The tiles used to guess at it from the
photograph's shape against the record's dimensions and crop to the work's shape
from the centre -- which found charts where there were none (a frame, an oval, a
sheet measured differently) and cut the painting itself, and where there was one
left half of it. This reads each museum photograph once (as the shape and
embedding reads did; nothing is kept) and looks for the chart itself: a border
band holding saturated patches of five or more distinct hues -- red, yellow,
green, cyan, blue, magenta side by side, which no painting's edge has -- is a
chart, and the band's extent along that edge is what the tile and the record crop
away. A photograph without one is shown whole.

Run deliberately, with the venv:  .venv-clip/bin/python chart_side.py   (from data/)
"""
import json, os, re, io, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
from shape_of import shape_of

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
OUT = "chart_sides.json"
W = json.load(open("data.json", encoding="utf-8"))["works"]
sides = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}

def url_of(im):
    if im.startswith("m:"): return f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={im[2:]}"
    return "https://digikogu.ekm.ee/static/preview/image/" + re.sub(r"/([^/]+)$", r"/t2_\1", im[2:])

SURPLUS = {}
for w in W:
    im, rp, rw = w.get("im"), w.get("ir"), shape_of(w.get("dm"))
    if im and rp and rw and 0.45 <= rw <= 2.2:
        if rp < rw / 1.08: SURPLUS[im] = ("x", 1 - rp / rw)      # wider than the work
        elif rp > rw * 1.08: SURPLUS[im] = ("y", 1 - rw / rp)    # taller
todo = sorted({w["im"] for w in W if str(w.get("im", ""))[:2] in ("m:", "e:") and w["im"] not in sides})
print(f"{len(sides):,} photographs read before, {len(todo):,} to read", flush=True)

BAND = 0.18          # how far in from an edge a chart is looked for
WIN, STEP = 24, 8    # a window this small holding four vivid hues, three of them cool, is a chart
def chart_windows(hsv):
    """boolean map of windows (rows, cols at STEP) that look like a colour chart: four
    or more distinct vivid hues, three of them cool, on a neutral ground, inside WIN x WIN pixels"""
    H, Wd = hsv.shape[:2]
    sat = (hsv[..., 1] > 80) & (hsv[..., 2] > 90)
    grey = hsv[..., 1] < 50                                   # the card, the grey scale, the gaps
    hue = hsv[..., 0] // 22
    rows = range(0, max(1, H - WIN + 1), STEP); cols = range(0, max(1, Wd - WIN + 1), STEP)
    out = np.zeros((len(rows), len(cols)), bool)
    for i, y in enumerate(rows):
        for j, x in enumerate(cols):
            m = sat[y:y + WIN, x:x + WIN]
            if m.sum() < 12: continue
            bins = np.bincount(hue[y:y + WIN, x:x + WIN][m].ravel(), minlength=12)
            # a painting's edge may hold four vivid hues, but not three cool ones --
            # green, cyan, blue, violet, magenta -- in a patch this small (the patches
            # of a chart in a 1,600-pixel photograph are three pixels wide here)
            # ...and a chart's patches sit on a neutral card beside a grey scale, so a
            # third of the window is unsaturated -- a meadow of flowers is not
            if (bins >= 3).sum() >= 4 and (bins[4:12] >= 3).sum() >= 3 and grey[y:y + WIN, x:x + WIN].mean() >= 0.3: out[i, j] = True
    return out, list(rows), list(cols)

def wedge_of(hsv):
    """(side, fraction) of a grey scale -- twenty steps from black to white along one
    edge, with no colour patches -- or None. A strip a few pixels thick is walked in
    from each edge; a run of unsaturated columns a fifth of the width long, whose
    values climb or fall through six or more plateaus over a range of 140, is a wedge."""
    H, Wd = hsv.shape[:2]
    best = None
    for side in "tblr":
        M = hsv if side in "tb" else hsv.transpose(1, 0, 2)          # rows along the edge
        n, m = M.shape[:2]
        if side in "br": M = M[::-1]                                   # walk in from the far edge
        lim = max(12, round(n * 0.18))
        for r0 in range(0, lim - 5, 3):
            blk = M[r0:r0 + 6]
            S, V = blk[..., 1].mean(axis=0), blk[..., 2].mean(axis=0)
            un = S < 45
            # longest run of unsaturated columns, gaps of two allowed
            runs, i = [], 0
            while i < m:
                if not un[i]: i += 1; continue
                j = i
                while j < m and (un[j] or (j + 2 < m and un[j + 1] and un[j + 2])): j += 1
                runs.append((i, j)); i = j
            if not runs: continue
            a, b = max(runs, key=lambda r: r[1] - r[0])
            if b - a < 0.2 * m: continue
            v = V[a:b]
            if v.max() - v.min() < 140: continue
            # plateaus: stretches where the value holds within six levels
            cuts = np.where(np.abs(np.diff(v)) > 6)[0]
            plateaus = np.diff(np.concatenate([[0], cuts + 1, [len(v)]]))
            steps = int((plateaus >= 3).sum())
            if steps < 6: continue
            x = np.arange(len(v)); rho = abs(np.corrcoef(x, v)[0, 1])
            if rho < 0.75: continue
            full = n
            frac = (r0 + 6 + 0.015 * full) / full
            score = steps * 10 + rho * 10
            if best is None or score > best[0]: best = (score, side, round(float(min(0.3, frac)), 3))
    return best[1:] if best else None

def chart_of(img, surplus=None):
    """(side, fraction) of a colour chart along one edge, or None. surplus, when the
    record's dimensions give it, is (axis, fraction): how much wider ('x') or taller
    ('y') the photograph is than the work -- a bound on the crop."""
    img = img.convert("RGB"); img.thumbnail((640, 640))
    hsv = np.asarray(img.convert("HSV"), dtype=np.int16)
    H, Wd = hsv.shape[:2]
    win, rows, cols = chart_windows(hsv)
    if not win.any():
        w = wedge_of(hsv)                                         # a grey scale alone
        if w and surplus and surplus[0] == ("x" if w[0] in "lr" else "y"): w = (w[0], round(min(w[1], surplus[1] + 0.02), 3))
        return w
    # The windows fall into clusters (touching windows); a chart is a cluster that lies
    # wholly within the band along one edge. A painting's own colourful passages -- the
    # shawl in Mägi's Alide Asmuse portree -- make clusters too, but in the middle, and
    # they no longer drown a chart at the top.
    lab = np.zeros(win.shape, int); nlab = 0
    for i, j in zip(*np.where(win)):
        if lab[i, j]: continue
        nlab += 1; stack = [(i, j)]; lab[i, j] = nlab
        while stack:
            a, b = stack.pop()
            for da in (-1, 0, 1):
                for db in (-1, 0, 1):
                    y2, x2 = a + da, b + db
                    if 0 <= y2 < win.shape[0] and 0 <= x2 < win.shape[1] and win[y2, x2] and not lab[y2, x2]:
                        lab[y2, x2] = nlab; stack.append((y2, x2))
    best = None
    for k in range(1, nlab + 1):
        ii, jj = np.where(lab == k)
        ys = np.array([rows[i] for i in ii]); xs = np.array([cols[j] for j in jj])
        reach = {"l": (xs.max() + WIN) / Wd, "r": 1 - xs.min() / Wd, "t": (ys.max() + WIN) / H, "b": 1 - ys.min() / H}
        side = min(reach, key=reach.get)
        if reach[side] > BAND: continue                         # in the middle: the painting's own colours
        if best is None or len(ii) > best[0]: best = (len(ii), side, xs, ys)
    if best is None: return None
    _, side, xs, ys = best
    ext = {"l": xs.max() + WIN, "r": Wd - xs.min(), "t": ys.max() + WIN, "b": H - ys.min()}[side]
    full = Wd if side in "lr" else H
    frac = (ext + 0.012 * full) / full
    if surplus and surplus[0] == ("x" if side in "lr" else "y"): frac = min(frac, surplus[1] + 0.02)
    return side, round(float(min(0.4, frac)), 3)

def one(im):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url_of(im), headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=60) as resp: b = resp.read()
            return im, chart_of(Image.open(io.BytesIO(b)), SURPLUS.get(im)) or 0
        except Exception:
            time.sleep(2 + 2 * attempt)
    return im, None

if __name__ == "__main__":
    n, t0 = 0, time.time()
    for items, workers in (([i for i in todo if i.startswith("e:")], 4), ([i for i in todo if i.startswith("m:")], 8)):
        with ThreadPoolExecutor(workers) as ex:
            for im, s in ex.map(one, items):
                if s is not None: sides[im] = s
                n += 1
                if n % 500 == 0:
                    json.dump(sides, open(OUT, "w", encoding="utf-8"))
                    print(f"  {n:,}/{len(todo):,}  {n/(time.time()-t0):.1f}/s", flush=True)
    json.dump(sides, open(OUT, "w", encoding="utf-8"))
    import collections
    print("CHART SIDES:", dict(collections.Counter(v[0] if v else "none" for v in sides.values())), f"of {len(sides):,} photographs")
