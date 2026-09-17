# -*- coding: utf-8 -*-
"""The shape of every MuIS picture -> muis_shapes.json  {media id: height/width}

MuIS serves one size of a picture, up to a few megabytes, and ignores Range; the
record's dimensions are height by width for a painting but height, width and depth
for a sculpture, and say nothing about the photograph's margins. So the file is
opened and read only as far as its JPEG header -- the first 64 KB, then the
connection is closed -- for the pixel size. Only pictures not read before are
fetched, so the monthly run is short.
"""
import json, os, struct, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
OUT = "muis_shapes.json"
works = json.load(open("data.json", encoding="utf-8"))["works"]
ids = sorted({w["im"][2:] for w in works if str(w.get("im", "")).startswith("m:")})
shapes = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = [i for i in ids if i not in shapes]
print(f"MuIS shapes: {len(ids):,} pictures, {len(shapes):,} measured, {len(todo):,} to read", flush=True)

def jpeg_size(b):
    if b[:2] != b"\xff\xd8": return None
    i = 2
    while i + 9 < len(b):
        if b[i] != 0xFF: i += 1; continue
        m = b[i + 1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7: i += 2; continue
        ln = struct.unpack(">H", b[i + 2:i + 4])[0]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", b[i + 5:i + 9]); return w, h
        i += 2 + ln
    return None

def one(mid):
    for attempt in range(2):
        try:
            r = urllib.request.Request(f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={mid}", headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=40) as resp:
                b = resp.read(65536)
                s = jpeg_size(b)
                if s is None: b += resp.read(262144); s = jpeg_size(b)
            return mid, (round(s[1] / s[0], 3) if s and s[0] and s[1] else None)
        except Exception:
            time.sleep(1 + attempt)
    return mid, None

n = 0
with ThreadPoolExecutor(12) as ex:
    for mid, r in ex.map(one, todo):
        if r: shapes[mid] = r
        n += 1
        if n % 500 == 0:
            json.dump(shapes, open(OUT, "w", encoding="utf-8"))
            print(f"  {n:,}/{len(todo):,}", flush=True)
json.dump(shapes, open(OUT, "w", encoding="utf-8"))
print(f"\nMUIS SHAPES: {len(shapes):,} of {len(ids):,} pictures measured")
