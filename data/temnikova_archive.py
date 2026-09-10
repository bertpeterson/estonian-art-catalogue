# -*- coding: utf-8 -*-
"""Temnikova & Kasela — unlisted exhibition archive.

The gallery links 7 exhibitions; ids reach past 416. Walking an id space is not the
same act as following published links, so this is deliberately conservative:

  * one request at a time, 1.5s apart, with an identifying User-Agent
  * a page is accepted ONLY if its date range parses cleanly and has already ENDED.
    Anything undated, malformed, or still running or upcoming is skipped — an
    unannounced show is the one thing here that could actually harm the gallery.
  * metadata only, no prices, and every record links back to the gallery's page.
"""
import re, json, os, gzip, time, datetime, urllib.request, ssl

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
BASE = "https://temnikova.ee"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
os.makedirs("gcache", exist_ok=True)
TODAY = datetime.date.today()
MAX_ID = 420

def get(url, key):
    p = f"gcache/{key}.html.gz"
    if os.path.exists(p):
        with gzip.open(p,"rt",encoding="utf-8") as f: return f.read()
    try:
        r = urllib.request.Request(url, headers={"User-Agent":UA,"Accept-Language":"en"})
        with urllib.request.urlopen(r, timeout=35, context=ctx) as f:
            h = f.read().decode("utf-8","replace")
    except Exception:
        h = ""
    with gzip.open(p,"wt",encoding="utf-8") as f: f.write(h)
    time.sleep(1.5)
    return h

def txt(s):
    s = re.sub(r'<[^>]+>',' ',s)
    for a,b in (("&amp;","&"),("&#039;","'"),("&quot;",'"'),("&nbsp;"," "),("&ndash;","–"),("&rsquo;","’")):
        s = s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

DATEBLOCK = re.compile(r'<span class="date">(.*?)</span>', re.S)
TIME = re.compile(r'<time datetime="(\d{4})-(\d{2})-(\d{2})')
ART  = re.compile(r'<article id="id(\d+)".*?</article>', re.S)

def ended(h):
    """(True, end_date) only when the run is well-formed and already over."""
    b = DATEBLOCK.search(h)
    if not b: return False, None
    ds = TIME.findall(b.group(1))
    if len(ds) < 2: return False, None
    try:
        a = datetime.date(*map(int, ds[0])); z = datetime.date(*map(int, ds[1]))
    except ValueError: return False, None
    if z < a: return False, None                 # malformed range
    return (z < TODAY), z

recs, stats = [], {"fetched":0,"empty":0,"skipped_dates":0,"accepted":0}
for eid in range(1, MAX_ID + 1):
    h = get(f"{BASE}/?c=exhibition&l=en&id={eid}", f"tk_ex{eid}")
    stats["fetched"] += 1
    if not h or '<article id="id' not in h:
        stats["empty"] += 1
    else:
        ok, end = ended(h)
        if not ok:
            stats["skipped_dates"] += 1
        else:
            n = 0
            for m in ART.finditer(h):
                b = m.group(0)
                a = re.search(r'<strong class="aut">(.*?)</strong>', b, re.S)
                t = re.search(r'<h3>(.*?)</h3>', b, re.S)
                tech = re.search(r'<span class="tech">(.*?)</span>', b, re.S)
                yr = re.search(r'<span class="year">(\d{4})</span>', b)
                if not (a and t): continue
                tc = txt(tech.group(1)) if tech else ""
                dm = re.search(r'([\d.,]+\s*[×x]\s*[\d.,]+(?:\s*[×x]\s*[\d.,]+)?\s*(?:cm|mm))', tc, re.I)
                dims = dm.group(1).strip() if dm else ""
                if dims: tc = tc.replace(dm.group(1),"").strip(" .,")
                recs.append({"gid":"tk-"+m.group(1), "artist":txt(a.group(1)),
                             "title":txt(t.group(1)).strip("'’\""), "year":yr.group(1) if yr else None,
                             "tech":tc, "dims":dims, "gallery":"Temnikova & Kasela", "city":"Tallinn",
                             "url":f"{BASE}/?c=exhibition&l=en&id={eid}"})
                n += 1
            if n: stats["accepted"] += 1
    if eid % 40 == 0: print(f"  id {eid}/{MAX_ID}  works {len(recs)}  {stats}", flush=True)

seen, out = set(), []
for r in recs:
    if r["gid"] in seen: continue
    seen.add(r["gid"]); out.append(r)
prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("tk-")]
json.dump(keep + out, open("gallery_records.json","w",encoding="utf-8"), ensure_ascii=False)
print(f"\nDONE {stats}")
print(f"TEMNIKOVA ARCHIVE WORKS: {len(out)}   artists: {len({r['artist'] for r in out})}")
print(f"  gallery_records.json now: {len(keep)+len(out)}")
