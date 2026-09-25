# -*- coding: utf-8 -*-
"""Artner (artner.ee) -> appends to gallery_records.json. WooCommerce; metadata only.

An Estonian dealer's online catalogue -- classics and contemporary work from galleries
and collectors, ~750 on sale in September 2026, strong on the post-war generation
(Kaljo, Ohakas, Pehap, Aino Bach, Hugo Mitt). Read through the WooCommerce Store API
(/wp-json/wc/store/v1/products), the read-only endpoint its own pages use; robots.txt
permits it. Each product carries the artist as an attribute ("MEEL, Raul"), the title
and year in its name ("Eesti saared II", 1986), the technique as another attribute, and
a size in centimetres only now and then. Prices are not read. A product out of stock is
the dealer's word that it sold: kept, flagged, for the ledger.
"""
import json, re, ssl, time, html, urllib.request
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
API = "https://artner.ee/wp-json/wc/store/v1/products"
ctx = ssl.create_default_context()
U = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def api(page):
    for k in range(3):
        try:
            r = urllib.request.Request(f"{API}?per_page=100&page={page}", headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=60, context=ctx) as f: return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:
            if k == 2: print("ERR page", page, repr(e)[:60], flush=True); return []
            time.sleep(3 * (k + 1))

def person(n):
    """'MEEL, Raul' -> 'Raul Meel'; 'NAVITROLLA' stays"""
    n = U(n)
    if "," in n:
        sur, first = [p.strip() for p in n.split(",", 1)]
        sur = sur.title() if sur.isupper() else sur
        return f"{first} {sur}".strip()
    return n.title() if n.isupper() and " " in n else n

recs, page = [], 1
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        who = [t["name"] for a in p.get("attributes", []) if a.get("taxonomy") == "pa_kunstnikud" for t in a.get("terms", [])]
        if not who: continue
        artist = person(who[0])
        if re.match(r"(tundmatu|teadmata|anonüüm)", artist, re.I): continue      # attributed work only
        name = U(p.get("name")).strip()
        m = re.match(r'^[“"„]?(.+?)[”"“]?\s*,\s*((?:ca\.?\s*)?\d{4}(?:\s*[–-]\s*\d{2,4})?)\s*$', name)
        title, year = (m.group(1), re.search(r"\d{4}", m.group(2)).group(0)) if m else (name.strip('“”"„'), None)
        sd = U(p.get("short_description"))
        dm = re.search(r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*cm", sd)
        # the technique is an attribute ("Serigraafia", "Vitrograafia"); the short
        # description holds signatures and framing more often than the medium, and the
        # size only as a class (S/M/L/XL) -- centimetres where it gives them. The price-
        # range attribute is never read.
        tech = next((t["name"] for a in p.get("attributes", []) if a.get("taxonomy") == "pa_tehnika" or a.get("name") == "Tehnika" for t in a.get("terms", [])), "")
        if not tech: tech = next((c["name"] for c in p.get("categories", [])), "")
        img = (p.get("images") or [{}])[0].get("src")
        recs.append({"gid": f"artner-{p['id']}", "artist": artist, "title": title.strip(), "year": year,
                     "tech": tech[:80], "dims": re.sub(r"\s*[x×]\s*", " x ", dm.group(1)) + " cm" if dm else "",
                     "gallery": "Artner", "city": "", "url": p.get("permalink") or "https://artner.ee",
                     **({"sold": True} if not p.get("is_in_stock", True) else {}),
                     **({"img": img} if img else {})})
    page += 1; time.sleep(1)
    if page > 30: break

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("artner-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"ARTNER WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
