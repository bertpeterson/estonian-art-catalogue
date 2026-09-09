import json,re,subprocess,collections
from concurrent.futures import ThreadPoolExecutor
UA="EstonianArtCatalogue/1.0 (one-off research compile; contact via claude.ai)"
def curl(u,extra=None):
    cmd=["curl","-sL","-m","90","--compressed","-A",UA]+(extra or [])+[u]
    try: return subprocess.run(cmd,capture_output=True,timeout=120).stdout.decode("utf-8","replace")
    except Exception: return ""
S=json.load(open('coll_samples.json',encoding='utf-8'))
def coll_id(item):
    label,oid=item
    r=curl(f"http://opendata.muis.ee/object/{oid}",["-H","Accept: application/rdf+xml"])
    m=re.search(r'rdf/collection/(\d+)',r)
    return label,(m.group(1) if m else None)
ids={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for label,cid in ex.map(coll_id,S.items()):
        if cid: ids[label]=cid
def size(item):
    label,cid=item
    r=curl(f"http://www.muis.ee/rdf/collection/{cid}")
    return label,cid,len(re.findall(r'opendata\.muis\.ee/object/\d+',r))
rows=[]
with ThreadPoolExecutor(max_workers=4) as ex:
    for label,cid,n in ex.map(size,ids.items()): rows.append((n,cid,label))
rows.sort(reverse=True)
json.dump([{"n":n,"cid":c,"label":l} for n,c,l in rows],open('collections.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
print(f"{len(rows)} collections resolved; total public objects: {sum(r[0] for r in rows):,}\n")
for n,c,l in rows[:22]: print(f"   {n:7,d}  id={c:<6s} {l}")
