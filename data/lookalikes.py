# -*- coding: utf-8 -*-
"""Works that look like this: the six nearest museum pictures to each museum picture,
by a CLIP image embedding -> lookalikes.json  {work key: [work keys]}

Every picture in the catalogue (MuIS pisipilt, EKM t2_ preview, a gallery's or the
Mägi Foundation's photograph) is read once into memory, turned into a 512-number
embedding by CLIP ViT-B/32 running on this machine, and discarded -- as the shape
reads did, the picture itself is never kept. The embeddings are cached in embcache/
(not committed) so a later run only reads pictures it has not seen. Every pictured
work gets a row; the works offered in it are museum pictures and the Foundation's
known works only -- gallery stock changes monthly and a row pointing at it would go
stale.

Neighbours are by cosine similarity, never the work's own artist (the artist's own
wall is a click away), at most two by any one artist, and one per title of theirs
(three impressions of one print would otherwise fill three of the six places);
below a similarity of 0.6 nothing is offered.

Run deliberately, with the venv:  .venv-clip/bin/python lookalikes.py   (from data/)
"""
import json, os, re, io, sys, time, threading, queue
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.parse
import numpy as np

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "embcache"; OUT = "lookalikes.json"
K, FLOOR, PER_ARTIST = 6, 0.6, 2
os.makedirs(CACHE, exist_ok=True)

d = json.load(open("data.json", encoding="utf-8"))
A, W = d["artists"], d["works"]
key = lambda w: w.get("k") or re.sub(r"[^A-Z0-9:]", "", (w.get("nu") or "").upper())
def url_of(im):
    if im.startswith("m:"): return f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={im[2:]}"
    if im.startswith("e:"): return "https://digikogu.ekm.ee/static/preview/image/" + re.sub(r"/([^/]+)$", r"/t2_\1", im[2:])
    # g: a gallery's own file; the Foundation's names carry ä and × and – unencoded
    return urllib.parse.quote(im[2:], safe=":/?=&%+~@")

# one embedding per distinct picture; several works can share one (folded impressions)
pics = {}
for w in W:
    im = w.get("im")
    if im and key(w): pics.setdefault(im, []).append(w)
ims = sorted(pics)
target = lambda w: w.get("im", "")[:2] in ("m:", "e:") or w.get("kind") == "known"
print(f"{len(ims):,} pictures for {sum(len(v) for v in pics.values()):,} works; "
      f"{sum(1 for im in ims if target(pics[im][0])):,} of them offered as neighbours", flush=True)

# ---- the cache: embeddings by picture id ----------------------------------------
emb_path, ids_path = os.path.join(CACHE, "emb.npy"), os.path.join(CACHE, "ids.json")
if os.path.exists(emb_path):
    E = np.load(emb_path); ids = json.load(open(ids_path))
else:
    E = np.zeros((0, 512), np.float16); ids = []
have = {i: n for n, i in enumerate(ids)}
todo = [im for im in ims if im not in have]
print(f"{len(have):,} embedded before, {len(todo):,} to read", flush=True)

if todo:
    import torch, open_clip
    from PIL import Image
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    model = model.to(dev).eval()

    def fetch(im):
        for attempt in range(3):
            try:
                r = urllib.request.Request(url_of(im), headers={"User-Agent": UA})
                with urllib.request.urlopen(r, timeout=60) as resp: b = resp.read()
                img = Image.open(io.BytesIO(b)).convert("RGB")
                return im, pre(img)
            except Exception as e:
                time.sleep(2 + 2 * attempt)
        return im, None

    new_ids, new_vecs, failed, n, t0 = [], [], 0, 0, time.time()
    batch_ims, batch_t = [], []
    def flush():
        global batch_ims, batch_t
        if not batch_t: return
        with torch.no_grad():
            x = torch.stack(batch_t).to(dev)
            f = model.encode_image(x).float()
            f = f / f.norm(dim=-1, keepdim=True)
        new_vecs.append(f.cpu().numpy().astype(np.float16)); new_ids.extend(batch_ims)
        batch_ims, batch_t = [], []
    def save():
        global E, ids
        if new_vecs:
            E = np.concatenate([E] + new_vecs); ids = ids + new_ids
            new_vecs.clear(); new_ids.clear()
        np.save(emb_path, E); json.dump(ids, open(ids_path, "w"))

    # MuIS is an API and gets fewer threads than EKM's static previews
    muis = [im for im in todo if im.startswith("m:")]; ekm = [im for im in todo if im.startswith("e:")]
    gal = [im for im in todo if im.startswith("g:")]       # the galleries' files, four at a time as the shape reads
    def run(items, workers):
        global n, failed
        with ThreadPoolExecutor(workers) as ex:
            for im, t in ex.map(fetch, items):
                n += 1
                if t is None: failed += 1
                else:
                    batch_ims.append(im); batch_t.append(t)
                    if len(batch_t) == 64: flush()
                if n % 500 == 0:
                    flush(); save()
                    print(f"  {n:,}/{len(todo):,}  {n/(time.time()-t0):.1f}/s  failed {failed}", flush=True)
    run(ekm, 4); run(muis, 8); run(gal, 4)
    flush(); save()
    print(f"embedded {len(ids):,} pictures, {failed} unreadable", flush=True)
    have = {i: n for n, i in enumerate(ids)}

# ---- the neighbours --------------------------------------------------------------
rows = [im for im in ims if im in have]
X = E[[have[im] for im in rows]].astype(np.float32)
X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
art_of = [pics[im][0]["a"] for im in rows]            # a folded picture's works share an artist
offer = np.array([target(pics[im][0]) for im in rows])  # museum pictures and known works only
tnorm = lambda w: re.sub(r"[^a-zõäöüšž0-9]+", " ", (w.get("t") or "").lower()).strip()
out, sims = {}, []
CH = 1024
for s in range(0, len(rows), CH):
    S = X[s:s + CH] @ X.T                              # cosine, rows are unit length
    for r in range(S.shape[0]):
        i = s + r; row = S[r]; row[i] = -1; row[~offer] = -1
        cand = np.argpartition(-row, 60)[:60]
        cand = cand[np.argsort(-row[cand])]
        picked, per_artist, titles = [], {}, set()
        for j in cand:
            if row[j] < FLOOR: break
            a = art_of[j]
            if a == art_of[i] or per_artist.get(a, 0) >= PER_ARTIST: continue
            w = pics[rows[j]][0]; tk = (a, tnorm(w))
            if tk in titles: continue
            titles.add(tk); per_artist[a] = per_artist.get(a, 0) + 1
            picked.append(key(w)); sims.append(float(row[j]))
            if len(picked) == K: break
        if picked:
            for w in pics[rows[i]]: out[key(w)] = picked
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
sims = np.array(sims)
print(f"LOOKALIKES: {len(out):,} works with neighbours, {len(sims):,} links, similarity median {np.median(sims):.2f}, "
      f"p10 {np.percentile(sims, 10):.2f}, p90 {np.percentile(sims, 90):.2f}")
