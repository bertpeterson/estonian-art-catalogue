# -*- coding: utf-8 -*-
"""Ruki galerii (Tallinn) -> appends to gallery_records.json.

robots.txt allows all but /files/ and /admin/ (it blocks adsbot and Barkrowler by name,
not us). Works are listed per category as four lines: title with year, artist with
birth year, technique with dimensions, price. The price line is discarded.
The artist line is the anchor, so a work with no named artist is skipped rather than
guessed at — the catalogue takes attributed work only.
"""
import re, json, os, gzip, time, urllib.request, ssl
UA="EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
BASE="https://rukigalerii.ee"
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
os.makedirs("gcache",exist_ok=True)
CATS=["maal","graafika","foto","joonistus","segatehnika","noored-kunstnikud"]

def get(u,key):
    p=f"gcache/{key}.html.gz"
    if os.path.exists(p):
        with gzip.open(p,"rt",encoding="utf-8") as f: return f.read()
    try:
        r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"et"})
        with urllib.request.urlopen(r,timeout=35,context=ctx) as f: h=f.read().decode("utf-8","replace")
    except Exception as e:
        print("ERR",u,repr(e)[:50]); h=""
    with gzip.open(p,"wt",encoding="utf-8") as f: f.write(h)
    time.sleep(1.2); return h

def lines(h):
    t=re.sub(r'(?s)<(script|style).*?</\1>','',h)
    t=t.replace("&nbsp;"," ").replace("&amp;","&").replace("&quot;",'"')
    t=re.sub(r'<[^>]+>','\n',t)
    return [re.sub(r'\s+',' ',x).strip() for x in t.split('\n') if x.strip()]

ARTIST=re.compile(r'^(.{3,45}?)\s*\(\s*s\.\s*(\d{4})\s*\)\s*$')
DIM=re.compile(r'([\d.,]+\s*[x×]\s*[\d.,]+(?:\s*[x×]\s*[\d.,]+)?)\s*(cm|mm)', re.I)
PRICE=re.compile(r'^\s*[\d\s]+\s*€|kokkuleppel|müüdud', re.I)
def clean_tech(t):
    # a measurement wrapped onto the next line leaves "..., mõõt 115 x" behind
    t = re.sub(r'[,;]?\s*(?:mõõt|suurus)?\s*[\d.,]+\s*[x×]\s*[\d.,]*\s*$', '', t, flags=re.I)
    return re.sub(r'\s{2,}', ' ', t).strip(" ,.")

recs=[]
for cat in CATS:
    L=lines(get(f"{BASE}/teosed/{cat}", f"ruki_{cat}"))
    for i,ln in enumerate(L):
        m=ARTIST.match(ln)
        if not m: continue
        artist=m.group(1).strip(" ,")
        prev=L[i-1] if i else ""
        tm=re.match(r'^(.*?),\s*(\d{4})\s*$', prev)
        title, year = (tm.group(1).strip(), tm.group(2)) if tm else (prev.strip(), None)
        if not title or ARTIST.match(prev) or PRICE.match(prev): continue
        tech=dims=""
        for nx in L[i+1:i+4]:
            if PRICE.match(nx): break
            d=DIM.search(nx)
            if d and not dims:
                dims=f"{d.group(1).strip()} {d.group(2).lower()}"
                nx=nx.replace(d.group(0),"")
            if not tech and nx.strip(" ,."): tech=nx.strip(" ,.")
        recs.append({"gid":"ruki-"+re.sub(r'[^a-z0-9]','',(artist+title).lower())[:40],
                     "artist":artist,"title":title,"year":year,
                     "tech":clean_tech(tech),"dims":dims,
                     "gallery":"Ruki galerii","city":"Tallinn","url":f"{BASE}/teosed/{cat}"})

seen,out=set(),[]
for r in recs:
    if r["gid"] in seen or not r["title"]: continue
    seen.add(r["gid"]); out.append(r)
prev=json.load(open("gallery_records.json",encoding="utf-8"))
keep=[r for r in prev if not r["gid"].startswith("ruki-")]
json.dump(keep+out,open("gallery_records.json","w",encoding="utf-8"),ensure_ascii=False)
print(f"RUKI WORKS: {len(out)}   artists: {len({r['artist'] for r in out})}")
print(f"  with year {sum(1 for r in out if r['year'])}, with dims {sum(1 for r in out if r['dims'])}")
for r in out[:5]: print(f"   {r['artist'][:22]:22} {r['title'][:28]:28} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:24]}")
