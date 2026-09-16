# -*- coding: utf-8 -*-
"""Temnikova & Kasela -> appends to gallery_records.json.

Only exhibitions the gallery actually links from its own listing pages are fetched.
Exhibition ids run far higher than what is published, but enumerating an unlisted id
space is not the same act as following published links, so we do not.
Metadata only, no prices.
"""
import re, json, os, gzip, time, urllib.request, ssl
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
os.makedirs("gcache", exist_ok=True)
BASE = "https://temnikova.ee"

def get(url, key):
    p = f"gcache/{key}.html.gz"
    # stock changes month to month: a cached page older than a day is fetched again
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > 86400: os.remove(p)
    if os.path.exists(p):
        with gzip.open(p,"rt",encoding="utf-8") as f: return f.read()
    try:
        r = urllib.request.Request(url, headers={"User-Agent":UA,"Accept-Language":"en"})
        with urllib.request.urlopen(r, timeout=40, context=ctx) as f:
            h = f.read().decode("utf-8","replace")
    except Exception as e:
        print("ERR", url, repr(e)[:60]); return ""
    with gzip.open(p,"wt",encoding="utf-8") as f: f.write(h)
    time.sleep(1)
    return h

def txt(s):
    s = re.sub(r'<[^>]+>',' ',s)
    for a,b in (("&amp;","&"),("&#039;","'"),("&quot;",'"'),("&nbsp;"," "),("&ndash;","–")): s=s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

ids = set()
# the current shows, and the past ones a year at a time (the site moved its archive
# under ?c=past-exhibitions&s.date=YYYY in 2026; the old ?c=past now redirects home)
h = get(BASE+"/?c=exhibitions&l=en", "tk_c_exhibitions_l_en")
ids |= set(re.findall(r'c=exhibition&(?:amp;)?l=en[^"]*id=(\d+)', h))
years = sorted(set(re.findall(r'c=past-exhibitions&(?:amp;)?l=en&(?:amp;)?s\.date=(\d{4})', h)))
for y in years:
    hy = get(f"{BASE}/?c=past-exhibitions&l=en&s.date={y}", f"tk_past_{y}")
    ids |= set(re.findall(r'c=exhibition&(?:amp;)?l=en[^"]*id=(\d+)', hy))
# art fairs are listed apart, and the shows the gallery's artists had elsewhere --
# Tartu Art House, Berlin, Recklinghausen -- are no longer linked from any list at
# all, though their pages stand. Every exhibition the ledger has seen is read again.
hf = get(f"{BASE}/?c=art-fairs&l=en", "tk_c_art_fairs")
ids |= set(re.findall(r'c=exhibition&(?:amp;)?l=en[^"]*id=(\d+)', hf))
if os.path.exists("gallery_seen.json"):
    for e in json.load(open("gallery_seen.json", encoding="utf-8")).values():
        r = e.get("rec", {})
        if r.get("gallery") == "Temnikova & Kasela":
            m = re.search(r"id=(\d+)", r.get("url", ""))
            if m: ids.add(m.group(1))
print("archive years:", years[0] if years else "-", "to", years[-1] if years else "-", flush=True)
print("published exhibitions:", len(ids), flush=True)

ART = re.compile(r'<article id="id(\d+)".*?</article>', re.S)
recs = []
for eid in sorted(ids, key=int):
    h = get(f"{BASE}/?c=exhibition&l=en&id={eid}", f"tk_ex{eid}")
    ex = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    for m in ART.finditer(h):
        b = m.group(0)
        a = re.search(r'<strong class="aut">(.*?)</strong>', b, re.S)
        t = re.search(r'<h3>(.*?)</h3>', b, re.S)
        tech = re.search(r'<span class="tech">(.*?)</span>', b, re.S)
        yr = re.search(r'<span class="year">(\d{4})</span>', b)
        img = re.search(r'<img class="img t1" src="([^"?]+)', b)
        if not (a and t): continue
        tc = txt(tech.group(1)) if tech else ""
        dm = re.search(r'([\d.,]+\s*[×x]\s*[\d.,]+(?:\s*[×x]\s*[\d.,]+)?\s*(?:cm|mm))', tc, re.I)
        dims = dm.group(1).strip() if dm else ""
        if dims: tc = tc.replace(dm.group(1),"").strip(" .,")
        recs.append({"gid":"tk-"+m.group(1), "artist":txt(a.group(1)),
                     "title":txt(t.group(1)).strip("'’"), "year":yr.group(1) if yr else None,
                     "tech":tc, "dims":dims, "gallery":"Temnikova & Kasela", "city":"Tallinn",
                     "url":f"{BASE}/?c=exhibition&l=en&id={eid}", **({"img": BASE + img.group(1)} if img else {})})

seen,out=set(),[]
for r in recs:
    if r["gid"] in seen: continue
    seen.add(r["gid"]); out.append(r)
prev = json.load(open("gallery_records.json",encoding="utf-8")) if os.path.exists("gallery_records.json") else []
prev = [r for r in prev if not r["gid"].startswith("tk-")]
json.dump(prev+out, open("gallery_records.json","w",encoding="utf-8"), ensure_ascii=False)
print(f"TEMNIKOVA WORKS: {len(out)}   artists: {len({r['artist'] for r in out})}")
for r in out[:4]: print(f"   {r['artist'][:22]:22} {r['title'][:28]:28} {r['year'] or '—':6} {r['dims']}")
