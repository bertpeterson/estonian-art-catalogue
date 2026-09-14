# -*- coding: utf-8 -*-
"""Vernissage auction results -> auction_records.json

The same Store API the shop harvest reads lists every auction lot the house has ever
put up, past sales included: is_purchasable is false for a lot, and the name carries
what the house published about it --
  "Jüri Arrak. Viiuldaja. 1965. Linoollõige. Paber. Km 34.5 x 27.2 cm. Alghind: 1800 € Haamrihind: 1800 €"
-- starting price, hammer price when it sold, MÜÜDUD when it sold at a price the house
did not print. The product category names the sale ("Sügisoksjon 2023").

These are results as the auction house published them, not valuations: a lot that
found no buyer is a result too, and is kept as one, marked unsold, with the price it
was offered at. A lot in a sale that has not happened yet is not a result and is
left out until it is.

The shop harvest is not touched: these records are a separate kind, and the
catalogue's rule that gallery asking prices are never shown stands.
"""
import re, json, os, time, datetime, urllib.request, ssl, html
from vern_parse import parse
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
API = "https://vernissage.ee/wp-json/wc/store/v1/products"
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

# "Haamrihind: 2050 €" is a sale; "Haamrihind: €" an unsold lot; "Haamrihind: müüdud
# 1200 €" a lot sold after the sale at its starting price. The 2022 sales number their
# lots ("71. Olev Mikiver. ...") and the number is not the artist.
START  = re.compile(r"alghind\s*:?\s*([\d\s.,]*?)\s*(?:€|eur)", re.I)
HAMMER = re.compile(r"haamrihind\s*:?\s*(müüdud\s*)?([\d\s.,]*?)\s*(?:€|eur)", re.I)
PRICE_PHRASE = re.compile(r"\b(alghind|haamrihind|hind|price|starting price|hammer price)\s*:?\s*(müüdud\s*)?[\d\s.,]*\s*(€|eur)?", re.I)
LOTNO = re.compile(r"^\s*\d{1,3}\.\s*")
SALE = re.compile(r"(kevad|suve|sügis|talve)?oksjon\s*(\d{4})", re.I)
MONTH = {"kevad": 5, "suve": 7, "sügis": 11, "talve": 2}   # when the house holds them; for ordering only
euros = lambda s: int(re.sub(r"[^\d]", "", s)) if re.sub(r"[^\d]", "", s) else None

today = datetime.date.today()
recs, page, seen = [], 1, set()
n_lots = n_upcoming = n_unparsed = n_nosale = n_odd = 0
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        if p.get("is_purchasable"): continue
        name = html.unescape(p.get("name") or "")
        cats = [html.unescape(c["name"]) for c in p.get("categories", [])]
        sale = next((c for c in cats if SALE.search(c)), None)
        if not sale: n_nosale += 1; continue            # a sold shop item, not a lot
        n_lots += 1
        m = SALE.search(sale)
        year, month = int(m.group(2)), MONTH.get((m.group(1) or "").lower(), 12)
        if (year, month) > (today.year, today.month): n_upcoming += 1; continue
        start = START.search(name); hammer = HAMMER.search(name)
        start = euros(start.group(1)) if start else None
        hammer = euros(hammer.group(2)) if hammer else None
        sold = hammer is not None or bool(re.search(r"\bmüüdud\b|\bsold\b", name, re.I))
        if re.search(r"\bmüümata\b|\bunsold\b", name, re.I): sold = False
        if hammer is not None and start is not None and hammer < start: n_odd += 1
        got = parse(LOTNO.sub("", PRICE_PHRASE.sub(" ", name)))
        if not got: n_unparsed += 1; continue
        artist, title, wyear, tech, dims = got
        aid = "vern-" + str(p.get("id"))
        if aid in seen: continue
        seen.add(aid)
        recs.append({"aid": aid, "artist": artist, "title": title, "year": wyear, "tech": tech, "dims": dims,
                     "house": "Vernissage", "sale": sale, "when": f"{year}-{month:02d}",
                     "start": start, "hammer": hammer, "sold": sold,
                     "url": p.get("permalink") or "https://vernissage.ee"})
    if page % 5 == 0: print(f"  page {page}  lots {len(recs)}", flush=True)
    page += 1; time.sleep(1.0)
    if page > 80: break

recs.sort(key=lambda r: (r["when"], r["artist"], r["title"]))
# one file for every house; this script owns its own house's records in it
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump([r for r in prev if r["house"] != "Vernissage"] + recs, open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
sold = [r for r in recs if r["sold"]]
print(f"\nVERNISSAGE AUCTION RESULTS: {len(recs)}   sold {len(sold)} (with hammer price {sum(1 for r in sold if r['hammer'])})   unsold {len(recs)-len(sold)}")
print(f"  lots seen {n_lots}, upcoming {n_upcoming}, unparsed {n_unparsed}, hammer below start {n_odd}, non-lots skipped {n_nosale}")
print("  sales:", sorted({r["sale"] for r in recs}, key=lambda s: SALE.search(s).group(2)))
for r in recs[:3] + recs[-3:]:
    print(f"   {r['when']} {r['artist'][:18]:18} {r['title'][:28]:28} {r['year'] or '—':5} start {r['start']!s:>6} hammer {r['hammer']!s:>6} {'sold' if r['sold'] else 'unsold'}")
