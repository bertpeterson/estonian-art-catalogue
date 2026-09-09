import re, json, gzip, os, unicodedata, collections
def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]', '', s)

R = json.load(open("records.json", encoding="utf-8"))
AUT = re.compile(r'autor:\s*([^(\n]{2,70}?)\s*\((\d{3,4})\s*[-–]\s*(\d{3,4})?\)')
fixed = dropped = 0
for r in R:
    p = "cache/%s.html.gz" % r["id"]
    if not os.path.exists(p): continue
    with gzip.open(p, "rt", encoding="utf-8") as f: h = f.read()
    txt = re.sub(r'<[^>]+>', '\n', h)
    key = norm(r["artist_key"])
    hit = None
    for m in AUT.finditer(txt):
        if norm(m.group(1)) == key:
            hit = [m.group(2), m.group(3) or ""]; break
    old = r.get("life")
    if hit: r["life"] = hit
    elif old: r.pop("life"); dropped += 1
    if hit and old != hit: fixed += 1
json.dump(R, open("records.json", "w", encoding="utf-8"), ensure_ascii=False)
print("corrected:", fixed, " removed (wrong person):", dropped)
per = collections.defaultdict(collections.Counter)
for r in R:
    if r.get("life"): per[r["artist"]][tuple(r["life"])] += 1
for n in ["Gerhard von Kügelgen","Eduard Wiiralt","Johann Köler","Konrad Mägi","Kristjan Raud","Ülo Sooster","Julie Hagen-Schwarz","August Weizenberg"]:
    print(f"  {n:24s} {per.get(n) and per[n].most_common(2)}")
print("artists with life now:", len(per))
