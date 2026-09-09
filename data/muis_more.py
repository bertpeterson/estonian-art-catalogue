import re, json, os, gzip, time, unicodedata, collections
from concurrent.futures import ThreadPoolExecutor
exec(open('harvest.py').read().split('names = [')[0])
src = open('enrich.py', encoding='utf-8').read()
exec(src.split('R = json.load')[0])            # STOP, flat, field, op, page, DESC_KEYS, parse
sel = open('details.py', encoding='utf-8').read()
exec(sel.split('def select')[0].split("exec(open('harvest.py')")[1].split('\n',1)[1])  # ART, ART_MUSEUMS, BAD_TITLE, is_art, keyt

H = json.load(open("harvest2.json", encoding="utf-8"))
R = json.load(open("records.json", encoding="utf-8"))
have = {r["id"] for r in R}
jobs = []
for key, v in H.items():
    for r in v["rows"]:
        if r["id"] in have: continue
        t = r["title"].strip()
        if not is_art(r["essence"]) or not t or len(t) < 2 or BAD_TITLE.match(t): continue
        coll, _, mus = r["coll"].rpartition(",")
        jobs.append({"id": r["id"], "artist_key": key, "artist": v["display"], "num": r["num"],
                     "author": r["author"], "title": t, "essence": r["essence"],
                     "collection": coll.strip(), "museum": mus.strip()})
print("new MuIS detail fetches:", len(jobs), flush=True)
print("by museum:", collections.Counter(j["museum"] for j in jobs).most_common(6), flush=True)

AUT = re.compile(r'autor:\s*([^(\n]{2,70}?)\s*\((\d{3,4})\s*[-–]\s*(\d{3,4})?\)')
def norm(s):
    s = unicodedata.normalize('NFKD', s.lower()); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]', '', s)
def work(j):
    try:
        rec = parse(dict(j))
        # name-matched life dates only
        h = page(j["id"]); txt = re.sub(r'<[^>]+>', '\n', h or "")
        rec.pop("life", None)
        for m in AUT.finditer(txt):
            if norm(m.group(1)) == norm(j["artist_key"]):
                rec["life"] = [m.group(2), m.group(3) or ""]; break
        return rec
    except Exception:
        return None
out, done = [], 0
with ThreadPoolExecutor(max_workers=5) as ex:
    for rec in ex.map(work, jobs):
        done += 1
        if rec: out.append(rec)
        if done % 500 == 0: print("  %d/%d" % (done, len(jobs)), flush=True)
R.extend(out)
json.dump(R, open("records.json", "w", encoding="utf-8"), ensure_ascii=False)
print("MuIS records now:", len(R), " added:", len(out), " dated:", sum(1 for r in out if r.get("date")))
