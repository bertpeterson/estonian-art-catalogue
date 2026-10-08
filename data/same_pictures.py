# -*- coding: utf-8 -*-
"""One picture under two names: pictures of one artist that CLIP finds identical
(cosine 0.99 or more) though the holder filed them under different image ids ->
same_pictures.json  {picture id: the group's first picture id}

MuIS attaches one photograph of a sheet or an album page to each work on it -- Karl
August Hermann's four poets' portraits, Žukovski's six Jelagin views -- and a gallery
lists one work on its English and its Estonian page. On an artist's wall that is the
same picture shown four or six times; merge.py gives such records one `sp` and the
wall shows the picture once, marked x4. Records that share one image id need no entry
here: merge.py groups those itself.

Below 0.99 most pairs are different works of one series -- Eelma's three mirrors,
Zimmermann's skulls -- and stay apart, unless something else says it is one picture:
one object numbered two ways (MuIS's sheet "21885/ab" beside EKM's side "21885a",
0.95 or more -- the back, "21885b", is another picture and stays), or two impressions
of a print under two titles (Mülber's "Mees mõõgaga. Mapist ..." and "Mees mõõgaga.
IV leht mapist ...", the same words before the first full stop, 0.97 or more; not
two sheets of one folder, "171/7" and "171/9", which are a series).

Reads the embeddings lookalikes.py cached in embcache/; fetches nothing. Run after
lookalikes.py, with the venv:  .venv-clip/bin/python same_pictures.py   (from data/)
"""
import json, re, collections
import numpy as np

CUT, SAME_OBJECT, SAME_PRINT = 0.99, 0.95, 0.97
d = json.load(open("data.json", encoding="utf-8"))
E = d["vocab"]["e"]
MULTI = {"Print", "Sculpture", "Relief", "Illustration", "Bookplate", "Poster"}
ids = json.load(open("embcache/ids.json"))
emb = np.load("embcache/emb.npy").astype(np.float32)
pos = {k: i for i, k in enumerate(ids)}

# the object a number names, sides and sub-number spellings aside
obj = lambda w: w.get("nu") and (w.get("mu"), re.sub(r"\s+", " ", re.sub(r"\bj\s+", "", re.sub(r"(\d)/(?=\d)", r"\1:",
    re.sub(r"(\d)[a-z]\b", r"\1", re.sub(r"/[a-z](-[a-z])?\b", "", w["nu"], flags=re.I), flags=re.I)))).strip())
# sheets of one folder -- "171/7" and "171/9" -- are a series, not two impressions
def parent(w):
    m = re.search(r"\d[\d:/]*[:/]\d+", w.get("nu") or "")
    return m and (w.get("mu"), re.split(r"[:/](?=\d+$)", m.group())[0])
# a print's title up to its first full stop or slash
head = lambda w: E[w["e"]] in MULTI and re.split(r"[./]", str(w["t"]).lower())[0].strip() if isinstance(w.get("e"), int) else None

by = collections.defaultdict(lambda: collections.defaultdict(list))
for w in d["works"]:
    if w.get("im") in pos: by[w["a"]][w["im"]].append(w)

par = {}
def find(x):
    while par.setdefault(x, x) != x:
        par[x] = par[par[x]]; x = par[x]
    return x
why = collections.Counter()
for a, recs in by.items():
    ims = sorted(recs)
    if len(ims) < 2: continue
    X = emb[[pos[i] for i in ims]]; S = X @ X.T
    for i, j in zip(*np.where(np.triu(S, 1) >= SAME_OBJECT)):
        s, wi, wj = S[i, j], recs[ims[i]], recs[ims[j]]
        if s >= CUT: why["identical"] += 1
        elif {obj(x) for x in wi} & {obj(x) for x in wj} - {None, False}: why["one object"] += 1
        elif s >= SAME_PRINT and {head(x) for x in wi} & {head(x) for x in wj} - {None, False, ""} \
                and not {parent(x) for x in wi} & {parent(x) for x in wj} - {None}: why["one print"] += 1
        else: continue
        ri, rj = find(ims[i]), find(ims[j])
        if ri != rj: par[max(ri, rj)] = min(ri, rj)

out = {k: find(k) for k in sorted(par) if find(k) != k}
json.dump(out, open("same_pictures.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"same_pictures.json: {len(out)} pictures repeat {len(set(out.values()))} others; pairs: {dict(why)}")
