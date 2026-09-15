# -*- coding: utf-8 -*-
"""Allee galerii shop stock -> gallery_records.json (gallery: Allee galerii)

The same WooCommerce Store API that carries Allee's auction lots (type "auction",
read by allee_auctions.py) carries the gallery's own stock as plain products,
category "E-pood": what is purchasable and in stock now. The name is the lot line
the house uses everywhere -- "Endel Kõks “Théme-timide”, 1968" -- and the short
description opens with the medium and the size: "Söövitus paberil. Raamitud.
Mõõdud: plm 17,4 x 15 cm, raamiga 41 x 38 cm." The work's own size is taken, not
the frame's. Prices are in the payload and are not read.
"""
import re, json, os, time, html, urllib.request, ssl

API = "https://alleegalerii.ee/wp-json/wc/store/v1/products"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def api(page, per=100):
    for attempt in range(3):
        try:
            r = urllib.request.Request(f"{API}?per_page={per}&page={page}", headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f:
                return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:
            if attempt == 2: print("ERR page", page, repr(e)[:60], flush=True); return []
            time.sleep(3 * (attempt + 1))

clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
LOT = re.compile(r"^(?P<a>[^“”\"„]+?)\s*,?\s*[“”\"„]\s*(?P<t>.+?)\s*[”\"“]\s*,?\s*(?P<rest>.*)$", re.S)
DIMS = re.compile(r"(?:\b(?:plm|km|lm|vm|ava)\s*)?(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*cm", re.I)
SALE = re.compile(r"oksjon\s*\d{4}", re.I)

recs, seen, page, unparsed, skipped = [], set(), 1, 0, 0
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        cats = [clean(c["name"]) for c in p.get("categories", [])]
        # stock, not a lot: a plain product, purchasable and in stock, in no sale's category
        if p.get("type") != "simple" or not p.get("is_purchasable") or not p.get("is_in_stock") or any(SALE.search(c) for c in cats):
            skipped += 1; continue
        line = clean(p.get("name"))
        m = LOT.match(line)
        if not m: unparsed += 1; continue
        artist = re.sub(r"\([^)]*\)", " ", m.group("a"))
        artist = re.sub(r"i\s+illustratsioon.*$", "", artist)                    # "Eduard Wiiralti illustratsioon ..." -- the genitive
        artist = re.sub(r"(\s+[a-zäöüõšž][^\s]*)+$", "", re.sub(r"\s+", " ", artist).strip(" ,"))
        if not re.match(r"^[^\d]{3,60}$", artist): unparsed += 1; continue
        title = m.group("t").strip()
        yl = m.group("rest").strip(" ,.")
        y4 = re.search(r"(1[5-9]\d\d|20[0-2]\d)", yl)
        desc = clean(p.get("short_description") or "") or clean(p.get("description") or "")
        first = re.split(r"\.\s", desc, 1)[0]
        medium = first.strip(" .") if first and len(first) < 60 and not re.search(r"\d", first) else ""
        if re.fullmatch(r"(raamitud|raamimata|signeeritud)", medium, re.I): medium = ""   # a framing note, not a medium
        dm = re.search(r"Mõõdud\s*:?\s*(.*?)(?:raamiga|$)", desc, re.I)
        dd = DIMS.search(dm.group(1)) if dm else DIMS.search(desc)
        dims = (re.sub(r"\s*[x×]\s*", " x ", dd.group(1)).replace(",", ".") + " cm") if dd else ""
        gid = "allee-" + str(p.get("id"))
        if gid in seen: continue
        seen.add(gid)
        recs.append({"gid": gid, "artist": artist, "title": title, "year": y4.group(1) if y4 else None,
                     "tech": medium, "dims": dims, "gallery": "Allee galerii", "city": "Tallinn",
                     "url": p.get("permalink") or "https://alleegalerii.ee"})
    if page % 5 == 0: print(f"  page {page}  kept {len(recs)}", flush=True)
    page += 1; time.sleep(0.8)
    if page > 80: break

prev = json.load(open("gallery_records.json", encoding="utf-8")) if os.path.exists("gallery_records.json") else []
keep = [r for r in prev if not r["gid"].startswith("allee-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"\nALLEE WORKS: {len(recs)}   artists: {len({r['artist'] for r in recs})}   unparsed: {unparsed}   lots and sold skipped: {skipped}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with medium {sum(1 for r in recs if r['tech'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:5]: print(f"   {r['artist'][:20]:20} {r['title'][:30]:30} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
