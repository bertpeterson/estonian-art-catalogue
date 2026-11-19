# -*- coding: utf-8 -*-
"""Vaal galerii's sales before 2022 -> auction_records.json (house: Vaal galerii)

vaal_auctions.py reads the sales the house's present site draws from its API, spring 2022
on. The ones before stand on the old site, arhiiv.vaal.ee: every sale from spring 2001 to
spring 2021, twelve lots to a page, each lot on a page of its own with the artist and life
dates, title and year, technique, size, starting price and, where it sold, the hammer
price. The kroon years are shown there in euro already (18 000 kr as 1150.41 EUR), so the
prices are taken as they stand, rounded to the euro.

The archive gives no day for a sale, only the year and season its name carries ("2019
kevadoksjon"); a lot's date is the year. It is served over plain http and has no https, so
its pictures cannot be embedded on the site and no lot carries one.

Run by hand, not in CI: a sale of 2009 does not change. A lot page is fetched once and
cached (gcache), so a second run only reads the sale lists. vaal_auctions.py keeps these
lots as "not read this run" (auction_keep.py).
"""
import re, json, os, gzip, time, html, urllib.request
from scrape_util import U as clean

ROOT = "http://arhiiv.vaal.ee"
INDEX = ROOT + "/est/avaleht/oksjon/toimunud_oksjonid"
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
CACHE = "gcache"
HOUSE = "Vaal galerii"
os.makedirs(CACHE, exist_ok=True)

def fetch(url):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
            with urllib.request.urlopen(r, timeout=45) as f:
                return f.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == 2: print("ERR", url, repr(e)[:70], flush=True); return ""
            time.sleep(3 * (attempt + 1))

def get(url, key):
    p = os.path.join(CACHE, key + ".html.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    h = fetch(url)
    if h and "Autor:" in h:                       # an error page is not kept as the lot
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    time.sleep(0.4)
    return h

text = lambda s: clean(html.unescape(re.sub(r"<[^>]+>", " ", s or "")))

def euros(s):
    m = re.search(r"(\d[\d\s]*)(?:[.,](\d\d))?\s*EUR", s or "")
    return round(float(re.sub(r"\s", "", m.group(1)) + "." + (m.group(2) or "0"))) if m else None

def artist_of(s):
    """"27. Sooster, Ülo (1924-1970)" -> lot 27, "Ülo Sooster", "1924–1970"; a living artist
    reads "(s 1936)", and some carry no dates."""
    lot = re.match(r"^(\d+)\s*[.)]\s*", s)
    if lot: s = s[lot.end():]
    life = None
    m = re.search(r"\(([^()]*\d{4}[^()]*)\)\s*$", s)
    if m:
        life = re.sub(r"\s*[-–—]\s*", "–", m.group(1).strip())
        life = re.sub(r"^s\.?\s*(?=\d)", "s ", life)              # "s. 1936", "s.1936": born, as the later sales write it
        s = s[:m.start()]
    s = s.strip(" ,")
    if "," in s:
        last, first = s.split(",", 1)
        s = f"{first.strip()} {last.strip()}"
    return (int(lot.group(1)) if lot else None), clean(s), life

def title_of(s):
    """"Kadakad (1958)", "Päevalilled (1930ndad)": the year stands in brackets after the title."""
    yl = None
    m = re.search(r"\(([^()]*\d{4}[^()]*)\)\s*$", s)
    if m: yl = m.group(1).strip(); s = s[:m.start()].strip()
    if s in ("", "-", "–"): s = "Nimetu"
    return s, yl

def sale_name(title, slug):
    """"2019 kevadoksjon" -> "Vaal galerii kevadoksjon 2019", the way the later sales are named."""
    m = re.match(r"^(\d{4})\s+(.+)$", title)
    year = m.group(1) if m else (re.search(r"(?:19|20)\d\d", slug) or [None])[0]
    return f"{HOUSE} {m.group(2) if m else title}{' ' + year if year else ''}".strip(), year

index = fetch(INDEX)
slugs = sorted(set(re.findall(r"toimunud_oksjonid/([A-Za-z0-9_-]+)", index)))
print(f"VAAL ARCHIVE: {len(slugs)} sales listed", flush=True)

recs, n_unparsed, n_missing = [], 0, 0
for slug in slugs:
    first = fetch(f"{INDEX}/{slug}"); time.sleep(0.4)
    h1 = re.search(r'id="content">\s*<h1>(.*?)</h1>', first, re.S)
    sale, year = sale_name(text(h1.group(1)) if h1 else slug, slug)
    if not year: print("  no year for", slug); continue
    pages = [first] + [fetch(f"{INDEX}/{slug}/?page={p}") for p in sorted({int(p) for p in re.findall(r"\?page=(\d+)", first)})]
    paths = []
    for pg in pages:
        for p in re.findall(r"open_window\('([^']+pic_id-\d+)'", pg or ""):
            if p not in paths: paths.append(p)
    total = re.search(r"_count_all=(\d+)", first)
    n = 0
    for path in paths:
        pid = re.search(r"pic_id-(\d+)", path).group(1)
        page = get(ROOT + path, f"vaalarh_{pid}")
        f = {text(k).strip(" :"): text(v) for k, v in re.findall(r'class="field">(.*?)</td>\s*<td[^>]*>(.*?)</td>', page or "", re.S)}
        if not f.get("Autor"): n_missing += 1; continue
        lot, artist, life = artist_of(f["Autor"])
        title, yl = title_of(f.get("Teos", ""))
        if not re.match(r"^[^\d]{3,60}$", artist): n_unparsed += 1; continue
        y4 = re.search(r"(1[5-9]\d\d|20[0-2]\d)", yl or "")
        dm = re.search(r"\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?", f.get("Mõõdud", ""))
        start, hammer = euros(f.get("Alghind")), euros(f.get("Lõpphind"))
        recs.append({"aid": "vaalarh-" + pid, "artist": artist, "title": title,
                     "year": y4.group(1) if y4 else None, "yl": yl,
                     "tech": f.get("Tehnika", ""), "dims": (re.sub(r"\s*[x×]\s*", " x ", dm.group(0)).replace(",", ".") + " cm") if dm else "",
                     "life": life, "house": HOUSE, "sale": sale, "when": year, "date": year, "surl": f"{INDEX}/{slug}",
                     "start": start, "hammer": hammer, "sold": hammer is not None,
                     "url": ROOT + path, "img": None, "lot": lot})
        n += 1
    print(f"  {slug:22} {sale[:44]:44} lots {n}" + (f"  (the sale counts {total.group(1)})" if total and int(total.group(1)) != n else ""), flush=True)

recs.sort(key=lambda r: (r["date"], r["sale"], r["lot"] or 0))
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
read = {r["sale"] for r in recs}
kept = [r for r in prev if str(r["aid"]).startswith("vaalarh-") and r["sale"] not in read]     # a sale that would not load keeps its lots
out = [r for r in prev if not str(r["aid"]).startswith("vaalarh-")] + kept + recs
json.dump(sorted(out, key=lambda r: (r["house"], str(r.get("date") or r.get("when") or ""), str(r["aid"]))), open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
sold = [r for r in recs if r["sold"]]
print(f"\nVAAL ARCHIVE RESULTS: {len(recs)}   sold {len(sold)}   unsold {len(recs) - len(sold)}   sales {len(read)}   kept from before {len(kept)}")
print(f"  lot pages missing {n_missing}, unparsed {n_unparsed}, with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with life dates {sum(1 for r in recs if r['life'])}, no start price {sum(1 for r in recs if r['start'] is None)}")
for r in recs[:3] + recs[-3:]:
    print(f"   {r['date']:5} {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':5} {r['tech'][:16]:16} start {r['start']!s:>6} hammer {r['hammer']!s:>6}")
