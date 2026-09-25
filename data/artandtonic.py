# -*- coding: utf-8 -*-
"""Art & Tonic (artandtonic.art) -> appends to gallery_records.json. WooCommerce; metadata only.

A contemporary gallery founded in Tartu in 2019, in Tallinn since 2025 (~190 works on
sale in September 2026: Alo Valge, Rauno Thomas Moss, Alar Tuul, Marko Mäetamm).
Read through the WooCommerce Store API; robots.txt permits everything. The artist is
the product's category; the short description gives size, technique and year
("120×80 cm, õlimaal lõuendil, 2026"). A product out of stock is sold: kept, flagged.
Prices are not read.
"""
import json, re, ssl, time, html, urllib.request
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
API = "https://artandtonic.art/wp-json/wc/store/v1/products"
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

recs, page = [], 1
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        cats = [U(c["name"]) for c in p.get("categories", []) if not re.match(r"(uncategorized|määramata|pood|shop)", c["name"], re.I)]
        if not cats: continue
        artist = cats[0]
        if "/" in artist: continue                      # a work by two artists ("A / B"): no single maker
        sd = U(p.get("short_description")) or U(p.get("description"))[:200]
        dm = re.search(r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*cm", sd)
        ym = re.search(r"\b(19\d\d|20\d\d)\b", sd)
        tech = re.sub(r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*cm|\b(19|20)\d\d\b", "", sd.split(".")[0])
        tech = re.sub(r"\s*,\s*,+", ",", tech).strip(" ,.;")
        img = (p.get("images") or [{}])[0].get("src")
        recs.append({"gid": f"aat-{p['id']}", "artist": artist, "title": U(p.get("name")).strip('“”"„'), "year": ym.group(1) if ym else None,
                     "tech": tech[:80], "dims": re.sub(r"\s*[x×]\s*", " x ", dm.group(1)) + " cm" if dm else "",
                     "gallery": "Art & Tonic", "city": "Tallinn", "url": p.get("permalink") or "https://artandtonic.art",
                     **({"sold": True} if not p.get("is_in_stock", True) else {}),
                     **({"img": img} if img else {})})
    page += 1; time.sleep(1)
    if page > 10: break

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("aat-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"ART & TONIC WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
