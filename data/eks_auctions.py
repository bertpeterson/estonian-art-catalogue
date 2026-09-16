# -*- coding: utf-8 -*-
"""E-Kunstisalong auction results -> auction_records.json (house: E-Kunstisalong)

Tartu's E-Kunstisalong, the oldest private gallery in the country (1997), has held
two sales a year since 1999 -- fifty-seven by 2026 -- and keeps a page per sale.
From about 2018 the page lists the lots with the outcome on each:
    Alg: € 1 500, lõpp: € 1 700     sold, with the hammer price
    Alg: € 2 500 müüdud              sold at the starting price
    Alg: € 1 600                     unsold
Each lot card carries the artist, the lot number and title, and a line of year,
technique and size ("1970. Õli, lõuend. 60 x 73. Signatuuriga."). The sale's date
is on the list of sales ("14.05.2026 Tartu galeriis kell 17"). The earlier sales
have a page but no lots on it; there is nothing to take from those.

The pages are ISO-8859-4. Sale pages are cached; a past sale does not change, but a
sale not yet held is fetched again each run until it has results.
"""
import re, json, os, gzip, time, html, datetime, urllib.request, ssl

BASE = "https://www.e-kunstisalong.ee"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "gcache"
os.makedirs(CACHE, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f:
                return f.read().decode("iso-8859-4", "replace")
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

# the sales, with their dates, from the list page
index = fetch(f"{BASE}/E-kunstisalongi_oksjonid_756")
sales = []
# each sale is a card: <a href='56_E-kunstisalongi_oksjon_13734'>...</div>56. E-Kunstisalongi oksjon<br><span class=autor>14.05.2026 Tartu galeriis kell 17</span></a>
for m in re.finditer(r"<a href='([^']+)'[^>]*>(?:(?!</a>\s*</span>).)*?</div>\s*([^<]{3,80}?)<br><span class=autor>(\d{2})\.(\d{2})\.(\d{4})", index, re.S):
    url, name = m.group(1), clean(m.group(2))
    if not re.search(r"oksjon", url + name, re.I): continue
    sales.append((f"{BASE}/{url.lstrip('/')}", name, f"{m.group(5)}-{m.group(4)}-{m.group(3)}"))
seen_urls = set(); sales = [s for s in sales if not (s[0] in seen_urls or seen_urls.add(s[0]))]
print(f"E-KUNSTISALONG: {len(sales)} sales listed", flush=True)

CARD = re.compile(r"<span class='toot_hr_jn alapealkiri'>(.*?)</span><span class='toot_hr_jn'>(.*?)</span></b><span class=toot_hr_jn>(.*?)</span><span >Alg:\s*<b>(.*?)</b></span>", re.S)
today = datetime.date.today().isoformat()
recs, n_open, n_empty, n_unparsed = [], 0, 0, 0
for url, sale, date in sales:
    if date > today: n_open += 1; continue
    key = "eksauc_" + re.sub(r"\W+", "_", url.rsplit("/", 1)[-1])
    h = get(url, key)
    cards = CARD.findall(h)
    if not cards:
        n_empty += 1
        p = os.path.join(CACHE, key + ".html.gz")
        if os.path.exists(p) and date > (datetime.date.today() - datetime.timedelta(days=60)).isoformat(): os.remove(p)   # results may come later
        continue
    n = 0
    for artist, lot, line, price in cards:
        artist, lot, line, price = clean(artist), clean(lot), clean(line), clean(price)
        # the older sales list the title without a lot number
        lm = re.match(r"^(?:(\d+)\.\s*)?(.+)$", lot)
        if not lm or not re.match(r"^[^\d]{3,60}$", artist): n_unparsed += 1; continue
        lotno, title = lm.group(1) or str(n + 1), lm.group(2).strip()
        # "1970. Õli, lõuend. 60 x 73. Signatuuriga." / "U1925. Õli, lõuend. 53,2 x 70,5. Signatuurita."
        # older sales run the line together: "1961-1964 Õli,papp 50 x 70"; the year is
        # whatever leads, the size whatever measures, the medium what sits between
        dm = re.search(r"(?:\b(?:ava|lm|plm|km)\s*)?(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)", line, re.I)
        head = line[:dm.start()] if dm else line
        ym = re.match(r"^\s*(U?\s*\d{4}(?:\s*[-–]\s*\d{2,4})?(?:ndad|\.?\s*a)?|\d{4}\s*[-–]\s*\d{4}ndad|\d{2}\.\s*saj\.?[^.]*)\.?\s*", head)
        yl = ym.group(1).strip() if ym else ""
        rest = head[ym.end():] if ym else head
        y4 = re.search(r"(1[5-9]\d\d|20[0-2]\d)", yl)
        tech = next((t.strip(" ,.") for t in re.split(r"\.\s*", rest) if re.search(r"[A-Za-zÕÄÖÜõäöü]", t) and not re.search(r"signatuur|signeeri|raam|dateeri|numm|nimetu", t, re.I)), "")
        tech = re.sub(r",(?=\S)", ", ", tech)
        dims = (re.sub(r"\s*[x×]\s*", " x ", dm.group(1)).replace(",", ".") + " cm") if dm else ""
        start = euros(re.split(r",|müüdud|lõpp", price)[0])
        hm = re.search(r"lõpp\s*:?\s*€?\s*([\d\s]+)", price)
        hammer = euros(hm.group(1)) if hm else (start if "müüdud" in price else None)
        sold = hammer is not None
        recs.append({"aid": f"eks-{key[7:]}-{lotno}", "artist": artist, "title": title,
                     "year": y4.group(1) if y4 else None, "yl": yl.strip("U ") or None, "tech": tech.strip(" ,."), "dims": dims,
                     "house": "E-Kunstisalong", "sale": sale, "when": date[:7], "date": date,
                     "start": start, "hammer": hammer, "sold": sold, "url": url})
        n += 1
    print(f"  {date} {sale[:36]:36} lots {n}", flush=True)

recs.sort(key=lambda r: (r["date"], r["artist"], r["title"]))
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump([r for r in prev if r["house"] != "E-Kunstisalong"] + recs, open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
sold = [r for r in recs if r["sold"]]
print(f"\nE-KUNSTISALONG AUCTION RESULTS: {len(recs)}   sold {len(sold)}   unsold {len(recs) - len(sold)}   sales {len({r['sale'] for r in recs})}")
print(f"  sales still to come {n_open}, sales with no lot list {n_empty}, lots unparsed {n_unparsed}, with year {sum(1 for r in recs if r['year'])}, with medium {sum(1 for r in recs if r['tech'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:3] + recs[-3:]:
    print(f"   {r['date']} {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':5} {r['tech'][:16]:16} start {r['start']!s:>6} hammer {r['hammer']!s:>6}")
