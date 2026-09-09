import re, json, os, time
from concurrent.futures import ThreadPoolExecutor
exec(open('dk_list.py', encoding='utf-8').read().split('pairs=[]')[0])
exec(open('dk_detail.py', encoding='utf-8').read().split('D=json.load')[0].split("exec(open('dk_list.py'")[1].split('\n',1)[1])  # page, ROW, txt, parse_item

T = json.load(open('dk_totals.json', encoding='utf-8'))

# ---- 1. listings by author id, full paging
def listing(item):
    name, v = item
    aid, total = v['aid'], v['total']
    rows, seen = [], set()
    pages = (total + 17) // 18
    for p in range(1, pages + 1):
        url = f"{BASE}/search?searchtype=complex&author_ids={aid}" if p == 1 \
              else f"{BASE}/ekm/search/?_page={p}&_count_all={total}&searchtype=complex&author_ids={aid}"
        rs = parse(get(url))
        if not rs: break
        new = 0
        for r in rs:
            if r['oid'] not in seen: seen.add(r['oid']); rows.append(r); new += 1
        if new == 0: break
        time.sleep(0.12)
    return name, aid, rows
L = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for name, aid, rows in ex.map(listing, T.items()):
        L[name] = {"aid": aid, "rows": rows}
        print("  list %-24s %5d / %d" % (name, len(rows), T[name]['total']), flush=True)
json.dump(L, open('dk_list2.json', 'w', encoding='utf-8'), ensure_ascii=False)
print("LISTED:", sum(len(v['rows']) for v in L.values()), flush=True)

# ---- 2. details for oids not yet fetched
R = json.load(open('dk_records.json', encoding='utf-8'))
have = {r['oid'] for r in R}
keys = {l.split('|')[1].strip(): l.split('|')[0].strip() for l in open('artists2.txt', encoding='utf-8') if l.strip()}
jobs = [(keys.get(name, name), name, r['oid']) for name, v in L.items() for r in v['rows'] if r['oid'] not in have]
print("DETAIL FETCHES:", len(jobs), flush=True)
def work(j):
    key, disp, oid = j
    try: rec = parse_item(oid)
    except Exception: rec = None
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

# ---- 3. author pages: EKM's own biographical facts
def author(item):
    name, v = item
    h = get(f"{BASE}/authors/author_id-{v['aid']}")
    out = {"aid": v['aid']}
    for lm, vm in ROW.findall(h):
        lab = txt(lm).rstrip(':').strip(); val = txt(vm)
        if lab and val: out[lab] = val[:900]
    m = re.search(r'<h1>\s*(.*?)\s*</h1>', h, re.S)
    if m: out["name"] = txt(m.group(1))
    return name, out
AU = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for name, out in ex.map(author, T.items()): AU[name] = out
json.dump(AU, open('dk_authors.json', 'w', encoding='utf-8'), ensure_ascii=False)
print("AUTHORS:", len(AU), " with birth:", sum(1 for a in AU.values() if a.get('Sündinud')), flush=True)
