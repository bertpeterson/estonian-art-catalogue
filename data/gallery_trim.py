# -*- coding: utf-8 -*-
"""The empty border around a gallery's picture -> gallery_trim.json  {url: [left, top, right, bottom] | 0}

Some galleries (Artrovert) show a work as a small picture in the middle of a white or transparent
square. The picture is embedded from the gallery, never copied, so the border cannot be cut off the
file: it is measured here, per picture, and the site's tiles zoom past it when they draw the picture.

A side is trimmed only where the file's edge is flat background: every row or column from the edge
inward that is pure white (or transparent) to within NOISE. White paper photographed is not flat
white, so a print's own margin stays. A sliver (KEEP) of the border is left on each trimmed side, and
a picture whose border is thin (under MIN of its width or height on every side) is left alone: 0.
Insets are in thousandths of the width (left, right) and height (top, bottom). Each picture is read
once, in memory, and nothing of it is kept. Only the galleries in HOSTS are read.

    .venv-clip/bin/python gallery_trim.py            measure pictures not measured before
    .venv-clip/bin/python gallery_trim.py --sheet    also write trim_sheet.html: before and after, for the eye
"""
import io, json, os, sys, time, urllib.request
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
OUT = "gallery_trim.json"
HOSTS = {"www.artrovert.ee", "www.idla.ee"}
WHITE, NOISE, KEEP, MIN = 250, 0.004, 0.012, 0.03


def border(img):
    """[l, t, r, b] in thousandths, or 0: how far the flat background reaches in from each edge"""
    img.thumbnail((700, 700))
    a = np.asarray(img.convert("RGBA"))
    bg = (a[..., 3] < 8) | (a[..., :3].min(axis=2) >= WHITE)        # transparent, or white
    h, w = bg.shape
    def run(lines):                                                  # how many lines from the edge are background
        n = 0
        for line in lines:
            if 1 - line.mean() > NOISE: break
            n += 1
        return n
    t, b = run(bg), run(bg[::-1])
    if t + b >= h: return 0                                          # an empty picture
    l, r = run(bg[t:h - b].T), run(bg[t:h - b].T[::-1])
    f = [l / w, t / h, r / w, b / h]
    if max(f) < MIN: return 0
    return [max(0, round((x - KEEP) * 1000)) if x >= MIN else 0 for x in f]


def read(u):
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(quote(u, safe=":/?&=%+,;@()~!*'"), headers={"User-Agent": UA}), timeout=60) as r:
                return u, border(Image.open(io.BytesIO(r.read())))
        except Exception as e:
            err = e; time.sleep(2 + 3 * k)
    print("  not read:", u, err, flush=True)
    return u, None


def sheet(works, trim):
    """trim_sheet.html: each trimmed picture as the gallery sends it and as a tile would draw it"""
    cell = []
    for w in works:
        u = w["im"][2:]; v = trim.get(u)
        if not v: continue
        l, t, r, b = (x / 1000 for x in v)
        kw, kh = 1 - l - r, 1 - t - b
        after = (f'<div class="t" style="aspect-ratio:{kw:.4f}/{kh:.4f}"><img loading="lazy" src="{u}" '
                 f'style="width:{100 / kw:.2f}%;height:{100 / kh:.2f}%;left:{-100 * l / kw:.2f}%;top:{-100 * t / kh:.2f}%"></div>')
        cell.append(f'<figure><div class="p"><div class="b"><img loading="lazy" src="{u}"></div>{after}</div>'
                    f'<figcaption><a href="{w["url"]}">{w.get("t") or ""}</a><br>{v}</figcaption></figure>')
    open("trim_sheet.html", "w", encoding="utf-8").write(
        '<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>Border trim</title><style>'
        'body{background:#777;font:12px system-ui;margin:16px;color:#fff}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}'
        'figure{margin:0;background:#555;padding:8px}.p{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:center}'
        '.b img{width:100%;display:block}.t{position:relative;overflow:hidden;width:100%}.t img{position:absolute;max-width:none}'
        'a{color:#fff}figcaption{margin-top:6px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}</style>'
        f'<p>{len(cell)} pictures with a border, each as the gallery sends it (left) and trimmed (right). Grey shows through where a file is transparent.</p><main>'
        + "".join(cell) + "</main>")
    print(f"trim_sheet.html: {len(cell)} pictures")


if __name__ == "__main__":
    d = json.load(open(os.environ.get("MUSEAAL_DATA", "data.json"), encoding="utf-8"))   # local_cuts.sh: the published data.json
    works = [w for w in d["works"] if str(w.get("im") or "").startswith("g:") and urlparse(w["im"][2:]).hostname in HOSTS]
    trim = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    urls = sorted({w["im"][2:] for w in works})
    todo = [u for u in urls if u not in trim]
    print(f"{len(urls)} pictures, {len(todo)} to read", flush=True)
    with ThreadPoolExecutor(3) as ex:
        for u, v in ex.map(read, todo):
            if v is not None: trim[u] = v
    trim = {u: trim[u] for u in urls if u in trim}                  # a picture no longer shown leaves the file
    json.dump(trim, open(OUT, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"{OUT}: {len(trim)} measured, {sum(1 for v in trim.values() if v)} with a border to trim")
    if "--sheet" in sys.argv: sheet(works, trim)
