# -*- coding: utf-8 -*-
"""The galleries' own smaller copies of their pictures, for the wall -> img_small.json
{picture: smaller picture, or "" where there is none}

A gallery's photograph on the wall was the file the gallery uploaded: 1,300 to 2,700
pixels across, 500 to 750 KB, for a tile under 300 pixels wide. A WordPress gallery
(Allee, Vernissage, Kogo, Artrovert) keeps a copy of every upload 768 pixels wide,
named <file>-768x<height>.<ext> -- the gallery's own file on the gallery's own server,
a quarter of the weight. This works out each picture's name at that width from its
shape (read from the first bytes of the file, or from the name where the gallery
already links a sized copy), checks the copy is there, and records it. The wall and
the hub pages show the copy; an opened record shows the gallery's picture as before.
Nothing is kept but the addresses.

MuIS, NOBA and Tütar serve one size only; EKM, Haus and E-Kunstisalong already link
small files. A picture checked once is not checked again, found or not.

    python3 img_small.py            (from data/; after the merges)
"""
import json, os, re, struct, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
OUT = "img_small.json"
WP = {"alleegalerii.ee", "vernissage.ee", "www.kogogallery.ee", "kogogallery.ee", "artrovert.ee", "www.artrovert.ee"}
WIDTH = 768

W = json.load(open("data.json", encoding="utf-8"))["works"]
done = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}

def get(url, rng=None):
    h = {"User-Agent": UA}
    if rng: h["Range"] = rng
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
        return r.status, r.read(rng and 262144 or None)

def dims(b):
    """width and height from a JPEG's frame header, a PNG's IHDR or a WebP's VP8 header"""
    if b[:8] == b"\x89PNG\r\n\x1a\n": return struct.unpack(">II", b[16:24])
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        if b[12:16] == b"VP8X": return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
        if b[12:16] == b"VP8 ": w, h = struct.unpack("<HH", b[26:30]); return w & 0x3fff, h & 0x3fff
        if b[12:16] == b"VP8L": v = int.from_bytes(b[21:25], "little"); return 1 + (v & 0x3fff), 1 + ((v >> 14) & 0x3fff)
    if b[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF: i += 1; continue
            m = b[i + 1]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7: i += 2; continue
            n = struct.unpack(">H", b[i + 2:i + 4])[0]
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", b[i + 5:i + 9]); return w, h
            i += 2 + n
    return None

def size_of(url):
    """the picture's width and height, from as little of the file as tells them"""
    _, b = get(url, "bytes=0-65535")
    d = dims(b)
    if not d:
        _, b = get(url); d = dims(b)
    if not d: raise ValueError("no size")
    return d

def exists(url):
    try:
        st, b = get(url, "bytes=0-0")
        return st in (200, 206) and len(b) > 0
    except Exception:
        return False

def small(im):
    url = im[2:]
    m = re.match(r"^(.*?)(?:-(\d+)x(\d+))?(\.(?:jpe?g|png|webp))$", url, re.I)
    if not m: return ""
    base, w, h, ext = m.group(1), m.group(2), m.group(3), m.group(4)
    try:
        w, h = (int(w), int(h)) if w else size_of(url)
    except Exception:
        return None                                 # unreadable today: try again next run
    if w <= WIDTH * 1.15: return ""                 # already about the size
    hh = round(h * WIDTH / w)
    for c in (hh, hh - 1, hh + 1):                  # WordPress rounds; a pixel either way
        cand = f"{base}-{WIDTH}x{c}{ext}"
        if exists(cand): return "g:" + cand
    return ""

todo = sorted({w["im"] for w in W if (w.get("im") or "").startswith("g:")
               and urllib.parse.urlparse(w["im"][2:]).netloc in WP and w["im"] not in done})
print(f"img_small: {len(todo):,} gallery pictures to check ({len(done):,} checked before)")
with ThreadPoolExecutor(4) as ex:
    for im, s in zip(todo, ex.map(small, todo)):
        if s is not None: done[im] = s
live = {w["im"] for w in W if w.get("im")}
done = {k: v for k, v in sorted(done.items()) if k in live}       # a picture gone from the data goes from here
json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0, separators=(",", ":"))
print(f"img_small: {sum(1 for v in done.values() if v):,} of {len(done):,} have a smaller copy")
