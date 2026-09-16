# -*- coding: utf-8 -*-
"""Haus Galerii artwork catalogue -> gallery_records.json

Metadata only: artist, title, year, technique, dimensions, and a link back to the
gallery's own page for every record. Prices are deliberately NOT collected — a price
index is a different object from a catalogue of works.
"""
import re, json, os, gzip, time, urllib.request, ssl
from concurrent.futures import ThreadPoolExecutor

BASE = "https://haus.ee"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "gcache"
os.makedirs(CACHE, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def get(url, key):
    p = os.path.join(CACHE, key + ".html.gz")
    # stock changes month to month: a cached page older than a day is fetched again
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > 86400: os.remove(p)
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f:
                h = f.read().decode("utf-8", "replace")
            with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
            return h
        except Exception as e:
            if attempt == 2: print("ERR", url, repr(e)[:70], flush=True); return ""
            time.sleep(3 * (attempt + 1))

FIG = re.compile(r'<figure id="tid(\d+)".*?</figure>', re.S)
def txt(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    for a, b in (("&amp;","&"),("&quot;",'"'),("&#039;","'"),("&nbsp;"," "),("&ndash;","–"),("&rsquo;","’")):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()

def parse(h):
    out = []
    for m in FIG.finditer(h):
        b = m.group(0)
        aut = re.search(r'<strong class="aut">(.*?)</strong>', b, re.S)
        ttl = re.search(r'<em class="title[^"]*">(.*?)</em>', b, re.S)
        yr  = re.search(r'<span class="year">(\d{4})</span>', b)
        tec = re.search(r'<p class="tech[^"]*">(.*?)</p>', b, re.S)
        slug = re.search(r'href="(\?c=all-artworks[^"]*id=\d+)"', b)
        img = re.search(r'<img class="pilt_t t" src="([^"?]+)', b)
        if not (aut and ttl): continue
        title = txt(ttl.group(1))
        if yr: title = re.sub(r'\s*' + yr.group(1) + r'\s*$', '', title).strip()
        # Haus writes "Title. Technique" and the harvester kept the separator: 967 titles
        # ended in a full stop, and a work with no title showed as "--.". Strip the
        # trailing stop unless it closes an initial or an abbreviation; blank the dashes.
        title = re.sub(r'\.\s*$', '', title).strip()
        if re.fullmatch(r'[-–—\s.]*', title): title = ""
        tech = txt(tec.group(1)) if tec else ""
        # "Oil, acrylic, canvas. 120.0 × 130.0 cm" -> technique / dimensions
        dm = re.search(r'([\d.,]+\s*[×x]\s*[\d.,]+(?:\s*[×x]\s*[\d.,]+)?\s*(?:cm|mm))', tech, re.I)
        dims = dm.group(1).strip() if dm else ""
        if dims: tech = tech.replace(dm.group(1), "").strip(" .,")
        out.append({"gid": m.group(1), "artist": aut.group(1).strip(), "title": title,
                    "year": yr.group(1) if yr else None, "tech": tech, "dims": dims,
                    "gallery": "Haus Galerii", "city": "Tallinn",
                    "url": BASE + "/" + slug.group(1).replace("&amp;", "&") if slug else BASE,
                    **({"img": BASE + img.group(1)} if img else {})})
    return out

first = get(f"{BASE}/?c=all-artworks&l=en&cat=0&p=1", "haus_c0_p1")
# hrefs are HTML-escaped ("&amp;p=18"), so do not anchor on a literal & or ?
pages = max([int(x) for x in re.findall(r'p=(\d+)"', first)] or [1])
print(f"Haus: {pages} pages", flush=True)
rows = {r["gid"]: r for r in parse(first)}
def one(p): return parse(get(f"{BASE}/?c=all-artworks&l=en&cat=0&p={p}", f"haus_c0_p{p}"))
with ThreadPoolExecutor(max_workers=3) as ex:
    for i, rs in enumerate(ex.map(one, range(2, pages + 1)), 2):
        for r in rs: rows[r["gid"]] = r
        if i % 10 == 0: print(f"  page {i}/{pages}  works {len(rows)}", flush=True)

recs = list(rows.values())
# Replace only Haus's own records. This was the first harvester and wrote the whole
# file; run on its own after the others existed, it wiped them.
prev = json.load(open("gallery_records.json", encoding="utf-8")) if os.path.exists("gallery_records.json") else []
json.dump([r for r in prev if r.get("gallery") != "Haus Galerii"] + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"\nHAUS WORKS: {len(recs)}")
print(f"  with year      : {sum(1 for r in recs if r['year'])}")
print(f"  with dimensions: {sum(1 for r in recs if r['dims'])}")
print(f"  distinct artists: {len({r['artist'] for r in recs})}")
