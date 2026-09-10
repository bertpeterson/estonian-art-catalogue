# -*- coding: utf-8 -*-
"""Tütar galerii (Tallinn) -> appends to gallery_records.json.

robots.txt is "Allow: /". The site is Next.js and ships its data as JSON in the page,
so this reads the payload rather than guessing at markup. Metadata only: the details
field carries technique, dimensions and a price line, and the price line is discarded.
"""
import re, json, os, gzip, time, urllib.request, ssl

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
BASE = "https://www.tutar.ee"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
os.makedirs("gcache", exist_ok=True)

def get(url, key):
    p = f"gcache/{key}.html.gz"
    if os.path.exists(p):
        with gzip.open(p,"rt",encoding="utf-8") as f: return f.read()
    try:
        r = urllib.request.Request(url, headers={"User-Agent":UA,"Accept-Language":"et,en"})
        with urllib.request.urlopen(r, timeout=40, context=ctx) as f:
            h = f.read().decode("utf-8","replace")
    except Exception as e:
        print("ERR", url, repr(e)[:60], flush=True); h = ""
    with gzip.open(p,"wt",encoding="utf-8") as f: f.write(h)
    time.sleep(1.2)
    return h

def payload(h):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', h, re.S)
    return json.loads(m.group(1)) if m else None

listing = get(f"{BASE}/kunstnikud", "tutar_list")
slugs = sorted(set(re.findall(r'/kunstnikud/([a-z0-9-]+)', listing)))
print("artists:", len(slugs), flush=True)

DIM = re.compile(r'([\d.,]+\s*[x×]\s*[\d.,]+(?:\s*[x×]\s*[\d.,]+)?)\s*\(?\s*(cm|mm)\s*\)?', re.I)
recs = []
for sl in slugs:
    d = payload(get(f"{BASE}/kunstnikud/{sl}", f"tutar_{sl}"))
    if not d: continue
    a = (d.get("props",{}).get("pageProps",{}) or {}).get("artist") or {}
    name = (a.get("title") or "").strip()
    works = ((a.get("artistFields") or {}).get("artworks")) or []
    if not name: continue
    for w in works:
        af = w.get("artworkFields") or {}
        title = (w.get("title") or "").strip()
        ym = re.search(r'\((\d{4})\)\s*$', title)
        year = ym.group(1) if ym else None
        if ym: title = title[:ym.start()].strip()
        lines = [x.strip() for x in re.split(r'<br\s*/?>|\n', af.get("details") or "") if x.strip()]
        tech, dims = "", ""
        for ln in lines:
            m = DIM.search(ln)
            if m and not dims: dims = f"{m.group(1).strip()} {m.group(2).lower()}"
            # the price line is not collected
            elif not tech and not re.search(r'hind|price|päringu|request|€|eur\b', ln, re.I):
                tech = ln
        if not title: continue
        recs.append({"gid": "tutar-"+str(w.get("id") or w.get("slug")), "artist": name,
                     "title": title, "year": year, "tech": tech, "dims": dims,
                     "gallery": "Tütar galerii", "city": "Tallinn",
                     "url": BASE + (w.get("uri") or f"/kunstnikud/{sl}")})

seen, out = set(), []
for r in recs:
    if r["gid"] in seen: continue
    seen.add(r["gid"]); out.append(r)
prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("tutar-")]
json.dump(keep + out, open("gallery_records.json","w",encoding="utf-8"), ensure_ascii=False)
print(f"TÜTAR WORKS: {len(out)}   artists: {len({r['artist'] for r in out})}")
print(f"  with year {sum(1 for r in out if r['year'])}, with dims {sum(1 for r in out if r['dims'])}")
print(f"  gallery_records.json now: {len(keep)+len(out)}")
for r in out[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:30]:30} {r['year'] or '—':6} {r['tech'][:20]:20} {r['dims']}")
