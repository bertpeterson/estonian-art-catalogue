import json,gzip,re,os,collections,unicodedata
R=json.load(open('records.json',encoding='utf-8'))
ROLE=re.compile(r'^(kujutatu|kujutatud|annetaja|omanik|valmistaja|autor|seosisik|seosorganisatsioon|jäädvustaja|koguja|eelmine omanik)\s*:',re.I)
END={'seosobjekt','Püsiviide:','Museaali andmed RDF/XML kujul','Tagasiside'}
def norm(s):
    s=unicodedata.normalize('NFKD',s.lower()); s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]','',s)
def lines(mid):
    p="cache/%s.html.gz"%mid
    if not os.path.exists(p): return None
    h=gzip.open(p,'rt',encoding='utf-8').read()
    h=re.sub(r'<script.*?</script>','',h,flags=re.S); h=re.sub(r'<style.*?</style>','',h,flags=re.S)
    return [x.strip() for x in re.sub(r'<[^>]+>','\n',h).split('\n') if x.strip()]
def bio_from(mid, key):
    L=lines(mid)
    if not L: return None
    nk=norm(key)
    start=None
    for n,x in enumerate(L):
        m=re.match(r'^autor:\s*([^(]{2,70}?)\s*\(',x)
        if m and norm(m.group(1))==nk: start=n; break
    if start is None: return None
    end=len(L)
    for n in range(start+1,len(L)):
        if L[n] in END or ROLE.match(L[n]): end=n; break
    win=L[start+1:end]
    marks=[i for i,x in enumerate(win) if 'luloolised andmed' in x.lower() or x=='töö ja tegevus']
    for i in marks:
        for x in win[i+1:]:
            if len(x)>150 and not x.startswith('('): return x[:1600]
    cand=[x for x in win if len(x)>200 and not x.startswith('(')]
    return max(cand,key=len)[:1600] if cand else None

fixed=dropped=0
for r in R:
    old=r.get('bio'); new=bio_from(r['id'], r['artist_key'])
    if new:
        if new!=old: fixed+=1
        r['bio']=new
    elif old:
        r.pop('bio'); dropped+=1
json.dump(R,open('records.json','w',encoding='utf-8'),ensure_ascii=False)
per=collections.defaultdict(list)
for r in R:
    if r.get('bio'): per[r['artist']].append(r['bio'])
print(f"rewritten {fixed}  removed {dropped}   artists with MuIS bio: {len(per)}")
for n in ["Ülo Sooster","Eduard Wiiralt","Konrad Mägi","August Weizenberg","Kristjan Raud","Anu Põder"]:
    b=max(per.get(n,[""]),key=len)
    print(f"  {n:18s} {b[:104]!r}")
