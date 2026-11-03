# -*- coding: utf-8 -*-
"""Art Keller (artkeller.ee) -> appends to gallery_records.json. WooCommerce; metadata only.

A Tallinn dealer in Estonian art (Pärnu mnt 142, buys and swaps works too) -- ~350 works
in November 2026, two thirds prints: Peet Aren's 1920 linocuts, Mugasto's 1938 wood
engravings, Wiiralt, Illimar Paul, Priidu Aavik, with Soviet-era and living painters
(Okas, Leškin, Jan Tammik). Read through the WooCommerce Store API, the read-only
endpoint its own pages use; robots.txt closes only the cart, admin and upload logs.
The product name carries artist, title and year (Evald Okas “Kalevipoja säng” 1961.);
the short description gives the technique on the line after the title ("Õli, lõuend",
"Söövitus, ofort 17/40"), the long one the sizes -- the picture's (Maali mõõt, Valgusmõõt)
before the sheet's or the frame's. The asking price of current stock is read
(asking_price.py); a sold work's never. Out of stock = sold: kept, flagged.
Works by two or more hands ("Evald Okas, Allex Kütt, Olev Soans") are left out.
"""
import json, re, ssl, time, html, urllib.request
from asking_price import asking
import store_api
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
API = "https://artkeller.ee/wp-json/wc/store/v1/products"
ctx = ssl.create_default_context()
U = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
DIM = r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?\s*cm"
CAT = {"Õli": "õli", "Akvarell": "akvarell", "Guašš-Tempera": "guašš", "GRAAFIKA": "graafika", "SKULPTUUR": "skulptuur"}

def api(page):
    return store_api.page(f"{API}?per_page=100&page={page}", UA, ctx, 60)    # a page not read stops the script (store_api.py)

def artist_of(a):
    """'* Richard Kaljo' -> 'Richard Kaljo'; 'Ülo Sooster Ülo Sooster' -> once; 'Vive Tolli (Pajusoo)' -> 'Vive Tolli';
    'Kairo (Kairi Kliimand)' -> the full name in the brackets"""
    a = a.strip(" ,*")
    m = re.match(r"^(.+?)\s*\((.+)\)$", a)
    if m: a = m.group(2) if " " in m.group(2) else m.group(1)
    w = a.split()
    if len(w) % 2 == 0 and w[:len(w) // 2] == w[len(w) // 2:]: a = " ".join(w[:len(w) // 2])
    return a

def tech_of(short, title):
    """The paragraph after the one holding the title, unless it is only 'Signeeritud' and the like"""
    ps = [U(p) for p in re.findall(r"<p>(.*?)</p>", short or "", re.S)]
    ps = [p for p in ps if p]
    k = next((i for i, p in enumerate(ps) if title and title.lower() in p.lower()), -1)
    for p in ps[k + 1:]:
        # the title line again, worded otherwise ('“Nõukogude palee, Kreml Moskva” 1940-ndad'), is not it either
        if not re.match(r"(signeeritud|signeerimata|ekspertiisiakt|raamitud|raamis)\b", p, re.I) and not re.search(r"[“„\"”]", p):
            return re.sub(r"\s+\d+/\d+\b.*$", "", p).strip(" .,")      # the edition ("17/40", "3/10 autorieksemplar") is not the technique
    return ""

def dims_of(desc):
    """The picture's size before the sheet's or the frame's"""
    best = None
    for m in re.finditer(r"([\wõäöü]+ ?mõõt\w*)?\s*:?\s*" + DIM, desc, re.I):
        label = (m.group(1) or "").lower()
        if best is None: best = m
        if label and not re.match(r"(lehe|raami|originaalraami)", label): best = m; break
    return " x ".join(g for g in best.groups()[1:] if g) + " cm" if best else ""

recs, page = [], 1
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        name = U(p.get("name"))
        m = re.match(r"^(.+?)\s*[“„\"”]\s*(.+?)\s*[”“\"]\s*,?\s*(.*)$", name)
        if not m: continue                                               # no quoted title: not an artwork
        artist, title, rest = artist_of(m.group(1)), m.group(2).strip(), m.group(3)
        if not artist or re.search(r",|\bja\b|&|/|\?", artist) or re.match(r"(tundmatu|teadmata|anonüüm)", artist, re.I): continue
        y = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", rest) or re.search(r"\b(1[5-9]\d\d|20\d\d)\b", title)   # a portfolio's: “Linoollõiked 1920”
        cat = next((CAT[c["name"]] for c in p.get("categories", []) if c["name"] in CAT), "")
        im = (p.get("images") or [{}])[0]
        # the 768-wide copy from the srcset, not the 2560 "scaled" original
        img = next((u for u, w in re.findall(r"(\S+) (\d+)w", im.get("srcset") or "") if 600 <= int(w) <= 1024), im.get("src"))
        recs.append({**asking(p), "gid": f"artkeller-{p['id']}", "artist": artist, "title": title, "year": y.group(1) if y else None,
                     "tech": (tech_of(p.get("short_description"), title) or cat)[:80], "dims": dims_of(U(p.get("description"))),
                     "gallery": "Art Keller", "city": "Tallinn", "url": p.get("permalink") or "https://artkeller.ee",
                     **({"sold": True} if not p.get("is_in_stock", True) else {}),
                     **({"img": img} if img else {})})
    page += 1; time.sleep(1)
    if page > 10: break

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("artkeller-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"ART KELLER WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}  priced: {sum(1 for r in recs if r.get('price'))}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with tech {sum(1 for r in recs if r['tech'])}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
