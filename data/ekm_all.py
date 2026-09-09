import re,json,os,time
from concurrent.futures import ThreadPoolExecutor
exec(open('dk_list.py',encoding='utf-8').read().split('pairs=[]')[0])
BASE="https://digikogu.ekm.ee"
h=get(f"{BASE}/search?searchtype=simple&searchtext=")
total=int(re.search(r'_count_all=(\d+)',h).group(1))
pages=(total+17)//18
print(f"collection total {total:,} -> {pages:,} listing pages",flush=True)
def one(p):
    u=(f"{BASE}/search?searchtype=simple&searchtext=" if p==1 else
       f"{BASE}/ekm/search/?_page={p}&_count_all={total}&searchtype=simple&searchtext=")
    return parse(get(u))
rows={};done=0
with ThreadPoolExecutor(max_workers=4) as ex:
    for rs in ex.map(one,range(1,pages+1)):
        done+=1
        for r in rs: rows[r["oid"]]=r
        if done%200==0: print(f"  page {done}/{pages}  unique {len(rows):,}",flush=True)
json.dump(list(rows.values()),open('ekm_all_list.json','w',encoding='utf-8'),ensure_ascii=False)
held={f[:-8] for f in os.listdir('dkcache') if f.endswith('.html.gz')}
new=[o for o in rows if o not in held]
print(f"LISTED {len(rows):,}   already fetched {len(rows)-len(new):,}   new {len(new):,}",flush=True)
json.dump(new,open('ekm_all_new.json','w',encoding='utf-8'))
