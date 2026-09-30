# -*- coding: utf-8 -*-
"""Artman (artman.ee) -> appends to gallery_records.json. WooCommerce; metadata only.

A Tallinn Old Town dealer's e-shop -- ~115 works in September 2026, mostly the classics
(Wiiralt, Albo, Pehap, Ohakas, Okas) with a few living artists (Raul Meel, Navitrolla,
Kostabi). Read through the WooCommerce Store API (/wp-json/wc/store/v1/products), the
read-only endpoint its own pages use; robots.txt permits it. The product name carries
artist, title and year (Valdur Ohakas “Portree”, 1992); the technique and the size sit in
the prose description ("... valminud õlimaal ... Mõõtmed 39 × 29 cm"), the category is the
fallback technique. Prices are not read. Out of stock = sold: kept, flagged, for the ledger.
About 40% of the stock is also offered at Artner (artner.py, which runs first): a work
both dealers list stays one record, Artner's, and Artman keeps what only it has.
"""
import json, re, ssl, time, html, urllib.request
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
API = "https://www.artman.ee/wp-json/wc/store/v1/products"
ctx = ssl.create_default_context()
U = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
# first technique named in the description; whole words only ("maalikunstnik" is not one)
TECH = re.compile(r"\b(?:värviline\s+)?(õlimaal|akrüülmaal|temperamaal|akvarell|guašš|pastell|segatehnika|söejoonistus|"
                  r"tušijoonistus|pliiatsijoonistus|joonistus|litograafia|ofort|kuivnõel|akvatinta|mezzotinto|metsotinto|"
                  r"monotüüpia|linoollõige|puulõige|kõrgtrükk|sügavtrükk|serigraafia|siiditrükk|giclée|digitrükk)\b", re.I)
CAT = {"Õlimaalid": "õli", "Graafika": "graafika"}

def api(page):
    for k in range(3):
        try:
            r = urllib.request.Request(f"{API}?per_page=100&page={page}", headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=60, context=ctx) as f: return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:
            if k == 2: print("ERR page", page, repr(e)[:60], flush=True); return []
            time.sleep(3 * (k + 1))

def artist_of(a):
    """'Karl Burman seenior' -> 'Karl Burman sr' (merge reads the generation); 'Gita Teearu,' -> 'Gita Teearu'"""
    a = re.sub(r"\bseenior\b", "sr", a.strip(" ,"), flags=re.I)
    return re.sub(r"\bjuunior\b", "jr", a, flags=re.I)

F = lambda s: re.sub(r"\W", "", (s or "").lower())
prev = json.load(open("gallery_records.json", encoding="utf-8"))
at_artner = {(F(r["artist"]), F(r["title"])) for r in prev if r["gid"].startswith("artner-") and not r.get("sold")}
recs, page, twins = [], 1, 0
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        name = U(p.get("name"))
        m = re.match(r"^(.+?)\s*[“„\"](.+?)[”“\"]\s*,?\s*(.*)$", name)
        if not m: continue                                               # no quoted title: not an artwork
        artist, title, rest = artist_of(m.group(1)), m.group(2).strip(), m.group(3)
        if not artist or re.match(r"(tundmatu|teadmata|anonüüm)", artist, re.I): continue
        if (F(artist), F(title)) in at_artner: twins += 1; continue
        y = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", rest)
        desc = U(p.get("description"))
        dm = re.search(r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?\s*cm", desc)
        tm = TECH.search(desc)
        cat = next((c["name"] for c in p.get("categories", [])), "")
        tech = tm.group(0).lower() if tm else CAT.get(cat, "")
        img = (p.get("images") or [{}])[0].get("src")
        recs.append({"gid": f"artman-{p['id']}", "artist": artist, "title": title, "year": y.group(1) if y else None,
                     "tech": tech[:80], "dims": " x ".join(g for g in dm.groups() if g) + " cm" if dm else "",
                     "gallery": "Artman", "city": "Tallinn", "url": p.get("permalink") or "https://www.artman.ee",
                     **({"sold": True} if not p.get("is_in_stock", True) else {}),
                     **({"img": img} if img else {})})
    page += 1; time.sleep(1)
    if page > 10: break

keep = [r for r in prev if not r["gid"].startswith("artman-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"ARTMAN WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}  also at Artner, left to it: {twins}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with tech {sum(1 for r in recs if r['tech'])}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
