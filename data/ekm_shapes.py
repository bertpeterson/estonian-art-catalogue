# -*- coding: utf-8 -*-
"""The shape of every EKM picture -> ekm_shapes.json  {oid: height/width}

The wall lays its tiles out before the pictures arrive, so it needs each picture's
proportions up front. A third of the EKM records have no dimensions, and a photograph
of a work has margins the work's dimensions do not know about. The smallest preview
(tss_, about 150 px, 3 KB) is read for its pixel size -- the JPEG header, nothing
kept. Only pictures not measured before are fetched, so the monthly run is short.
"""
import json, os, struct, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://digikogu.ekm.ee/static/preview/image/"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
OUT = "ekm_shapes.json"
imgs = json.load(open("ekm_images.json", encoding="utf-8"))
shapes = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = [(oid, p) for oid, p in imgs.items() if oid not in shapes]
print(f"EKM shapes: {len(imgs):,} pictures, {len(shapes):,} measured, {len(todo):,} to read", flush=True)

def jpeg_size(b):
    """width, height from the SOF marker; None if it is not a JPEG we can read"""
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

def one(item):
    oid, p = item
    d, f = p.rsplit("/", 1)
    for attempt in range(3):
        try:
            r = urllib.request.Request(BASE + d + "/tss_" + f, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=30) as resp: b = resp.read()
            s = jpeg_size(b)
            return oid, (round(s[1] / s[0], 3) if s and s[0] else None)
        except Exception:
            time.sleep(1 + attempt)
    return oid, None

n = 0
with ThreadPoolExecutor(4) as ex:
    for oid, r in ex.map(one, todo):
        if r: shapes[oid] = r
        n += 1
        if n % 2000 == 0:
            json.dump(shapes, open(OUT, "w", encoding="utf-8"))
            print(f"  {n:,}/{len(todo):,}", flush=True)
json.dump(shapes, open(OUT, "w", encoding="utf-8"))
print(f"\nEKM SHAPES: {len(shapes):,} pictures measured")
