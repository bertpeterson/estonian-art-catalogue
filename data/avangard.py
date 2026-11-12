# -*- coding: utf-8 -*-
"""Avangard Galerii (avangardgallery.eu) -> appends to gallery_records.json. Metadata only.

A Pärnu gallery (Supeluse 1) with a small shop of prints, 24 in November 2026: Jüri Arrak,
Leonhard Lapin, Evi Tihemets, Mare Vint, Illimar Paul, Tõnis Vint. The shop is Voog; its
robots.txt closes only /files/ and /admin/. One listing (/e-pood) gives the works' addresses.
Each work's page carries the product as schema.org JSON-LD (name, id, price, availability,
picture) with the text a visitor reads in its description: a note on the artist, then lines
such as "Litograafia, tiraaž: 38/65" and "Kujutise mõõt 65x60 cm."
The name is 'Artist "Title" (year)'; a print pulled later from an old plate gives both years
("(1976/2018)") and the first, the year of the image, is kept. What stands between the title
and the year ('"Lõhutud ringid" VI-A (1992)') belongs to the title.
The asking price of a work in stock is read (asking_price.py); a sold work's never.
Anything but InStock = sold. Pictures are the site's own copies on Voog's media server
(media.voog.com, boundary.py IMAGE_HOSTS). Pages are cached for a day.
"""
import json, re, html
from asking_price import euros
from scrape_util import U, cached
BASE = "https://avangardgallery.eu"
FIX = {"Illmar Paul": "Illimar Paul"}                                   # the shop's own slip, on one work of four
NUM = r"\d+(?:[.,]\d+)?"
# the line that names the technique starts with one of these: "Litograafia, tiraaž: 38/65", "Serigraafia, 12/50"
TECH = (r"(?:värvi)?(?:lito\w*|serigraafia|siiditrükk|ofort|söövitus|akvatinta|kuivnõel|puulõige|linool\w*|mezzotinto|metsotinto|"
        r"pehmelakk|sügavtrükk|kõrgtrükk|ofset\w*|digi\w*|giclee|giclée|monotüüpia|segatehnika|õli|akrüül|akvarell|guašš|tušš|pliiats)")

def get(u, key): return cached(u, key, pause=1.2)   # scrape_util.py: a page not read stops the script

def lines(desc):
    """the description's lines as a visitor reads them: <br> and block ends are line ends"""
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|\n", "\n", desc or "")
    return [x for x in (U(l) for l in t.split("\n")) if x]

listing = get(f"{BASE}/e-pood", "avangard_shop")
slugs = list(dict.fromkeys(re.findall(r'href="/et/products/([a-z0-9-]+)"', listing)))
print("works listed:", len(slugs), flush=True)

recs, ids = [], set()
for s in slugs:
    h = get(f"{BASE}/et/products/{s}", f"avangard_{s}")
    p = None
    for block in re.findall(r'(?s)<script type="application/ld\+json">(.*?)</script>', h):
        try: j = json.loads(block)
        except ValueError: continue
        if isinstance(j, dict) and j.get("@type") == "Product": p = j; break
    if not p or not p.get("productID") or p["productID"] in ids: continue
    ids.add(p["productID"])
    name = U(p.get("name"))
    m = re.match(r'^(.+?)\s*[„"“”«]\s*(.+?)\s*["“”»]\s*(.*)$', name)
    if not m: continue
    artist = FIX.get(m.group(1).strip(" ,"), m.group(1).strip(" ,"))
    if len(artist.split()) < 2 or re.search(r"\d|\bja\b|&|\?|/", artist): continue
    rest = m.group(3)
    ym = re.search(r"\(\s*(1[89]\d\d|20[0-2]\d)\b[^)]*\)", rest)
    title = (m.group(2) + " " + (rest[:ym.start()] if ym else rest)).strip(" ,")
    ls = lines(p.get("description"))
    # the work's own lines are short ("Värviline lito, tiraaž: 8/120.", '"Vana Tallinn XII", signeeritud digitrükk 25/50',
    # "Tiraaž: 3/40. Lehe mõõt: 75,5x70 cm."); the note on the artist runs long and may name techniques too
    tech = next((l for l in ls if len(l) < 110 and re.search(rf"\b{TECH}\b|tiraa[žz]", l, re.I)), "")
    tech = re.sub(r'^[„"“][^"“”]+["“”]\s*,?\s*', "", tech)
    tech = re.sub(rf"(?:paberi|lehe|kujutise|pildi)?\s*mõõ[dt]\w*:?\s*{NUM}\s*[x×].*$", "", tech, flags=re.I)
    tech = re.sub(r"\b(?:1[89]|20)\d\d\b\.?(?:\s*a\.)?", "", tech)
    tech = re.sub(r"\s+([,.])", r"\1", re.sub(r"\s*[,.]\s*(?=[,.])|\s+", " ", tech)).strip(" ,.;")
    # the image's size where the page gives it ("kujutise mõõt 28x32 cm", "43x60 cm (pilt)"), else the sheet's
    D = rf"({NUM})\s*[x×]\s*({NUM})\s*cm"
    text = " ".join(ls)
    dm = re.search(rf"kujutise mõõt:?\s*{D}", text, re.I) or re.search(rf"{D}\s*\(pilt\)", text, re.I) or re.search(D, text)
    off = p.get("offers") or {}
    sold = not str(off.get("availability", "")).endswith("/InStock")
    try: n = round(float(off.get("price") or 0))
    except (TypeError, ValueError): n = 0
    price = {} if sold or off.get("priceCurrency") != "EUR" else euros(f"{n} €")
    img = p.get("image") or ""
    if img.startswith("//"): img = "https:" + img
    img = re.sub(r"(?<!_block)\.(jpe?g|png|webp)$", r"_block.\1", img, flags=re.I) if re.match(r"https://media\.voog\.com/", img) else ""
    recs.append({**price, "gid": f"avg-{p['productID']}", "artist": artist, "title": title or "Nimetu",
                 "year": ym.group(1) if ym else None, "tech": tech[:80],
                 "dims": f"{dm.group(1)} x {dm.group(2)} cm" if dm else "",
                 "gallery": "Avangard Galerii", "city": "Pärnu", "url": f"{BASE}/et/products/{s}",
                 **({"sold": True} if sold else {}),
                 **({"img": img} if img else {})})

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("avg-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"AVANGARD WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}  priced: {sum(1 for r in recs if r.get('price'))}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with tech {sum(1 for r in recs if r['tech'])}, with picture {sum(1 for r in recs if r.get('img'))}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
