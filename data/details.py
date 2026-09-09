import re, json, os, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
exec(open('harvest.py').read().split('names = [')[0])

ART = {"maal","graafika","joonistus","skulptuur","akvarell","installatsioon","kollaaž",
       "segatehnika","videosalvestis","plastika","pastell","monotüüpia","digitaalne kujutis",
       "illustratsioon","gvašš","guašš","reljeef","vaip","keraamika","emailmaal","mosaiik",
       "vitraaž","assamblaaž","performance","objekt","fotoinstallatsioon","tempera"}
ART_MUSEUMS = ("Eesti Kunstimuuseum","Tartu Kunstimuuseum","Eesti Kunstiakadeemia",
               "Tartu Ülikooli kunstimuuseum","Eesti Tarbekunsti","Adamson-Eric")
BAD_TITLE = re.compile(r'^(foto|postkaart|plakat|raamat|medal|kott|ümbrik|väiketrükis|kalender|dokument)\b', re.I)

def is_art(e):
    parts = [p.strip().lower() for p in re.split(r'[;/]', e)]
    return any(p in ART for p in parts)

def keyt(t):
    t = unicodedata.normalize('NFKD', t.lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', t)

def select(rows, cap=20):
    def score(r):
        s = 0
        if any(m in r["coll"] for m in ART_MUSEUMS): s -= 10
        if r["essence"].strip().lower() in ("maal","skulptuur"): s -= 3
        return s
    keep, seen = [], set()
    for r in sorted([r for r in rows if is_art(r["essence"])], key=score):
        t = r["title"].strip()
        if not t or len(t) < 2 or BAD_TITLE.match(t): continue
        k = keyt(t)
        if not k or k in seen: continue
        seen.add(k); keep.append(r)
        if len(keep) >= cap: break
    return keep

def flat(h):
    t = re.sub(r'<script.*?</script>', '', h, flags=re.S)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
    t = re.sub(r'<br\s*/?>', '\n', t)
    t = re.sub(r'</(div|p|h\d|li|td|tr|span|dt|dd)>', '\n', t)
    t = re.sub(r'<[^>]+>', '\n', t)
    t = t.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
    return [x.strip() for x in t.split('\n') if x.strip()]

STOP = {"Number","Autor","Nimetus","Olemus","Dateering","Originaal","Seisund","Tehnika",
        "Materjal","Värvus","Mõõdud","Vähem «","Rohkem »","Muuseumikogu",
        "Hinnang museaali kultuuriväärtuse kohta","Kirjeldus","Kommentaar"}

def field(L, key, multi=False):
    try: i = L.index(key)
    except ValueError: return None
    if not multi:
        v = L[i+1] if i+1 < len(L) else None
        return None if v in STOP else v
    out = []
    for x in L[i+1:]:
        if x in STOP: break
        out.append(x)
    return out or None

def detail(item):
    mid = item["id"]
    h = get(None_opener, BASE + "/museaalview/" + mid) if False else None
    return None

_op = None
def op():
    global _op
    if _op is None: _op = opener()
    return _op

def fetch(item):
    h = get(op(), BASE + "/museaalview/" + item["id"])
    if not h: return None
    L = flat(h)
    rec = {"id": item["id"]}
    try: mi = L.index("Muuseumikogu"); rec["museum"] = L[mi-1]; rec["collection"] = L[mi+1]
    except ValueError: rec["museum"] = item["coll"].split(",")[-1].strip(); rec["collection"] = item["coll"].split(",")[0].strip()
    rec["num"]     = field(L, "Number") or item["num"]
    rec["author"]  = field(L, "Autor") or item["author"]
    rec["title"]   = field(L, "Nimetus") or item["title"]
    rec["essence"] = field(L, "Olemus") or item["essence"]
    rec["date"]    = field(L, "Dateering")
    rec["tech"]    = field(L, "Tehnika")
    rec["mat"]     = field(L, "Materjal")
    dims = field(L, "Mõõdud", multi=True)
    rec["dims"] = "; ".join(dims[:4]) if dims else None
    try:
        i = L.index("füüsiline kirjeldus")
        rec["desc"] = L[i+1][:600]
    except ValueError: rec["desc"] = None
    m = re.search(r'autor:\s*[^(\n]{2,60}\((\d{3,4})\s*[-–]\s*(\d{3,4})?\)', "\n".join(L))
    if m: rec["life"] = (m.group(1), m.group(2) or "")
    # museum's own artist biography = longest paragraph after the life-dates line
    bio = max((x for x in L if len(x) > 220 and 'sündis' in x.lower()), key=len, default=None)
    if bio: rec["bio"] = bio[:1400]
    return rec

H = json.load(open("harvest2.json", encoding="utf-8"))
CAP = int(os.environ.get("CAP", "20"))
jobs = []
for key, v in H.items():
    for r in select(v["rows"], CAP):
        jobs.append((key, v["display"], r))
print("detail fetches:", len(jobs), flush=True)

out = []
def work(j):
    key, disp, r = j
    try:
        rec = fetch(r)
    except Exception:
        rec = None
    if rec: rec["artist_key"] = key; rec["artist"] = disp
    return rec

done = 0
with ThreadPoolExecutor(max_workers=6) as ex:
    for rec in ex.map(work, jobs):
        done += 1
        if rec: out.append(rec)
        if done % 200 == 0: print("  %d/%d" % (done, len(jobs)), flush=True)
json.dump(out, open("records.json", "w", encoding="utf-8"), ensure_ascii=False)
print("RECORDS:", len(out))
print("with date:", sum(1 for r in out if r.get("date")))
