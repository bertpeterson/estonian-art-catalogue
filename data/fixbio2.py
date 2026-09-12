# -*- coding: utf-8 -*-
"""Re-read each MuIS biography from the cached page as a whole, not its longest paragraph.

details.py kept "the longest paragraph containing 'sündis'". The museum's biography is
usually two or three paragraphs -- birth, training, career -- and the longest is
often the last, so the page opened Priidu Aavik's life at "on returning to Estonia".
This takes the whole run of long paragraphs around the birth one. Cached pages only;
MuIS is not fetched.
"""
import json, gzip, re, os
MU = json.load(open("records.json", encoding="utf-8"))
def flat(h):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t); t = re.sub(r"[ \t\xa0]+", " ", t)
    return [x.strip() for x in t.split("\n") if x.strip()]
def whole_bio(L):
    idx = [i for i, x in enumerate(L) if len(x) > 120 and "sündis" in x.lower()]
    if not idx: return None
    i = idx[0]; lo = hi = i
    while lo > 0 and len(L[lo-1]) > 120 and not L[lo-1].endswith(":"): lo -= 1
    while hi + 1 < len(L) and len(L[hi+1]) > 120: hi += 1
    return "\n\n".join(L[lo:hi+1])[:2400]
changed = longer = 0
for r in MU:
    if not r.get("bio"): continue
    p = f"cache/{r['id']}.html.gz"
    if not os.path.exists(p): continue
    b = whole_bio(flat(gzip.open(p, "rt", encoding="utf-8", errors="replace").read()))
    if b and b != r["bio"]:
        if len(b) > len(r["bio"]): longer += 1
        r["bio"] = b; changed += 1
json.dump(MU, open("records.json", "w", encoding="utf-8"), ensure_ascii=False)
print("records with a biography rewritten:", changed, "| now longer:", longer)
