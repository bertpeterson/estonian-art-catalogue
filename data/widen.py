import re,json,os,gzip,collections
from concurrent.futures import ThreadPoolExecutor
exec(open('harvest.py').read().split('names = [')[0])
exec(open('enrich.py').read().split('R = json.load')[0])   # STOP, flat, field, page, parse, DESC_KEYS

# artworks the first whitelist threw away; documentation and ephemera stay out
ART2 = {"maal","graafika","joonistus","skulptuur","akvarell","installatsioon","kollaaž",
 "segatehnika","videosalvestis","plastika","pastell","monotüüpia","digitaalne kujutis",
 "illustratsioon","gvašš","guašš","reljeef","vaip","keraamika","emailmaal","mosaiik",
 "vitraaž","assamblaaž","performance","objekt","fotoinstallatsioon","tempera",
 "foto","kavand/joonis/eskiis","plakat","visand/skits/etüüd","videoinstallatsioon",
 "eksliibris","karikatuur","medal","dekoratiivne vorm","vaas","figuur","surimask",
 "graafikaplaat","gobelään","tekstiil","klaas","ehe","nukk","maquette"}
def is_art2(e):
    v = (e or "").strip().lower()
    # some essence values contain slashes as part of the term ("kavand/joonis/eskiis"),
    # so test the whole string before splitting it
    if v in ART2: return True
    return any(p.strip().lower() in ART2 for p in re.split(r'[;/]', v))
OLD = {"maal","graafika","joonistus","skulptuur","akvarell","installatsioon","kollaaž",
 "segatehnika","videosalvestis","plastika","pastell","monotüüpia","digitaalne kujutis",
 "illustratsioon","gvašš","guašš","reljeef","vaip","keraamika","emailmaal","mosaiik",
 "vitraaž","assamblaaž","performance","objekt","fotoinstallatsioon","tempera"}
def is_art_old(e):
    return any(p.strip().lower() in OLD for p in re.split(r'[;/]', e or ""))
BAD = re.compile(r'^(postkaart|raamat|kott|ümbrik|väiketrükis|kalender|dokument|järjehoidja|foto; fotonegatiiv)\b', re.I)

H=json.load(open('harvest2.json',encoding='utf-8'))
R=json.load(open('records.json',encoding='utf-8'))
have={r['id'] for r in R}
jobs=[]
for key,v in H.items():
    for r in v['rows']:
        if r['id'] in have: continue
        e=r['essence']
        if is_art_old(e) or not is_art2(e): continue
        t=r['title'].strip()
        if not t or len(t)<2 or BAD.match(t) or BAD.match(e or ""): continue
        coll,_,mus=r['coll'].rpartition(",")
        jobs.append({"id":r['id'],"artist_key":key,"artist":v['display'],"num":r['num'],
                     "author":r['author'],"title":t,"essence":e,
                     "collection":coll.strip(),"museum":mus.strip()})
print("newly eligible objects:",len(jobs))
print("by essence:",collections.Counter(j['essence'] for j in jobs).most_common(10))
AUT=re.compile(r'autor:\s*([^(\n]{2,70}?)\s*\((\d{3,4})\s*[-–]\s*(\d{3,4})?\)')
import unicodedata
def norm(s):
    s=unicodedata.normalize('NFKD',s.lower()); s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]','',s)
def work(j):
    try:
        rec=parse(dict(j)); h=page(j["id"]); txt=re.sub(r'<[^>]+>','\n',h or "")
        rec.pop("life",None)
        for m in AUT.finditer(txt):
            if norm(m.group(1))==norm(j["artist_key"]): rec["life"]=[m.group(2),m.group(3) or ""]; break
        return rec
    except Exception: return None
out=[];done=0
with ThreadPoolExecutor(max_workers=4) as ex:
    for rec in ex.map(work,jobs):
        done+=1
        if rec: out.append(rec)
        if done%200==0: print(" ",done,"/",len(jobs),flush=True)
R.extend(out)
json.dump(R,open('records.json','w',encoding='utf-8'),ensure_ascii=False)
print("added:",len(out)," MuIS records now:",len(R))
