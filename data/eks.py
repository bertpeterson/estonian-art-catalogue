# -*- coding: utf-8 -*-
"""E-Kunstisalong's works for sale -> gallery_records.json (gallery: E-Kunstisalong)

Beside its auctions (eks_auctions.py) the salon sells directly; "Teosed" lists every
work with a card: artist and title in two spans, then "2026. Õli, lõuend. 20x20." --
year, medium, size in centimetres -- and a price, which is not read. One page holds
the whole stock; the robots file forbids query strings and asks a two-minute delay, and
this reads one page. The pages are ISO-8859-4, like the auction ones.
The card's picture is the salon's own, taken while the work is for sale.
"""
import re, json, os, html, urllib.request

BASE = "https://www.e-kunstisalong.ee"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
r = urllib.request.Request(f"{BASE}/Teosed_702", headers={"User-Agent": UA})   # one page; robots.txt disallows query strings, so no filters
with urllib.request.urlopen(r, timeout=60) as f: h = f.read().decode("iso-8859-4", "replace")
CARD = re.compile(r"<a href=\"([^\"]+)\"[^>]*class=autor[^>]*>\s*<b><span class='toot_hr_jn alapealkiri'>(.*?)</span><span class='toot_hr_jn'>(.*?)</span></b><span class=toot_hr_jn>(.*?)</span>", re.S)
IMG = re.compile(r"data-src='(/s2/[^']+)'")
clean = lambda s: html.unescape(re.sub(r"\s+", " ", s)).strip()
DIMS = re.compile(r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?")

recs, imgs = [], {}
for m in IMG.finditer(h): pass
# the picture sits in the card just before the text; pair by walking the cards in order
cards = list(CARD.finditer(h))
pics = [m for m in IMG.finditer(h)]
for k, c in enumerate(cards):
    slug, artist, title, line = (clean(x) for x in c.groups())
    pid = slug.rsplit("_", 1)[-1]
    # "2026. Õli, lõuend. 20x20." / "1987. Akvatinta, ofort. plm 24x30, lm 33x45."
    parts = [p.strip() for p in line.split(".") if p.strip()]
    year = parts[0] if parts and re.match(r"^\d{4}", parts[0]) else None
    medium = next((p for p in parts[1:] if not DIMS.search(p) and not re.match(r"^\d", p)), None) if year else (parts[0] if parts and not DIMS.search(parts[0]) else None)
    dm = DIMS.search(line)
    dims = (" x ".join(x.replace(",", ".") for x in dm.groups() if x) + " cm") if dm else ""
    # the card's picture is the nearest data-src before this card's text
    before = [p for p in pics if p.start() < c.start()]
    img = BASE + before[-1].group(1) if before else None
    recs.append({"gid": "eks-" + pid, "artist": artist, "title": title, "year": year[:4] if year else None,
                 "tech": medium, "dims": dims, "gallery": "E-Kunstisalong", "city": "Tallinn",
                 "url": f"{BASE}/{slug}", **({"img": img} if img else {})})
prev = json.load(open("gallery_records.json", encoding="utf-8")) if os.path.exists("gallery_records.json") else []
keep = [r for r in prev if not r["gid"].startswith("eks-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"E-KUNSTISALONG STOCK: {len(recs)} works for sale; {sum(1 for r in recs if r.get('img'))} with a picture")
for r in recs[:4]: print("  ", r["artist"], "|", r["title"], "|", r["year"], "|", r["tech"], "|", r["dims"])
