import re,json,time,urllib.parse
exec(open('dk_list.py',encoding='utf-8').read().split('pairs=[]')[0])
d=json.load(open('dk_list.json',encoding='utf-8'))
capped=[(k,v) for k,v in d.items() if len(v['rows'])>=130 and v['total']>len(v['rows'])]
print("deepening",len(capped),"artists")
def run(kv):
    key,v=kv; disp=v['display']; q=urllib.parse.quote(disp)
    seen={r['oid'] for r in v['rows']}; rows=list(v['rows']); nk=toks(key)
    for p in range(9,26):
        h=get(f"{BASE}/ekm/search/?_page={p}&_count_all={v['total']}&searchtype=simple&searchtext={q}")
        rs=parse(h)
        if not rs: break
        new=0
        for r in rs:
            if r['oid'] in seen: continue
            seen.add(r['oid'])
            if toks(r['author'])==nk: rows.append(r); new+=1
        time.sleep(0.15)
    return key,rows
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=5) as ex:
    for key,rows in ex.map(run,capped):
        print("  %-24s %d -> %d"%(d[key]['display'],len(d[key]['rows']),len(rows)),flush=True)
        d[key]['rows']=rows
json.dump(d,open('dk_list.json','w',encoding='utf-8'),ensure_ascii=False)
print("TOTAL ROWS:",sum(len(v['rows']) for v in d.values()))
