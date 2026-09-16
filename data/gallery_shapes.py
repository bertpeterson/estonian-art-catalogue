# -*- coding: utf-8 -*-
"""The shape of every gallery picture -> gallery_shapes.json  {url: height/width}

The galleries' dimension lines cannot give a tile its shape: museums write height by
width, Vernissage width by height, and a photograph has margins the work does not.
So the picture itself is read for its pixel size -- the first 32 KB of the file,
enough for a JPEG's, PNG's or WebP's header, nothing kept. Only pictures not read
before are fetched, so the monthly run is short.
"""
import json, os, re, struct, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
OUT = "gallery_shapes.json"
works = json.load(open("data.json", encoding="utf-8"))["works"]
urls = sorted({w["im"][2:] for w in works if str(w.get("im", "")).startswith("g:")})
shapes = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = [u for u in urls if u not in shapes]
print(f"gallery shapes: {len(urls):,} pictures, {len(shapes):,} measured, {len(todo):,} to read", flush=True)

def size_of(b):
    """(width, height) from the header of a JPEG, PNG, GIF or WebP; None if unreadable"""
    if b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) >= 24: return struct.unpack(">II", b[16:24])
    if b[:6] in (b"GIF87a", b"GIF89a"): return struct.unpack("<HH", b[6:10])
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        f = b[12:16]
        if f == b"VP8X": return (int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1)
        if f == b"VP8L": n = int.from_bytes(b[21:25], "little"); return ((n & 0x3FFF) + 1, ((n >> 14) & 0x3FFF) + 1)
        if f == b"VP8 ": return (struct.unpack("<H", b[26:28])[0] & 0x3FFF, struct.unpack("<H", b[28:30])[0] & 0x3FFF)
        return None
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

def one(u):
    for attempt in range(2):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA, "Range": "bytes=0-32767"})
            with urllib.request.urlopen(r, timeout=30) as resp: b = resp.read(32768)
            s = size_of(b)
            if s is None:   # a long EXIF block before the frame header: read on
                r = urllib.request.Request(u, headers={"User-Agent": UA, "Range": "bytes=0-262143"})
                with urllib.request.urlopen(r, timeout=30) as resp: b = resp.read(262144)
                s = size_of(b)
            return u, (round(s[1] / s[0], 3) if s and s[0] and s[1] else None)
        except Exception:
            time.sleep(1 + attempt)
    return u, None

n = 0
with ThreadPoolExecutor(4) as ex:
    for u, r in ex.map(one, todo):
        if r: shapes[u] = r
        n += 1
        if n % 500 == 0:
            json.dump(shapes, open(OUT, "w", encoding="utf-8"))
            print(f"  {n:,}/{len(todo):,}", flush=True)
json.dump(shapes, open(OUT, "w", encoding="utf-8"))
print(f"\nGALLERY SHAPES: {len(shapes):,} of {len(urls):,} pictures measured")
