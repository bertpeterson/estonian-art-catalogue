import re, json, os, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
exec(open('harvest.py').read().split('names = [')[0])

MAXPAGES = 5
pairs = []
for l in open('artists2.txt', encoding='utf-8'):
    l = l.strip()
    if not l: continue
    key, disp = l.split('|')
    pairs.append((key, disp))

def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in s if not unicodedata.combining(c)))

def harvest(pair):
    key, disp = pair
    o = opener()
    h = get(o, BASE + "/otsivaade/lihtotsing"); fd = formdata(h, "globalSearchFrom")
    if not fd: return key, disp, []
    post(o, BASE + "/index.layout.globalsearchfrom",
         {"t:formdata": fd, "globalSearchInput": disp, "submit_0": "Otsi"})
    h = get(o, BASE + "/search"); fd2 = formdata(h, "searchForm")
    if not fd2: return key, disp, []
    post(o, BASE + "/search.searchform",
         {"t:formdata": fd2, "searchName": "", "searchDescription": "",
          "searchPaev1": "", "searchKuu1": "", "searchAasta1": "",
          "searchPaev2": "", "searchKuu2": "", "searchAasta2": "",
          "textfield": disp, "searchPerson": "", "submitSearch": "Otsi"})
    get(o, BASE + "/search.pagination:pageitemcountevent/100")
    acc, seen = [], set()
    nk = norm(key)
    for p in range(MAXPAGES):
        if p: get(o, BASE + "/search.pagination:page/%d" % p)
        rs = rows(get(o, BASE + "/search"))
        if not rs: break
        for x in rs:
            if x["id"] in seen: continue
            seen.add(x["id"])
            # keep only rows whose author field actually contains this artist
            if any(norm(a) == nk for a in re.split(r'[;/]', x["author"])):
                acc.append(x)
        if len(rs) < 100: break
        time.sleep(0.25)
    return key, disp, acc

res = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for key, disp, acc in ex.map(harvest, pairs):
        res[key] = {"display": disp, "rows": acc}
        print("%-26s %4d" % (disp, len(acc)), flush=True)
json.dump(res, open("harvest2.json", "w", encoding="utf-8"), ensure_ascii=False)
n0 = [k for k, v in res.items() if not v["rows"]]
print("TOTAL ROWS:", sum(len(v["rows"]) for v in res.values()))
print("NO HITS (%d): %s" % (len(n0), ", ".join(n0)))
