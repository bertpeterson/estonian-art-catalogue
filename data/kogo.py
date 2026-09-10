# -*- coding: utf-8 -*-
"""Kogo Galerii (Tartu) -> appends to gallery_records.json. Metadata only, no prices."""
import re, json, os, gzip, urllib.request, ssl
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
os.makedirs("gcache", exist_ok=True)

def get(url, key):
    p = f"gcache/{key}.html.gz"
    if os.path.exists(p):
        with gzip.open(p,"rt",encoding="utf-8") as f: return f.read()
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language":"en"})
    with urllib.request.urlopen(r, timeout=60, context=ctx) as f:
        h = f.read().decode("utf-8","replace")
    with gzip.open(p,"wt",encoding="utf-8") as f: f.write(h)
    return h

def txt(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    for a,b in (("&amp;","&"),("&#8217;","’"),("&#8211;","–"),("&nbsp;"," "),("&quot;",'"')):
        s = s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

BLOCK = re.compile(r'<div class="artwork-details">(.*?)</div><!-- details -->', re.S)
out = []
for page in ("art-store", "works"):
    try: h = get(f"https://www.kogogallery.ee/en/{page}/", f"kogo_{page}")
    except Exception as e: print("skip", page, repr(e)[:60]); continue
    for m in BLOCK.finditer(h):
        b = m.group(1)
        t = re.search(r'class="artwork-navigate" href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
        a = re.search(r'artwork-artist">\s*<a[^>]*>(.*?)</a>', b, re.S)
        info = re.search(r'artwork-info">(.*?)$', b, re.S)
        if not (t and a): continue
        raw = txt(info.group(1)) if info else ""
        dm = re.search(r'<span class="dimensions">(.*?)</span>', b, re.S)
        dims = re.sub(r'\s*cm\s*cm', ' cm', txt(dm.group(1))).strip(" ,") if dm else ""
        yr = re.search(r'(\b(?:19|20)\d{2}\b)\s*$', raw)
        tech = raw
        if dims: tech = tech.replace(dims.replace(" cm"," cm cm"), "").replace(dims, "")
        if yr: tech = tech[:yr.start()] if yr.start() < len(tech) else tech
        tech = re.sub(r'\s+',' ', re.sub(r'[,\s]+$','',tech)).strip(" ,")
        out.append({"gid": "kogo-"+t.group(1).rstrip("/").rsplit("/",1)[-1],
                    "artist": txt(a.group(1)), "title": txt(t.group(2)),
                    "year": yr.group(1) if yr else None, "tech": tech, "dims": dims,
                    "gallery": "Kogo galerii", "city": "Tartu", "url": t.group(1)})

seen, recs = set(), []
for r in out:
    if r["gid"] in seen: continue
    seen.add(r["gid"]); recs.append(r)
prev = json.load(open("gallery_records.json", encoding="utf-8")) if os.path.exists("gallery_records.json") else []
prev = [r for r in prev if not r["gid"].startswith("kogo-")]
json.dump(prev + recs, open("gallery_records.json","w",encoding="utf-8"), ensure_ascii=False)
print(f"KOGO WORKS: {len(recs)}   artists: {len({r['artist'] for r in recs})}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:4]: print(f"   {r['artist'][:24]:24} {r['title'][:30]:30} {r['year'] or '—':6} {r['dims']}")
