# -*- coding: utf-8 -*-
"""Art by mood for the galleries' stock -> stock_moods.json

moods.py scores the museum pictures; gallery stock changes weekly, so it is scored here,
on the same scale, from the words and the museum pictures' spread that moods.py leaves
in mood_words.npz. A picture's score for a word is its cosine to the word, less its own
mean over the word's set (moods, or subjects), as a z-score against the museum pictures.

Only works for sale with the gallery's picture. Each picture is embedded once -- from
embcache/ where lookalikes.py already read it (on the Mac), else fetched from the
gallery's server and discarded, as the shapes are -- and its scores kept by picture, so
a week's run reads only the new stock. A picture no longer for sale leaves the file.
Kept per picture: the words it answers to best (z >= 0.8), at most 16, one decimal.
And in stock_taste.json the picture as taste.py's 48 bytes, in the museum pictures' space,
for Buy art's For you; a picture missing from either file is read again.

    python3 stock_moods.py --todo    exit 0 if there are pictures to read (CI installs CLIP only then)
    .venv-clip/bin/python stock_moods.py
"""
import json, os, sys, io, time, urllib.request
import numpy as np
import taste
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stock_moods.json")
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
MIN_Z, TOP = 0.8, 16

W = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))["works"]
ims = sorted({w["im"] for w in W if w.get("kind") == "gallery" and (w.get("im") or "").startswith("g:")})
have = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
have = {im: v for im, v in have.items() if im in set(ims)}          # gone from stock: gone from here
TOUT = os.path.join(HERE, "stock_taste.json")
tv = json.load(open(TOUT, encoding="utf-8")) if os.path.exists(TOUT) else {}
tv = {im: v for im, v in tv.items() if im in set(ims)}
todo = [im for im in ims if im not in have or im not in tv]
if "--todo" in sys.argv:
    print(f"{len(todo)} stock pictures to score"); sys.exit(0 if todo else 1)

M = np.load(os.path.join(HERE, "mood_words.npz"))
T, mu, sd, split = M["T"], M["mu"], M["sd"], int(M["split"])
def score(x):
    x = x / (np.linalg.norm(x) + 1e-9); s = T @ x
    s = np.concatenate([s[:split] - s[:split].mean(), s[split:] - s[split:].mean()])
    z = (s - mu) / sd
    best = [j for j in np.argsort(-z) if z[j] >= MIN_Z][:TOP]
    return [[int(j), round(float(z[j]), 1)] for j in best]

vec = {}
cache = os.path.join(HERE, "embcache", "ids.json")
if os.path.exists(cache) and todo:
    ids = {im: n for n, im in enumerate(json.load(open(cache)))}
    E = np.load(os.path.join(HERE, "embcache", "emb.npy"))
    for im in todo:
        if im in ids: vec[im] = E[ids[im]].astype(np.float32)
    print(f"{len(vec):,} of {len(todo):,} from embcache/", flush=True)
rest = [im for im in todo if im not in vec]
if rest:
    import torch, open_clip
    from PIL import Image
    model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k"); model.eval()
    def fetch(im):
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(im[2:], headers={"User-Agent": UA}), timeout=60) as r:
                    img = Image.open(io.BytesIO(r.read())); img.draft("RGB", (448, 448))
                    return im, pre(img.convert("RGB"))
            except Exception: time.sleep(2 + 2 * attempt)
        return im, None
    with ThreadPoolExecutor(4) as ex:                    # the galleries' servers, four at a time
        got = [(im, t) for im, t in ex.map(fetch, rest) if t is not None]
    with torch.no_grad():
        for k in range(0, len(got), 64):
            b = got[k:k + 64]
            f = model.encode_image(torch.stack([t for _, t in b])).float().numpy()
            for (im, _), v in zip(b, f): vec[im] = v
    print(f"{len(got):,} of {len(rest):,} fetched and embedded", flush=True)
for im, v in vec.items(): have[im] = score(v)
if vec: tv.update(zip(vec, taste.encode(np.stack(list(vec.values())), *taste.load())))
json.dump(dict(sorted(have.items())), open(OUT, "w", encoding="utf-8"), separators=(",", ":"))
json.dump(dict(sorted(tv.items())), open(TOUT, "w", encoding="utf-8"), separators=(",", ":"))
print(f"stock_moods.json: {len(have):,} pictures for sale scored; stock_taste.json: {len(tv):,}", flush=True)
