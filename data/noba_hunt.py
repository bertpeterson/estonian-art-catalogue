# -*- coding: utf-8 -*-
"""Work through the NOBA gallery names: derive likely domains, probe each for a
work-level catalogue (artist + title + dimensions), and rank what is worth harvesting.
NOBA lists venues, not websites, so the domains are inferred and most will miss."""
import re, json, ssl, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA="EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
DIM=re.compile(r'\d+([.,]\d+)?\s*[x×]\s*\d+([.,]\d+)?\s*(cm|mm)',re.I)
WANT=re.compile(r'(kunstnik|artist|teos|work|shop|pood|galerii|gallery|artwork|müük|store|kunst)',re.I)

def get(u, t=18):
    try:
        r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"et,en"})
        with urllib.request.urlopen(r,timeout=t,context=ctx) as f:
            return f.geturl(), f.read().decode("utf-8","replace")
    except Exception: return None, ""

KNOWN={"a-galerii","haus-galerii","kogo-galerii","tutar-galerii","vaal-galerii","draakoni-galerii",
       "hobusepea-galerii","okapi-galerii","kai-kunstikeskus","temnikova-kasela-galerii",
       "kumu-kunstimuuseum","niguliste-muuseum","mikkeli-muuseum","kadrioru-kunstimuuseum",
       "adamson-ericu-muuseum","eesti-kaasaegse-kunsti-muuseum"}
SKIP=re.compile(r'muuseum|kultuurikeskus|keskuse|raamatukogu|kirik|loss|kool|teater|kino|selts', re.I)

names=json.load(open('noba_galleries.json',encoding='utf-8'))
cands=[n for n in names if re.search(r'galerii|gallery|kunstisalong|naitusesaal', n, re.I)
       and n not in KNOWN and not SKIP.search(n)]
print(f"gallery-like names to try: {len(cands)}", flush=True)

def domains(slug):
    t=[x for x in slug.split("-") if x not in ("galerii","gallery","en")]
    core="".join(t)
    out=[f"{core}.ee", f"{core}galerii.ee", f"galerii{core}.ee"]
    if len(t)>1: out.append(f"{t[0]}.ee")
    return list(dict.fromkeys(out))[:4]

def probe(slug):
    for d in domains(slug):
        url,h = get("https://"+d)
        if not h or len(h)<2000: continue
        best=len(DIM.findall(h)); page=url
        links={m if m.startswith("http") else url.rstrip("/")+"/"+m.lstrip("/")
               for m in re.findall(r'href="([^"#?]{2,70})"', h) if WANT.search(m)
               and not re.search(r'\.(css|js|png|jpe?g|svg|ico|webp|pdf)$', m, re.I)}
        for l in sorted(links)[:4]:
            _,p=get(l)
            n=len(DIM.findall(p))
            if n>best: best, page = n, l
        return {"slug":slug,"domain":d,"url":url,"dims":best,"page":page}
    return {"slug":slug,"domain":None,"dims":0,"page":None}

with ThreadPoolExecutor(max_workers=6) as ex: res=list(ex.map(probe,cands))
res.sort(key=lambda r:-r["dims"])
json.dump(res,open('noba_hunt.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
hits=[r for r in res if r["dims"]>=5]
print(f"\nreachable: {sum(1 for r in res if r['domain'])}/{len(res)}   with work-level data: {len(hits)}\n")
print(f"{'gallery':30} {'domain':26} {'dims':>5}  best page")
for r in res[:22]:
    if not r["domain"]: continue
    print(f"{r['slug'][:30]:30} {r['domain'][:26]:26} {r['dims']:5}  {(r['page'] or '')[:52]}")
