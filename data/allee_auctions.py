# -*- coding: utf-8 -*-
"""Allee galerii auction results -> auction_records.json (house: Allee galerii)

Allee has held Estonian art auctions each spring and autumn since 2020 and keeps the
lots online, one page per sale: the lot line ("Eduard Wiiralt “Viljandi maastik”,
1943. plm 39,2 x 64 cm"), the starting price and, where it sold, the hammer price.
The lot's own page adds the medium ("Kuivnõel paberil."), so each lot page is read
once and cached; a past sale does not change. A lot with no price block at all was
never offered as a lot and is left out; one with a starting price and no hammer
price did not sell, and is kept as that.

The house does not print the sale date on these pages; the season in the sale's
name places it in the year -- spring in May, autumn in November -- for ordering.
"""
import re, json, os, gzip, time, html, datetime, urllib.request, ssl

BASE = "https://alleegalerii.ee"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "gcache"
os.makedirs(CACHE, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f:
                return f.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == 2: print("ERR", url, repr(e)[:70], flush=True); return ""
            time.sleep(3 * (attempt + 1))

def get(url, key):
    p = os.path.join(CACHE, key + ".html.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    h = fetch(url)
    if h:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    time.sleep(10)      # the crawl delay alleegalerii.ee asks for
    return h

clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
euros = lambda s: int(re.sub(r"[^\d]", "", s)) if re.search(r"\d", s or "") else None
# Eduard Wiiralt “Viljandi maastik”, 1943. plm 39,2 x 64 cm   /   Urmas Pedanik “Teerist” 1983. 85 x 115
# The quotes bound the title; what follows is the dating up to the first full stop, and
# the size wherever it sits -- "Km 36 x 52,5 cm", "d=52 cm", "Koos alusega: 83 x 43 x 20 cm".
LOT = re.compile(r"^(?P<a>[^“\"„]+?)\s*[“\"„](?P<t>.+?)[”\"“]\s*,?\s*(?P<rest>.*)$", re.S)
DIMS = re.compile(r"(?:\b(?:plm|km|lm|vm|ava)\s*)?(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*(?:cm)?|d\s*=\s*(\d+(?:[.,]\d+)?)\s*cm", re.I)
SALE = re.compile(r"(kevad|suve|sügis|talve)?oksjon\s*(\d{4})", re.I)
MONTH = {"kevad": 5, "suve": 7, "sügis": 11, "talve": 2}

index = fetch(f"{BASE}/kunstioksjon/")
cats = {}
for slug, name in re.findall(r'href="' + BASE + r'/kunstioksjon-kategooria/([^/"]+)/"[^>]*>\s*<span[^>]*>(.*?)</span>', index, re.S):
    if SALE.search(clean(name)): cats[slug] = clean(name)
print(f"ALLEE: {len(cats)} sales listed", flush=True)

LOTS = json.load(open("allee_lots.json", encoding="utf-8")) if os.path.exists("allee_lots.json") else {}
today = datetime.date.today()
recs, n_upcoming, n_unparsed, n_nolot = [], 0, 0, 0
coming = []
# the coming sales' days, from the auction page: "Sügisoksjonid 2026: 13.-15. novembril"
DAYS = {(s.lower(), int(y)): int(d) for s, y, d in re.findall(r"(Kevad|Sügis|Suve|Talve)oksjonid\s+(\d{4}):\s*(\d{1,2})\.", clean(index))}
for slug, sale in cats.items():
    m = SALE.search(sale)
    year, month = int(m.group(2)), MONTH.get((m.group(1) or "").lower(), 12)
    if (year, month) > (today.year, today.month) and not re.search(r"Alghind", fetch(f"{BASE}/kunstioksjon-kategooria/{slug}/") or ""):
        n_upcoming += 1; continue                                    # announced, no lots online yet
    when = f"{year}-{month:02d}"
    h = fetch(f"{BASE}/kunstioksjon-kategooria/{slug}/"); time.sleep(0.8)
    # a sale is still to come if its month is ahead, or it is this month and no lot
    # has a hammer price yet -- it must not be recorded as a sale where nothing sold
    ahead = (year, month) > (today.year, today.month) or ((year, month) == (today.year, today.month) and "Haamrihind" not in (h or ""))
    if ahead: n_upcoming += 1
    day = DAYS.get(((m.group(1) or "").lower(), year))
    date = f"{year}-{month:02d}-{day:02d}" if day else when
    for art in re.finditer(r'<article id="post-(\d+)".*?</article>', h, re.S):
        pid, body = art.group(1), art.group(0)
        url = re.search(r'href="(' + BASE + r'/kunstioksjon/[^"]+)"', body)
        line = re.search(r'rel="bookmark">(.*?)</a>', body, re.S)
        prices = re.search(r'portfolio-related-auction">(.*?)</div>', body, re.S)
        if not (url and line and prices): n_nolot += 1; continue
        pt = clean(prices.group(1))
        sm = re.search(r"Alghind:\s*([\d\s]+)€", pt); hm = re.search(r"Haamrihind:\s*([\d\s]+)€", pt)
        start = euros(sm.group(1)) if sm else None
        hammer = euros(hm.group(1)) if hm else None
        if start is None and hammer is None: n_nolot += 1; continue
        lm = LOT.match(clean(line.group(1)))
        # "Lepo Mikko triptühhon “Inimesed ja maa”": a trailing lower-case word is a form, not a name
        artist = re.sub(r"(\s+[a-zäöüõšž][^\s]*)+$", "", lm.group("a").strip()) if lm else ""
        if not lm or not re.match(r"^[^\d]{3,60}$", artist): n_unparsed += 1; continue
        title, rest = lm.group("t").strip(), lm.group("rest")
        yl = re.split(r"\.\s|\s(?=(?:plm|km|lm|vm|ava|d\s*=)\b)", rest, 1, flags=re.I)[0].strip(" ,.")
        if not re.search(r"\d{4}|ndad|sajand|dateerimata", yl, re.I): yl = ""
        dm = DIMS.search(rest)
        dims = (re.sub(r"\s*[x×]\s*", " x ", dm.group(1)).replace(",", ".") + " cm") if dm and dm.group(1) \
               else (f"d {dm.group(2).replace(',', '.')} cm" if dm and dm.group(2) else "")
        y4 = re.match(r"(\d{4})", yl)
        if ahead:                                                     # a coming lot: the listing is enough; its page is read once it has a result
            coming.append({"house": "Allee galerii", "sale": sale, "date": date, "artist": artist, "title": title,
                           "year": y4.group(1) if y4 else None, "yl": yl or None, "tech": LOTS.get(pid, ""), "dims": dims,
                           "start": start, "url": url.group(1)})
            continue
        # the lot page: the medium is the first sentence of the description block. A
        # past lot's page does not change, and at the ten-second delay the house asks
        # for, 2,000 of them are six hours: the medium once read is kept in
        # allee_lots.json and the page is not fetched again.
        if pid in LOTS:
            medium = LOTS[pid]
            recs.append({"aid": "allee-" + pid, "artist": artist, "title": title,
                         "year": y4.group(1) if y4 else None, "yl": yl or None, "tech": medium, "dims": dims,
                         "house": "Allee galerii", "sale": sale, "when": when,
                         "start": start, "hammer": hammer, "sold": hammer is not None, "url": url.group(1)})
            continue
        lp = get(url.group(1), f"alleeauc_{pid}")
        # ...between the sale's heading and the size table: "Kuivnõel paberil. 1943." on
        # the newer pages, "Õli paberil, 1946." on the older; the year is the lot line's
        # -- read as text, since the older pages' markup is broken around it: the line
        # after the sale's name, up to the size table
        tx = html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"<script.*?</script>|<style.*?</style>", "", lp, flags=re.S)))
        lines = [l.strip() for l in tx.split("\n") if l.strip()]
        medium = ""
        for k, l in enumerate(lines):
            if l.lower() == sale.lower() and k + 1 < len(lines) and lines[k + 1] != "Mõõdud":
                medium = lines[k + 1]; break
        medium = re.sub(r"[,.;]?\s*(?:\d{4}|\d{2,4}\s*[-–/]\s*\d{2,4}|\d{4}ndad).*$", "", medium).strip(" ,.;")
        if not medium or re.match(r"^\d", medium) or len(medium) > 60 or re.search(r"alghind|haamrihind|€|eur", medium, re.I): medium = ""
        if lp: LOTS[pid] = medium
        recs.append({"aid": "allee-" + pid, "artist": artist, "title": title,
                     "year": y4.group(1) if y4 else None, "yl": yl or None, "tech": medium, "dims": dims,
                     "house": "Allee galerii", "sale": sale, "when": when,
                     "start": start, "hammer": hammer, "sold": hammer is not None, "url": url.group(1)})
    print(f"  {when} {sale[:32]:32} lots so far {len(recs)}", flush=True)

json.dump(LOTS, open("allee_lots.json", "w", encoding="utf-8"), ensure_ascii=False)
recs.sort(key=lambda r: (r["when"], r["artist"], r["title"]))
# the sales still to come: their lots, with the starting price, for upcoming.py
from upcoming import emit
emit("Allee galerii", [{"house": r["house"], "sale": r["sale"], "date": r.get("date") or r.get("when"), "artist": r["artist"], "title": r["title"],
                  "year": r.get("year"), "yl": r.get("yl"), "tech": r.get("tech") or "", "dims": r.get("dims") or "", "start": r.get("start"), "url": r.get("url")}
                 for r in coming])
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump(sorted([r for r in prev if r["house"] != "Allee galerii"] + recs, key=lambda r: (r["house"], str(r.get("date") or r.get("when") or ""), str(r["aid"]))), open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
sold = [r for r in recs if r["sold"]]
print(f"\nALLEE AUCTION RESULTS: {len(recs)}   sold {len(sold)}   unsold {len(recs) - len(sold)}   sales {len({r['sale'] for r in recs})}")
print(f"  upcoming sales left out {n_upcoming}, lots unparsed {n_unparsed}, without a price block {n_nolot}, with medium {sum(1 for r in recs if r['tech'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:3] + recs[-3:]:
    print(f"   {r['when']} {r['artist'][:20]:20} {r['title'][:28]:28} {r['year'] or '—':5} {r['tech'][:18]:18} start {r['start']!s:>6} hammer {r['hammer']!s:>6}")
