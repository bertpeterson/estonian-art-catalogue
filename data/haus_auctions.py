# -*- coding: utf-8 -*-
"""Haus Galerii auction results -> auction_records.json (house: Haus Galerii)

Haus has held Estonian art auctions every spring and autumn since 1997 and publishes
the whole archive: one page per sale, one figure per lot, with the starting price,
the last bid and the hammer price ("Haamrihind") where there was one. It is the
longest continuous record of the Estonian art market there is. Prices from the
kroon years are shown by the house in euro, converted at the fixed rate; they are
taken as shown.

The Estonian catalogue is read, as the catalogue keeps titles the way the holder
wrote them. A lot with a hammer price sold; one without did not. A sale whose date
is still ahead is not a result and is left until it is. Pages are cached, since a
past sale does not change; the list of sales is fetched fresh each run.
"""
import re, json, os, gzip, time, html, datetime, urllib.request, ssl

BASE = "https://haus.ee"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "gcache"
os.makedirs(CACHE, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "et"})
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
    time.sleep(0.8)
    return h

clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
euros = lambda s: int(re.sub(r"[^\d]", "", s)) if re.search(r"\d", s or "") else None
DIMS = re.compile(r"(\d+(?:[.,]\d+)?\s*[×x]\s*\d+(?:[.,]\d+)?(?:\s*[×x]\s*\d+(?:[.,]\d+)?)?)\s*cm")

# the list of sales: five pages, newest first
sales = {}
for pg in ("", "2", "3", "4", "5", "6"):
    h = fetch(f"{BASE}/?c=toimunud-oksjonid&l=et&_order=date.dsc&ps=25&_s=1&p={pg}")
    for aid, title, when in re.findall(r'<article id="toimunud-oksjonid-id(\d+)".*?<h3 class="title">(.*?)</h3>.*?<time datetime="([^"]+)"', h or "", re.S):
        sales[aid] = (clean(title).strip(" .-"), when[:10])
    time.sleep(0.8)
print(f"HAUS: {len(sales)} sales listed", flush=True)

today = datetime.date.today().isoformat()
recs, n_upcoming, n_unparsed = [], 0, 0
for aid, (sale, when) in sorted(sales.items(), key=lambda x: x[1][1]):
    if when > today: n_upcoming += 1; continue
    h = get(f"{BASE}/?c=toimunud-oksjonid&l=et&id={aid}", f"hausauc_{aid}")
    for fig in re.findall(r'<figure class="artwork.*?</figure>', h, re.S):
        item = re.search(r'data-id="(\d+)"', fig)
        aut = re.search(r'<em class="aut">(.*?)</em>', fig, re.S)
        tit = re.search(r'<strong class="title">(.*?)</strong>', fig, re.S)
        tech = re.search(r'<p class="tech">(.*?)</p>', fig, re.S)
        if not (item and aut and tit): n_unparsed += 1; continue
        t = tit.group(1)
        ym = re.search(r'<span class="year">(.*?)</span>', t)
        year = clean(ym.group(1)) if ym else ""
        title = clean(re.sub(r'<span class="year">.*?</span>', "", t)).rstrip(" .")
        # the early catalogues were typed in capitals ("SEISEV NAINE MAASTIKUL"); that is
        # the typewriter, not the title, and is set in sentence case
        if len(title) > 3 and title == title.upper() and re.search(r"[A-ZÄÖÜÕ]{2}", title):
            title = ". ".join(p[:1].upper() + p[1:].lower() for p in title.split(". "))
        artist = clean(aut.group(1))
        if not title or not re.match(r"^[^\d]{3,60}$", artist): n_unparsed += 1; continue
        tx = clean(tech.group(1)) if tech else ""
        dm = DIMS.search(tx)
        dims = re.sub(r"\s*[×x]\s*", " x ", dm.group(1)).replace(",", ".") + " cm" if dm else ""
        medium = re.sub(r"[.,;\s]+$", "", DIMS.sub("", tx)).strip() if tx else ""
        prices = dict((clean(k).lower(), clean(v)) for k, v in re.findall(r'<div class="price">(.*?)<strong class="price[^"]*">(.*?)</strong>', fig, re.S))
        start = euros(prices.get("alghind", ""))
        hammer = euros(prices.get("haamrihind", ""))
        # a hammer price with no bid in the room is a sale made after the sale, at the
        # price the house then agreed -- often below the start; the house still prints
        # it as Haamrihind on the sale page, and it is kept, marked as such
        after = hammer is not None and not re.search(r"\d", prices.get("viimane pakkumine", ""))
        y4 = re.match(r"(\d{4})", year)
        recs.append({"aid": "haus-" + item.group(1), "artist": artist, "title": title,
                     "year": y4.group(1) if y4 else None, "yl": year or None, "tech": medium, "dims": dims,
                     "house": "Haus Galerii", "sale": sale, "when": when[:7], "date": when,
                     "start": start, "hammer": hammer, "sold": hammer is not None, "after": after,
                     "url": f"{BASE}/?c=toimunud-oksjonid&l=et&id={aid}&item={item.group(1)}"})
    print(f"  {when} {sale[:40]:40} lots so far {len(recs)}", flush=True)

recs.sort(key=lambda r: (r["date"], r["artist"], r["title"]))
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump([r for r in prev if r["house"] != "Haus Galerii"] + recs, open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
sold = [r for r in recs if r["sold"]]
print(f"\nHAUS AUCTION RESULTS: {len(recs)}   sold {len(sold)}   unsold {len(recs) - len(sold)}   sales {len({r['sale'] + r['date'] for r in recs})}")
print(f"  upcoming sales left out {n_upcoming}, lots unparsed {n_unparsed}, with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:3] + recs[-3:]:
    print(f"   {r['date']} {r['artist'][:20]:20} {r['title'][:28]:28} {r['year'] or '—':5} start {r['start']!s:>6} hammer {r['hammer']!s:>6}")
