import re, json, os, sys
from concurrent.futures import ThreadPoolExecutor
# page(), parse_item(), get(), BASE  — reuse the existing detail scraper verbatim
exec(open('dk_detail.py', encoding='utf-8').read().split("D=json.load")[0])

UNK = re.compile(r'\bTundmatu|\bTundmata', re.I)
lst  = {r["oid"]: r for r in json.load(open('ekm_all_list.json', encoding='utf-8'))}
new  = json.load(open('ekm_all_new.json', encoding='utf-8'))
R    = json.load(open('dk_records.json', encoding='utf-8'))
have = {r["oid"] for r in R}

# attributed only — the catalogue excludes anonymous works by design
jobs = [(o, lst[o]["author"]) for o in new
        if o not in have and o in lst
        and lst[o].get("author", "").strip() and not UNK.search(lst[o]["author"])]
print("TO FETCH: %d (of %d enumerated)" % (len(jobs), len(new)), flush=True)

probe = parse_item(jobs[0][0])
assert probe and probe.get("Pealkiri") is not None, probe
print("probe ok:", probe.get("Pealkiri"), flush=True)

def work(j):
    oid, author = j
    try: rec = parse_item(oid)
    except Exception as e:
        print("ERR", oid, repr(e)[:70], flush=True); return None
    if rec: rec["artist"] = author; rec["artist_key"] = author
    return rec

done = added = 0
with ThreadPoolExecutor(max_workers=5) as ex:
    for rec in ex.map(work, jobs):
        done += 1
        if rec: R.append(rec); added += 1
        if done % 500 == 0:
            print("  %d/%d  added %d" % (done, len(jobs), added), flush=True)
            json.dump(R, open('dk_records.json', 'w', encoding='utf-8'), ensure_ascii=False)

json.dump(R, open('dk_records.json', 'w', encoding='utf-8'), ensure_ascii=False)
print("DONE. fetched %d, dk_records now %d" % (added, len(R)), flush=True)
