import re, json, time, unicodedata, urllib.request, urllib.parse, http.cookiejar
from concurrent.futures import ThreadPoolExecutor
BASE="https://digikogu.ekm.ee"
UA="EstonianArtRegister/1.0 (one-off research compile; contact via claude.ai)"

def opener():
    cj=http.cookiejar.CookieJar()
    o=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    o.addheaders=[("User-Agent",UA),("Accept-Language","et,en")]
    return o
_t={}
def op():
    import threading
    k=threading.get_ident()
    if k not in _t: _t[k]=opener()
    return _t[k]
def get(url,tries=3):
    for i in range(tries):
        try:
            with op().open(url,timeout=60) as r: return r.read().decode("utf-8","replace")
        except Exception:
            if i==tries-1: return ""
            time.sleep(1.2*(i+1))
    return ""
def norm(s):
    s=unicodedata.normalize('NFKD',s.lower())
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]','',s)

def toks(s):
    s=unicodedata.normalize('NFKD',s.lower())
    s=''.join(c for c in s if not unicodedata.combining(c))
    return tuple(sorted(t for t in re.split(r'[^a-z0-9]+',s) if t))

ITEM=re.compile(r'oid-(\d+)/[^"]*"[\s\S]{0,600}?<div class="description">\s*(.*?)\s*</div>')
def parse(h):
    i=h.find('id="imageList"')
    if i<0: return []
    out=[]
    for m in ITEM.finditer(h[i:]):
        oid,desc=m.group(1),re.sub(r'<[^>]+>','',m.group(2)).replace('&nbsp;',' ').strip()
        if ',' in desc:
            a,t=desc.split(',',1); out.append({"oid":oid,"author":a.strip(),"title":t.strip()})
        else:
            out.append({"oid":oid,"author":"","title":desc})
    return out

pairs=[]
for l in open('artists2.txt',encoding='utf-8'):
    l=l.strip()
    if not l: continue
    k,d=l.split('|'); pairs.append((k,d))
PAGES=8

def run(pair):
    key,disp=pair
    q=urllib.parse.quote(disp)
    h=get(f"{BASE}/search?searchtype=simple&searchtext={q}")
    m=re.search(r'Leitud pilte:\s*(\d+)',h)
    total=int(m.group(1)) if m else 0
    rows=parse(h); seen={r["oid"] for r in rows}
    for p in range(2,PAGES+1):
        if len(rows)>=total: break
        h2=get(f"{BASE}/ekm/search/?_page={p}&_count_all={total}&searchtype=simple&searchtext={q}")
        rs=parse(h2)
        if not rs: break
        for r in rs:
            if r["oid"] not in seen: seen.add(r["oid"]); rows.append(r)
        time.sleep(0.2)
    nk=toks(key)
    mine=[r for r in rows if toks(r["author"])==nk]
    return key,disp,total,mine

res={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for key,disp,total,mine in ex.map(run,pairs):
        res[key]={"display":disp,"total":total,"rows":mine}
        print("%-26s hits=%-6d mine=%d"%(disp,total,len(mine)),flush=True)
json.dump(res,open("dk_list.json","w",encoding="utf-8"),ensure_ascii=False)
print("ARTISTS:",sum(1 for v in res.values() if v["rows"]))
print("ROWS:",sum(len(v["rows"]) for v in res.values()))
