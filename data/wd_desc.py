# -*- coding: utf-8 -*-
import json, re, time, urllib.parse, urllib.request, collections
UA="EstonianArtCatalogue/1.0 (one-off research compile; contact via claude.ai)"
EP="https://query.wikidata.org/sparql"
d=json.load(open('data.json',encoding='utf-8'))
A=[a for a in d['artists'] if a.get('c',0)>0]
SKIP=re.compile(r'^(tundmat|teadmata|anon|rühmitus)',re.I)
todo=[a for a in A if not SKIP.match(a['n']) and len(a['n'])>3]
print(f"artists: {len(todo):,}",flush=True)
def q(batch):
    vals=" ".join('"%s"@en'%a['n'].replace('\\','').replace('"','') for a in batch)
    query="""SELECT ?name ?p ?desc ?birth WHERE {
  VALUES ?name { %s }
  ?p rdfs:label ?name . ?p wdt:P31 wd:Q5 .
  ?p schema:description ?desc . FILTER(lang(?desc)="en")
  OPTIONAL { ?p wdt:P569 ?birth }
}"""%vals
    for k in range(3):
        try:
            req=urllib.request.Request(EP,urllib.parse.urlencode({"query":query}).encode(),
                {"User-Agent":UA,"Accept":"application/sparql-results+json"})
            with urllib.request.urlopen(req,timeout=180) as r:
                return json.loads(r.read().decode())["results"]["bindings"]
        except Exception:
            if k==2: return []
            time.sleep(4*(k+1))
    return []
out={};B=60
for i in range(0,len(todo),B):
    batch=todo[i:i+B]
    want={a['n']:(a.get('l') or ["",""])[0] for a in batch}
    for b in q(batch):
        n=b['name']['value']; desc=b['desc']['value']
        raw=b.get('birth',{}).get('value','')
        by=raw[:4] if re.match(r'^\d{4}', raw) else ""      # Wikidata may return a URI for unknown dates
        # guard against name collisions (two Oskar Hoffmanns) using the birth year we hold
        mine=want.get(n,"") or ""
        if not re.match(r'^\d{4}$', str(mine)): mine=""
        if mine and by and abs(int(by)-int(mine))>3: continue
        if n not in out: out[n]={"desc":desc,"qid":b['p']['value'].rsplit('/',1)[-1],"byear":by}
    if (i//B)%5==0: print(f"  {min(i+B,len(todo))}/{len(todo)} matched {len(out):,}",flush=True)
    time.sleep(0.7)
json.dump(out,open('wd_desc.json','w',encoding='utf-8'),ensure_ascii=False)
print(f"\nMATCHED {len(out):,} of {len(todo):,} ({len(out)/len(todo)*100:.0f}%)",flush=True)
def affil(t):
    t=t.lower()
    for pat,lab in [(r'baltic[- ]german','Baltic German'),(r'estonian[- ]swedish','Estonian-Swedish'),
                    (r'estonian','Estonian'),(r'\bswedish','Swedish'),(r'\brussian','Russian'),
                    (r'\bgerman','German'),(r'\bswiss','Swiss'),(r'\bfinnish','Finnish'),
                    (r'\bpolish','Polish'),(r'\blatvian','Latvian'),(r'\bdutch','Dutch'),
                    (r'\bfrench','French'),(r'\bitalian','Italian'),(r'\bamerican','American'),
                    (r'\bbritish|\benglish','British'),(r'\bsoviet','Soviet')]:
        if re.search(pat,t): return lab
    return None
c=collections.Counter(affil(v['desc']) for v in out.values())
print("affiliations parsed:",c.most_common(16))
