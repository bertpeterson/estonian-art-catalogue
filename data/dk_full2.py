import re, json, os, gzip, time
from concurrent.futures import ThreadPoolExecutor
exec(open('dk_list.py', encoding='utf-8').read().split('pairs=[]')[0])
exec(open('dk_detail.py', encoding='utf-8').read().split('D=json.load')[0].split("exec(open('dk_list.py'")[1].split('\n',1)[1])
L = json.load(open('dk_list2.json', encoding='utf-8'))
R = json.load(open('dk_records.json', encoding='utf-8'))
have = {r['oid'] for r in R}
keys = {l.split('|')[1].strip(): l.split('|')[0].strip() for l in open('artists2.txt', encoding='utf-8') if l.strip()}
jobs = [(keys.get(name, name), name, r['oid']) for name, v in L.items() for r in v['rows'] if r['oid'] not in have]
print("DETAIL FETCHES:", len(jobs), flush=True)
# sanity: one synchronous fetch first so a bug fails loudly instead of silently
t = parse_item(jobs[0][2]); assert t and t.get("Pealkiri") is not None, t; print("probe ok:", t.get("Pealkiri"), flush=True)
def work(j):
    key, disp, oid = j
    try: rec = parse_item(oid)
    except Exception as e:
        print("ERR", oid, repr(e)[:80], flush=True); rec = None
    if rec: rec["artist_key"] = key; rec["artist"] = disp
    return rec
done = 0
with ThreadPoolExecutor(max_workers=5) as ex:
    for rec in ex.map(work, jobs):
        done += 1
        if rec: R.append(rec)
        if done % 500 == 0: print("  detail %d/%d" % (done, len(jobs)), flush=True)
json.dump(R, open('dk_records.json', 'w', encoding='utf-8'), ensure_ascii=False)
print("EKM RECORDS:", len(R), flush=True)
