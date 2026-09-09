import re,json,os,gzip,subprocess,collections,unicodedata
from concurrent.futures import ThreadPoolExecutor
exec(open('harvest.py').read().split('names = [')[0])
exec(open('enrich.py').read().split('R = json.load')[0])
UA="EstonianArtCatalogue/1.0 (one-off research compile; contact via claude.ai)"
def curl(u):
    try: return subprocess.run(["curl","-sL","-m","90","--compressed","-A",UA,u],
                               capture_output=True,timeout=120).stdout.decode("utf-8","replace")
    except Exception: return ""

# high-value art collections: paintings, sculpture, contemporary, plus Tartu painting.
# (Graafikakogu's 28k prints are deliberately left for a later pass.)
TARGETS=[("289","Eesti Kunstimuuseum SA | Maalikogu"),
         ("403","Eesti Kunstimuuseum SA | Skulptuurikogu"),
         ("400","Eesti Kunstimuuseum SA | Nüüdiskunstikogu"),
         ("442","Tartu Kunstimuuseum SA | Maal"),
         ("418","Tartu Kunstimuuseum SA | Joonistus")]
ids=[]
for cid,label in TARGETS:
    r=curl(f"http://www.muis.ee/rdf/collection/{cid}")
    found=sorted(set(re.findall(r'opendata\.muis\.ee/object/(\d+)',r)))
    ids+= [(i,label) for i in found]
    print(f"{label}: {len(found):,}",flush=True)
R=json.load(open('records.json',encoding='utf-8'))
have={r['id'] for r in R}
todo=[(i,l) for i,l in ids if i not in have]
print(f"total listed {len(ids):,}; already held {len(ids)-len(todo):,}; to fetch {len(todo):,}",flush=True)
json.dump(todo,open('mass_todo.json','w',encoding='utf-8'))
