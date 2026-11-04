# -*- coding: utf-8 -*-
"""Each picture's three main colours, for the palette on the masthead's Works button
-> colours.json  {picture id: "rrggbbrrggbbrrggbb"}

The palette is the colours of the visitor's own saved works: the latest three, one bar
each. The picture hosts don't let a browser read a picture's pixels (no CORS), so the
colours are read here, as lookalikes.py reads its embeddings: every picture once, into
memory, shrunk to 64 pixels, discarded. Only the nine bytes are kept, and a later run
reads only the pictures it has not seen.

The colours: a margin of 8% trimmed (scan edges, mounts, a frame's shadow), the rest
cut to six colours by median cut, the commonest first, a colour within 40 of one
already taken passed over, three kept (fewer only for a near-flat picture, repeated).

Run with the other picture scripts:  python3 colours.py   (from data/; needs Pillow)
"""
import json, os, re, io, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
OUT = "colours.json"

def url_of(im):
    if im.startswith("m:"): return f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={im[2:]}"
    if im.startswith("e:"): return "https://digikogu.ekm.ee/static/preview/image/" + re.sub(r"/([^/]+)$", r"/t2_\1", im[2:])
    return urllib.parse.quote(im[2:], safe=":/?=&%+~@")

def colours(img):
    img.draft("RGB", (128, 128))
    img = img.convert("RGB"); img.thumbnail((64, 64))
    w, h = img.size; mx, my = round(w * .08), round(h * .08)
    if w - 2 * mx > 8 and h - 2 * my > 8: img = img.crop((mx, my, w - mx, h - my))
    q = img.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    found = sorted(q.getcolors(), reverse=True)
    out = []
    for _, i in found:
        c = tuple(pal[3 * i: 3 * i + 3])
        if all(sum((a - b) ** 2 for a, b in zip(c, o)) > 40 ** 2 for o in out): out.append(c)
        if len(out) == 3: break
    while len(out) < 3: out.append(out[-1])
    return "".join(f"{r:02x}{g:02x}{b:02x}" for r, g, b in out)

def fetch(im):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url_of(im), headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=60) as resp: b = resp.read()
            return im, colours(Image.open(io.BytesIO(b)))
        except Exception:
            time.sleep(2 + 2 * attempt)
    return im, None

if __name__ == "__main__":
    W = json.load(open("data.json", encoding="utf-8"))["works"]
    ims = sorted({w["im"] for w in W if w.get("im")})
    have = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [im for im in ims if im not in have]
    print(f"{len(ims):,} pictures, {len(have):,} read before, {len(todo):,} to read", flush=True)
    n = failed = 0; t0 = time.time()
    def save():
        json.dump(dict(sorted(have.items())), open(OUT, "w"), separators=(",", ":"))
    def run(items, workers):
        global n, failed
        with ThreadPoolExecutor(workers) as ex:
            for im, c in ex.map(fetch, items):
                n += 1
                if c: have[im] = c
                else: failed += 1
                if n % 1000 == 0:
                    save(); print(f"  {n:,}/{len(todo):,}  {n/(time.time()-t0):.1f}/s  failed {failed}", flush=True)
    # as lookalikes.py: EKM and the galleries four at a time, MuIS eight
    run([i for i in todo if i.startswith("e:")], 4)
    run([i for i in todo if i.startswith("m:")], 8)
    run([i for i in todo if i.startswith("g:")], 4)
    save()
    print(f"{len(have):,} pictures with colours, {failed} unreadable", flush=True)
