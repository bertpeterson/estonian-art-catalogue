import re,json,os,gzip,unicodedata,time
from concurrent.futures import ThreadPoolExecutor
exec(open('harvest.py').read().split('names = [')[0])
exec(open('enrich.py').read().split('R = json.load')[0])
todo=json.load(open('mass_todo.json',encoding='utf-8'))
print("to fetch:",len(todo),flush=True)
AUT=re.compile(r'autor:\s*([^(\n]{2,70}?)\s*\((\d{3,4})\s*[-–]\s*(\d{3,4})?\)')
def norm(s):
    s=unicodedata.normalize('NFKD',(s or "").lower()); s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]','',s)
def display(a):
    a=(a or "").strip()
    if "," in a:
        sur,_,first=a.partition(",")
        return f"{first.strip()} {sur.strip()}".strip()
    return a
def work(item):
    oid,label=item
    try:
        rec=parse({"id":oid})
        au=rec.get("author")
        if not au: return None
        rec["artist_key"]=au
        rec["artist"]=display(au)
        h=page(oid); txt=re.sub(r'<[^>]+>','\n',h or "")
        rec.pop("life",None)
        for m in AUT.finditer(txt):
            if norm(m.group(1))==norm(au): rec["life"]=[m.group(2),m.group(3) or ""]; break
        rec["mass"]=True
        return rec
    except Exception:
        return None
out=[];done=0
with ThreadPoolExecutor(max_workers=4) as ex:
    for rec in ex.map(work,todo):
        done+=1
        if rec: out.append(rec)
        if done%1000==0: print(f"  {done}/{len(todo)}  kept {len(out)}",flush=True)
json.dump(out,open('mass_records.json','w',encoding='utf-8'),ensure_ascii=False)
print("FETCHED:",done," WITH AUTHOR:",len(out),flush=True)
