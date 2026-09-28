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

Since 2026-09-28 a second reading comes first: a strip of large solid patches along
an edge (Kodak's Color Control Patches, a Farbkarte), which the small windows missed,
with the crop walked on through its ruler and card; and a cluster of windows needs four
of them, which ended the crops of paintings that had no chart. `--all` reads every
photograph again after such a change.

Run deliberately (numpy, Pillow):  python3 chart_side.py [--all]   (from data/; monthly in the workflow)
"""
import json, os, re, io, time, urllib.request, urllib.parse
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image
from shape_of import shape_of

UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
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
import sys
REDO = "--all" in sys.argv        # read every photograph again (after a change to the rules below)
todo = sorted({w["im"] for w in W if str(w.get("im", ""))[:2] in ("m:", "e:") and (REDO or w["im"] not in sides)})
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
    # some museums serve a thumbnail of 200 pixels (Tartu Art Museum's Johani); its
    # chart is a few pixels of each hue, and the counts are read with that in mind
    small = max(H, Wd) < 400
    px, cool_n = (2, 2) if small else (3, 3)
    rows = range(0, max(1, H - WIN + 1), STEP); cols = range(0, max(1, Wd - WIN + 1), STEP)
    out = np.zeros((len(rows), len(cols)), bool)
    for i, y in enumerate(rows):
        for j, x in enumerate(cols):
            m = sat[y:y + WIN, x:x + WIN]
            if m.sum() < (6 if small else 12): continue
            bins = np.bincount(hue[y:y + WIN, x:x + WIN][m].ravel(), minlength=12)
            # a painting's edge may hold four vivid hues, but not three cool ones --
            # green, cyan, blue, violet, magenta -- in a patch this small (the patches
            # of a chart in a 1,600-pixel photograph are three pixels wide here)
            # ...and a chart's patches sit on a neutral card beside a grey scale, so a
            # third of the window is unsaturated -- a meadow of flowers is not
            if (bins >= px).sum() >= 4 and (bins[4:12] >= px).sum() >= cool_n and grey[y:y + WIN, x:x + WIN].mean() >= 0.3: out[i, j] = True
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

def strip_of(hsv, band=0.18, cw=12, step=3):
    """(side, fraction) of a strip of large colour patches along an edge -- Kodak's Color
    Control Patches, a Farbkarte's row -- or None. The windows above look for many hues in
    a small square, and a strip's patches are each wider than the square: a column of
    solid squares beside Mägi's Norra maastik (Tartu Art Museum) went unseen, while the
    painting's own dotted brushwork read as a chart. A narrow column, walked in from each
    edge, is read row by row: a row of one pure vivid hue belongs to a patch, a run of such
    rows is a patch, and four or more patches of distinct hues (two of them green to
    violet), end to end, are a strip. A painting's edge has vivid rows, but not solid ones."""
    best = None
    for side in "lrtb":
        M = hsv if side in "lr" else hsv.transpose(1, 0, 2)          # rows run along the edge
        n_along, n_across = M.shape[:2]
        lim = int(n_across * band)
        for k in range(0, max(1, lim - cw), step):
            x0 = k if side in "lt" else n_across - k - cw
            c = M[:, x0:x0 + cw]
            viv = (c[..., 1] > 80) & (c[..., 2] > 90)
            # per row: the vivid pixels' hue counts in twelve bins, all rows at once
            oh = (c[..., 0] // 22)[..., None] == np.arange(12)                  # (rows, cw, 12)
            bn = (oh & viv[..., None]).sum(axis=1)                               # (rows, 12)
            nv = viv.sum(axis=1)
            pure = (bn + np.roll(bn, 1, axis=1) + np.roll(bn, -1, axis=1)).max(axis=1) >= 0.85 * nv   # magenta sits on a bin's edge
            ok = (nv / cw >= 0.75) & pure
            ang = c[..., 0] * (2 * np.pi / 256)
            sn, cs = (np.sin(ang) * viv).sum(axis=1), (np.cos(ang) * viv).sum(axis=1)
            mh = np.where(ok, (np.degrees(np.arctan2(sn / np.maximum(nv, 1), cs / np.maximum(nv, 1))) + 360) % 360, -1.0)
            runs, r = [], 0                                   # runs of one hue: patches
            while r < n_along:
                if mh[r] < 0: r += 1; continue
                s0 = r
                while r < n_along and mh[r] >= 0 and min(abs(mh[r] - mh[s0]), 360 - abs(mh[r] - mh[s0])) < 12: r += 1
                if r - s0 >= max(4, 0.012 * n_along):
                    ang = np.radians(mh[s0:r]); runs.append((s0, r, (np.degrees(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) + 360) % 360))
            if len(runs) < 4: continue
            chain, top = [runs[0]], []                        # patches end to end
            for p, q in zip(runs, runs[1:]):
                if q[0] - p[1] <= max(6, 0.03 * n_along): chain.append(q)
                else:
                    if len(chain) > len(top): top = chain
                    chain = [q]
            if len(chain) > len(top): top = chain
            dist = []                                         # hues 25 degrees or more apart
            for h in sorted(x[2] for x in top):
                if all(min(abs(h - d), 360 - abs(h - d)) >= 25 for d in dist): dist.append(h)
            if len(dist) >= 4 and sum(1 for h in dist if 75 <= h <= 330) >= 2:
                frac = (k + cw) / n_across                    # the strip's innermost column so far
                if best is None: best = (side, frac)
                elif best[0] == side: best = (side, max(best[1], frac))
    return best

def walk_card(hsv, side, frac, extra=0.12):
    """from a strip's inner edge, on inwards through its card, for at most `extra` more of
    the picture: rows along the edge that are card (unsaturated and very dark or very
    light, or colourless: the ruler, the grey steps, a black holder), a row of pale patches
    (the Farbkarte's pastel row), or a solid bar darker than paper (its olive label strip,
    its ruler). A drawing's sheet is none of these, and is not walked into."""
    M = hsv if side in "lr" else hsv.transpose(1, 0, 2)
    n_along, n_across = M.shape[:2]
    k = int(frac * n_across); last = k; miss = 0
    while k < min(n_across - 1, int((frac + extra) * n_across)) and miss <= 8:
        col = M[:, k if side in "lt" else n_across - 1 - k]; S_, V_ = col[:, 1], col[:, 2]
        card = (((S_ < 60) & ((V_ < 70) | (V_ > 215))) | (S_ < 12)).mean() >= 0.8
        tint = S_ > 30; patches = False
        if tint.mean() >= 0.5:
            bn = np.bincount(col[:, 0][tint] // 22, minlength=12)
            patches = (bn >= 0.08 * tint.sum()).sum() >= 4
        mv, ms = np.median(V_), np.median(S_)
        bar = mv < 170 and ((np.abs(V_ - mv) < 16) & (np.abs(S_ - ms) < 16)).mean() >= 0.8
        if card or patches or bar: last = k + 1; miss = 0
        else: miss += 1
        k += 1
    return last / n_across

def chart_of(img, surplus=None):
    """(side, fraction) of a colour chart along one edge, or None. surplus, when the
    record's dimensions give it, is (axis, fraction): how much wider ('x') or taller
    ('y') the photograph is than the work -- a bound on the crop."""
    img = img.convert("RGB"); img.thumbnail((640, 640))
    hsv = np.asarray(img.convert("HSV"), dtype=np.int16)
    H, Wd = hsv.shape[:2]
    bound = lambda side, f: min(f, surplus[1] + 0.02) if surplus and surplus[0] == ("x" if side in "lr" else "y") else f
    # a strip of large patches first: the surest sign
    st = strip_of(hsv)
    if st:
        f = walk_card(hsv, *st) + 0.012
        # where the record's dimensions say how much more the photograph holds than the
        # work on that axis, that surplus is the chart and its card: the crop goes to it
        # (a pale grey ruler beside Kodak's strip is not card enough for the walk)
        if surplus and surplus[0] == ("x" if st[0] in "lr" else "y") and f < surplus[1] <= f + 0.12: f = surplus[1]
        return st[0], round(float(min(0.4, bound(st[0], f))), 3)
    def wedge():                                                  # a grey scale alone
        w = wedge_of(hsv)
        return (w[0], round(min(w[1], surplus[1] + 0.02), 3)) if w and surplus and surplus[0] == ("x" if w[0] in "lr" else "y") else w
    win, rows, cols = chart_windows(hsv)
    if not win.any(): return wedge()
    # The windows fall into clusters (touching windows); a chart is a cluster within the
    # band along one edge. They are clustered edge by edge, among the windows inside that
    # edge's band, so a painting's colourful passage beside a chart does not carry the
    # cluster into the middle; a cluster in a corner (a grey-scale card's colour patches
    # at its end) counts for the edge it lies closest to; and it takes four windows --
    # two or three were a painting's flowers, a stream in the snow (a tenth of the old
    # crops cut a painting that had no chart, 2026-09-28).
    R = np.array(rows)[:, None]; C = np.array(cols)[None, :]
    inband = {"l": (C + WIN) / Wd <= BAND, "r": 1 - C / Wd <= BAND, "t": (R + WIN) / H <= BAND, "b": 1 - R / H <= BAND}
    best = None
    for bside, m in inband.items():
        mask = win & np.broadcast_to(m, win.shape)
        lab = np.zeros(win.shape, int); nlab = 0
        for i, j in zip(*np.where(mask)):
            if lab[i, j]: continue
            nlab += 1; stack = [(i, j)]; lab[i, j] = nlab
            while stack:
                a, b = stack.pop()
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        y2, x2 = a + da, b + db
                        if 0 <= y2 < win.shape[0] and 0 <= x2 < win.shape[1] and mask[y2, x2] and not lab[y2, x2]:
                            lab[y2, x2] = nlab; stack.append((y2, x2))
        for k in range(1, nlab + 1):
            ii, jj = np.where(lab == k)
            if len(ii) < 4: continue
            ys = np.array([rows[i] for i in ii]); xs = np.array([cols[j] for j in jj])
            reach = {"l": (xs.max() + WIN) / Wd, "r": 1 - xs.min() / Wd, "t": (ys.max() + WIN) / H, "b": 1 - ys.min() / H}
            if min(reach, key=reach.get) != bside: continue
            if best is None or len(ii) > best[0]: best = (len(ii), bside, xs, ys)
    if best is None: return wedge()
    _, side, xs, ys = best
    ext = {"l": xs.max() + WIN, "r": Wd - xs.min(), "t": ys.max() + WIN, "b": H - ys.min()}[side]
    full = Wd if side in "lr" else H
    # the chart sits on a card, black or white, that runs on past the patches (Julie
    # Hagen-Schwarz's self-portrait: the patches in the top 4%, the black holder to 10%);
    # the crop walks on through rows that are card -- unsaturated and either very dark
    # or very light -- for at most another 8% of the picture
    # a row is still chart while it is neutral (the card, the grey patches, the holder)
    # or vivid (the patches themselves); the walk looks only across the chart's own span,
    # since beside the card is wall
    card = ((hsv[..., 1] < 60) & ((hsv[..., 2] < 70) | (hsv[..., 2] > 190))) | (hsv[..., 1] < 15)
    vivid = (hsv[..., 1] > 80) & (hsv[..., 2] > 90)
    lo, hi = (ys.min(), ys.max() + WIN) if side in "lr" else (xs.min(), xs.max() + WIN)
    seg = (lambda a, i: a[lo:hi, i]) if side in "lr" else (lambda a, i: a[i, lo:hi])
    at = (lambda k: k) if side in "lt" else (lambda k: full - 1 - k)
    k, miss, last = ext, 0, ext
    while k < min(full - 1, ext + 0.08 * full) and miss <= 3:        # the dark lines between patches are not the painting
        if seg(card, at(k)).mean() >= 0.6 or seg(vivid, at(k)).mean() >= 0.4: last = k + 1; miss = 0
        else: miss += 1
        k += 1
    ext = last
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

def run(items):
    """read the photographs in a pool of processes, one per core: the reading of a
    picture is numpy work that holds Python's lock, so threads ran on one core"""
    n, t0 = 0, time.time()
    with ProcessPoolExecutor(os.cpu_count() or 4) as ex:
        for im, s in ex.map(one, items, chunksize=4):
            if s is not None: sides[im] = s
            n += 1
            if n % 500 == 0:
                json.dump(sides, open(OUT + ".tmp", "w", encoding="utf-8")); os.replace(OUT + ".tmp", OUT)
                print(f"  {n:,}/{len(items):,}  {n/(time.time()-t0):.1f}/s", flush=True)
    json.dump(sides, open(OUT + ".tmp", "w", encoding="utf-8")); os.replace(OUT + ".tmp", OUT)

if __name__ == "__main__":
    run([i for i in todo if i.startswith("e:")] + [i for i in todo if i.startswith("m:")])
    import collections
    print("CHART SIDES:", dict(collections.Counter(v[0] if v else "none" for v in sides.values())), f"of {len(sides):,} photographs")
