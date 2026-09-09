import json,re,subprocess
from concurrent.futures import ThreadPoolExecutor
UA="EstonianArtCatalogue/1.0 (one-off research compile; contact via claude.ai)"
def curl(u):
    try: return subprocess.run(["curl","-sL","-m","90","--compressed","-A",UA,u],
                               capture_output=True,timeout=120).stdout.decode("utf-8","replace")
    except Exception: return ""
TARGETS=[("685","Virumaa Muuseumid | Kunstikogu"),
         ("666","Viljandi Muuseum | Kunstikogu"),
         ("305","Pärnu Muuseum | Kunstikogu"),
         ("737","Haapsalu ja Läänemaa | Kunstikogu"),
         ("508","Narva Muuseum | Kunstikogu"),
         ("335","Hiiumaa Muuseumid | Kunstikogu"),
         ("552","Eesti Ajaloomuuseum | Kujutav kunst"),
         ("402","EKM | Adamson-Ericu kogu")]
R=json.load(open('records.json',encoding='utf-8'))
have={r['id'] for r in R}
def fetch(t):
    cid,label=t
    ids=sorted(set(re.findall(r'opendata\.muis\.ee/object/(\d+)', curl(f"http://www.muis.ee/rdf/collection/{cid}"))))
    return cid,label,ids
rows=[];allnew=[]
with ThreadPoolExecutor(max_workers=4) as ex:
    for cid,label,ids in ex.map(fetch,TARGETS):
        new=[i for i in ids if i not in have]
        rows.append((label,len(ids),len(new)))
        allnew += [(i,label) for i in new]
print(f"{'total':>7} {'new':>7}  collection")
for label,tot,new in rows: print(f"{tot:7,d} {new:7,d}  {label}")
print(f"{sum(r[1] for r in rows):7,d} {sum(r[2] for r in rows):7,d}  TOTAL")
json.dump(allnew,open('scope_todo.json','w',encoding='utf-8'))
