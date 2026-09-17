# -*- coding: utf-8 -*-
"""Vaal galerii auction results -> auction_records.json (house: Vaal galerii)

Vaal has held a sale each spring and autumn since 2021, and its site draws each
sale from a small JSON API (oksjon.vaal.ee/api/auction, /api/item): the lots by
day with the day's date, artist and life dates, technique, starting price and
hammer price where it sold, and per lot the year and size. The API is what the
public page itself loads; it is read the same way, one call per sale and one per
lot, the lot calls cached since a past sale does not change.

A lot with no hammer price did not sell and is kept as that. A sale is a result
once every day of it is past and it has hammer prices; the API's own status lags
(spring 2026 stood at "active_hall" months after the hall had emptied). The 2021
sale predates the API and its page lists starting prices only; there is nothing
to take from it.
"""
import unicodedata, re, json, os, gzip, time, html, datetime, urllib.request, ssl

BASE = "https://www.vaal.ee"
API = "https://oksjon.vaal.ee/api"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "gcache"
os.makedirs(CACHE, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html"})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f:
                return f.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == 2: print("ERR", url, repr(e)[:70], flush=True); return ""
            time.sleep(3 * (attempt + 1))

def get(url, key):
    p = os.path.join(CACHE, key + ".json.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    h = fetch(url)
    if h:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    time.sleep(0.4)
    return h

def slugify(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'^-+|-+$', '', re.sub(r'[^a-z0-9]+', '-', t))[:60] or 'teos'
clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
euros = lambda s: int(re.sub(r"[^\d]", "", clean(s))) if re.search(r"\d", clean(s)) else None

# the sales: the page for each carries the API tag it loads
index = fetch(f"{BASE}/oksjonid")
slugs = sorted({s for s in re.findall(r'href="/oksjonid/(\d{4}-[a-z]+)"', index)})
print(f"VAAL: {len(slugs)} sales listed", flush=True)

today = datetime.date.today().isoformat()
recs, n_open, n_unparsed = [], 0, 0
for slug in slugs:
    page = fetch(f"{BASE}/oksjonid/{slug}"); time.sleep(0.5)
    tag = re.search(r"getItems\('(\d+)'\)", page)
    if not tag: print("  no API tag for", slug); continue
    data = fetch(f"{API}/auction?auction={tag.group(1)}"); time.sleep(0.5)
    try: a = json.loads(data)["auction"]
    except Exception: print("  bad API answer for", slug); continue
    days = a.get("days") or []
    dates = [f"{m.group(3)}-{m.group(2)}-{m.group(1)}" for d in days for m in [re.search(r"(\d{2})\.(\d{2})\.(\d{4})", d.get("auction_day_description") or "")] if m]
    ended = a.get("auction_status") == "ended" or (dates and max(dates) < today and any(i.get("item_price_final") for d in days for i in d.get("item", [])))
    if not ended: n_open += 1; continue
    sale = clean(a.get("auction_name") or slug)
    n = 0
    for day in a.get("days") or [{"auction_day_description": "", "item": a.get("item", [])}]:
        dm = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", day.get("auction_day_description") or "")
        when = f"{dm.group(3)}-{dm.group(2)}-{dm.group(1)}" if dm else slug[:4]
        for it in day.get("item", []):
            artist = clean(it.get("item_author"))
            title = re.sub(r"^\d+\.\s*", "", clean(it.get("item_name")))          # "12. Lamav akt"
            if not title or not re.match(r"^[^\d]{3,60}$", artist): n_unparsed += 1; continue
            start, hammer = euros(it.get("item_price_start")), euros(it.get("item_price_final"))
            det = get(f"{API}/item?item={it['item_id']}", f"vaalauc_{it['item_id']}")
            try: d = json.loads(det)["item"]
            except Exception: d = {}
            yl = clean(d.get("item_year") or "")
            y4 = re.search(r"(1[6-9]\d\d|20[0-2]\d)", yl)
            dims = clean(d.get("item_dimensions") or d.get("item_size") or "")
            dm2 = re.search(r"\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?", dims)
            dims = (re.sub(r"\s*[x×]\s*", " x ", dm2.group(0)).replace(",", ".") + " cm") if dm2 else ""
            life = clean(it.get("item_author_datum") or "")
            recs.append({"aid": "vaal-" + str(it["item_id"]), "artist": artist, "title": title,
                         "year": y4.group(1) if y4 else None, "yl": yl or None,
                         "tech": clean(it.get("item_technique") or ""), "dims": dims, "life": life or None,
                         "house": "Vaal galerii", "sale": sale, "when": when[:7], "date": when,
                         "start": start, "hammer": hammer, "sold": hammer is not None,
                         # the lot page reads its id from between "?" and the first "-", so
                         # the address needs a slug after the id or it shows nothing
                         "url": f"{BASE}/oksjonid/teos?{it['item_id']}-{slugify(title)}"})
            n += 1
    print(f"  {slug} {sale[:36]:36} lots {n}", flush=True)

recs.sort(key=lambda r: (r["date"], r["artist"], r["title"]))
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump([r for r in prev if r["house"] != "Vaal galerii"] + recs, open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
sold = [r for r in recs if r["sold"]]
print(f"\nVAAL AUCTION RESULTS: {len(recs)}   sold {len(sold)}   unsold {len(recs) - len(sold)}   sales {len({r['sale'] for r in recs})}")
print(f"  sales still open {n_open}, lots unparsed {n_unparsed}, with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with life dates {sum(1 for r in recs if r['life'])}")
for r in recs[:3] + recs[-3:]:
    print(f"   {r['date']:10} {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':5} {r['tech'][:16]:16} start {r['start']!s:>6} hammer {r['hammer']!s:>6}")
