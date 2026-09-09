import re, json, os, gzip, time
from concurrent.futures import ThreadPoolExecutor
exec(open('harvest.py').read().split('names = [')[0])

STOP = {"Number","Autor","Nimetus","Olemus","Dateering","Originaal","Seisund","Tehnika",
        "Materjal","Värvus","Mõõdud","Vähem «","Rohkem »","Muuseumikogu","Kunstiese",
        "Hinnang museaali kultuuriväärtuse kohta","Kirjeldus","Kommentaar","Kogu"}

def flat(h):
    t = re.sub(r'<script.*?</script>', '', h, flags=re.S)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
    t = re.sub(r'<br\s*/?>', '\n', t)
    t = re.sub(r'</(div|p|h\d|li|td|tr|span|dt|dd)>', '\n', t)
    t = re.sub(r'<[^>]+>', '\n', t)
    t = t.replace('&nbsp;',' ').replace('&amp;','&').replace('&quot;','"').replace('&#39;',"'")
    return [x.strip() for x in t.split('\n') if x.strip()]

def field(L, key, multi=False):
    try: i = L.index(key)
    except ValueError: return None
    if not multi:
        v = L[i+1] if i+1 < len(L) else None
        return None if (v is None or v in STOP) else v
    out = []
    for x in L[i+1:]:
        if x in STOP: break
        out.append(x)
    return out or None

_ops = {}
def op():
    import threading
    k = threading.get_ident()
    if k not in _ops: _ops[k] = opener()
    return _ops[k]

def page(mid):
    p = "cache/%s.html.gz" % mid
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    h = get(op(), BASE + "/museaalview/" + mid)
    if h:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    return h

DESC_KEYS = ["füüsiline kirjeldus","sisu kirjeldus","kirjeldus","tekst objektil"]

def parse(rec):
    h = page(rec["id"])
    if not h: return rec
    L = flat(h); blob = "\n".join(L)
    try:
        mi = L.index("Muuseumikogu"); rec["museum"] = L[mi-1]; rec["collection"] = L[mi+1]
    except ValueError: pass
    for k, f in (("num","Number"),("author","Autor"),("title","Nimetus"),
                 ("essence","Olemus"),("date","Dateering"),("tech","Tehnika"),
                 ("mat","Materjal"),("colour","Värvus")):
        v = field(L, f)
        if v: rec[k] = v
    dims = field(L, "Mõõdud", multi=True)
    if dims: rec["dims"] = "; ".join(d for d in dims[:4] if ':' in d)
    for dk in DESC_KEYS:
        if dk in L:
            i = L.index(dk); v = L[i+1]
            if v and v not in STOP and len(v) > 12:
                rec["desc"] = re.sub(r'\(\)\.?', '', v).strip()[:700]; break
    m = re.search(r'autor:\s*[^(\n]{2,70}\((\d{3,4})\s*[-–]\s*(\d{3,4})?\)', blob)
    if m: rec["life"] = [m.group(1), m.group(2) or ""]
    ai = next((n for n, x in enumerate(L) if x.startswith("autor:")), None)
    if ai is not None:
        cand = [x for x in L[ai:] if len(x) > 200]
        if cand: rec["bio"] = max(cand, key=len)[:1600]
    return rec

R = json.load(open("records.json", encoding="utf-8"))
print("enriching", len(R), flush=True)
done = 0
out = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(parse, R):
        out.append(r); done += 1
        if done % 300 == 0: print("  %d" % done, flush=True)
json.dump(out, open("records.json", "w", encoding="utf-8"), ensure_ascii=False)
print("dated:", sum(1 for r in out if r.get("date")))
print("desc:",  sum(1 for r in out if r.get("desc")))
print("life:",  sum(1 for r in out if r.get("life")))
print("bio:",   sum(1 for r in out if r.get("bio")))
