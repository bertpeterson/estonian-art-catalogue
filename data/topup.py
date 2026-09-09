import re, json, time, unicodedata
exec(open('harvest.py').read().split('names = [')[0])
OVR = [
  ("Kormašov, Nikolai", "Nikolai Kormašov", "Kormašov", "Kormašov, Nikolai"),
  ("Navitrolla",        "Navitrolla",        "Navitrolla", "Navitrolla, pseud."),
  ("Farkas, Dénes",     "Dénes Farkas",      "Farkas",    "Farkas, Dénes Kalev"),
]
def harvest(query, accept, pages=5):
    o = opener()
    h = get(o, BASE+"/otsivaade/lihtotsing"); fd = formdata(h, "globalSearchFrom")
    post(o, BASE+"/index.layout.globalsearchfrom", {"t:formdata": fd, "globalSearchInput": query, "submit_0": "Otsi"})
    h = get(o, BASE+"/search"); fd2 = formdata(h, "searchForm")
    post(o, BASE+"/search.searchform", {"t:formdata": fd2, "searchName": "", "searchDescription": "",
        "searchPaev1":"","searchKuu1":"","searchAasta1":"","searchPaev2":"","searchKuu2":"","searchAasta2":"",
        "textfield": query, "searchPerson": "", "submitSearch": "Otsi"})
    get(o, BASE+"/search.pagination:pageitemcountevent/100")
    acc, seen = [], set()
    for p in range(pages):
        if p: get(o, BASE+"/search.pagination:page/%d" % p)
        rs = rows(get(o, BASE+"/search"))
        if not rs: break
        for x in rs:
            if x["id"] in seen: continue
            seen.add(x["id"])
            if any(a.strip() == accept for a in re.split(r'[;/]', x["author"])): acc.append(x)
        if len(rs) < 100: break
    return acc

d = json.load(open("harvest2.json", encoding="utf-8"))
for key, disp, query, accept in OVR:
    acc = harvest(query, accept)
    d[key] = {"display": disp, "rows": acc}
    print("%-24s %d" % (disp, len(acc)))
for dead in ["Möller, Otto Friedrich von", "Kangro, Kirke"]:
    if dead in d and not d[dead]["rows"]:
        del d[dead]; print("dropped (no MuIS records):", dead)
json.dump(d, open("harvest2.json", "w", encoding="utf-8"), ensure_ascii=False)
print("artists:", len(d), "rows:", sum(len(v["rows"]) for v in d.values()))
