import re,json,os,gzip,time
from concurrent.futures import ThreadPoolExecutor
exec(open('dk_list.py',encoding='utf-8').read().split('pairs=[]')[0])

def page(oid):
    p="dkcache/%s.html.gz"%oid
    if os.path.exists(p):
        with gzip.open(p,'rt',encoding='utf-8') as f: return f.read()
    h=get(f"{BASE}/ekm/search/oid-{oid}/")
    if h:
        with gzip.open(p,'wt',encoding='utf-8') as f: f.write(h)
    return h

ROW=re.compile(r'<td class="title">(.*?)</td>\s*<td class="description[^"]*">(.*?)</td>',re.S)
def txt(s):
    s=re.sub(r'<br\s*/?>','\n',s)
    s=re.sub(r'<[^>]+>','',s)
    return s.replace('&nbsp;',' ').replace('&amp;','&').replace('&quot;','"').strip()

def parse_item(oid):
    h=page(oid)
    if not h: return None
    rec={"oid":oid}
    m=re.search(r'/authors/author_id-(\d+)',h)
    if m: rec["aid"]=m.group(1)
    for lm,vm in ROW.findall(h):
        labs=[x.strip().rstrip(':').strip() for x in txt(lm).split('\n') if x.strip()]
        vals=[x.strip() for x in txt(vm).split('\n')]
        if len(labs)==1:
            rec[labs[0]]=" ".join(v for v in vals if v).strip()
        else:
            for i,lab in enumerate(labs):
                rec[lab]=vals[i].strip() if i<len(vals) else ""
    return rec

D=json.load(open('dk_list.json',encoding='utf-8'))
jobs=[]
for key,v in D.items():
    for r in v['rows']: jobs.append((key,v['display'],r['oid']))
print("item fetches:",len(jobs),flush=True)
out=[];done=0
def work(j):
    key,disp,oid=j
    try: rec=parse_item(oid)
    except Exception: rec=None
    if rec: rec["artist_key"]=key; rec["artist"]=disp
    return rec
with ThreadPoolExecutor(max_workers=5) as ex:
    for rec in ex.map(work,jobs):
        done+=1
        if rec: out.append(rec)
        if done%750==0: print("  %d/%d"%(done,len(jobs)),flush=True)
json.dump(out,open('dk_records.json','w',encoding='utf-8'),ensure_ascii=False)
import collections
print("RECORDS:",len(out))
print("with Dateering:",sum(1 for r in out if r.get("Dateering")))
print("with Tulmenumber:",sum(1 for r in out if r.get("Tulmenumber")))
print("fields:",collections.Counter(k for r in out for k in r).most_common(16))
