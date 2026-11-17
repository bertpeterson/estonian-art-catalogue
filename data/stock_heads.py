# -*- coding: utf-8 -*-
"""Where to cut a gallery's picture so its heads stay in -> stock_heads.json  {im: 0..100 | null}

The Buy Art row on the home page draws each work as a square tile, cut from the middle of the
picture: a tall figure loses its head, a wide group the head at its side. Here each picture for
sale that is not near square, and that CLIP takes for a picture of people, is searched for
faces: square windows across the picture, each given its odds of being a face against words for
what is not one. The cut is then moved along the picture's long side to where it holds the most
of them, as little from the middle as that takes. Kept: where that cut starts, in percent of the
way it can move (CSS object-position), or null where there are no people, no face is found, or
the middle cut is as good. merge.py gives it to the work as "hp".

Each picture is read once, in memory, and nothing of it is kept. Hosts whose robots.txt refuses
scripts are not read. Runs locally only, as lookalikes.py does (CI does not: new stock is cut
from the middle until the next run):

    .venv-clip/bin/python stock_heads.py
"""
import io, json, os, sys, time, urllib.request
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stock_heads.json")
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
REFUSED = {"cms.tutar.ee", "alleegalerii.ee", "www.muis.ee", "digikogu.ekm.ee"}   # robots.txt: not for scripts
SQUARE = 0.1          # a picture within a tenth of square loses nothing worth moving for
PEOPLE, FACE = 0.6, 0.9      # how sure of people in the picture, and of a face in a window
PEOPLE_T = ["a painting of a person", "a portrait of a person", "a picture of human figures", "a drawing of a nude figure",
            "a painting of people", "a figure with a face"]
OTHER_T = ["a landscape painting", "a still life", "an abstract painting", "a cityscape with buildings", "a painting of flowers",
           "a picture of an animal", "a seascape", "an abstract print with shapes", "a painting of trees", "an interior without people",
           "a sculpture", "a ceramic vase", "a pattern"]
FACE_T = ["a human face", "the head of a person", "a face with eyes, nose and mouth", "a painted portrait head"]
REST_T = ["a torso", "hands", "legs and feet", "clothing", "a plain background", "a landscape", "an abstract pattern", "sky",
          "furniture", "a frame", "paper"]


def frame(img, tb):
    """the picture less its file's empty border; tb = [l, t, r, b] in thousandths, or 0"""
    if tb:
        w, h = img.size; l, t, r, b = (x / 1000 for x in tb)
        img = img.crop((round(w * l), round(h * t), round(w * (1 - r)), round(h * (1 - b))))
    return img


def windows(img):
    """square windows across the picture, half a side apart: sides of 0.5, 0.33 and 0.22 of its short side"""
    w, h = img.size; out = set()
    for f in (0.5, 0.33, 0.22):
        s = f * min(w, h); step = s / 2
        for j in range(int((h - s) / step) + 2):
            for i in range(int((w - s) / step) + 2):
                out.add((min(i * step, w - s), min(j * step, h - s), s))
    return sorted(out)


def place(faces, w, h):
    """where the square cut starts, 0..100 along the long side, to hold the most of the faces (x, y, side, odds);
    None if the middle does as well"""
    axis = 1 if h > w else 0; short = min(w, h); room = max(w, h) / short - 1
    if not faces or room <= 0: return None
    def gain(at):
        g = 0
        for f in faces:
            lo, hi = (f[axis] + 0.15 * f[2]) / short, (f[axis] + 0.85 * f[2]) / short     # the face, less its window's edge
            if lo >= at and hi <= at + 1: g += f[3]
        return g
    ats = [room * k / 40 for k in range(41)]; gs = [gain(a) for a in ats]
    if gs[20] >= 0.9 * max(gs): return None
    best = min((a for a, g in zip(ats, gs) if g >= 0.97 * max(gs)), key=lambda a: abs(a - room / 2))
    return round(100 * best / room)


class Finder:
    def __init__(self):
        import torch, open_clip
        self.torch = torch
        self.model, _, self.pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
        self.model.eval()
        tok = open_clip.get_tokenizer("ViT-B-32")
        with torch.no_grad():
            enc = lambda ts: torch.nn.functional.normalize(self.model.encode_text(tok(ts)).float(), dim=-1).numpy()
            self.Tp, self.To, self.Tf, self.Tr = enc(PEOPLE_T), enc(OTHER_T), enc(FACE_T), enc(REST_T)

    def embed(self, ims):
        with self.torch.no_grad():
            f = self.model.encode_image(self.torch.stack([self.pre(i) for i in ims])).float()
            return self.torch.nn.functional.normalize(f, dim=-1).numpy()

    def people(self, v):
        """how sure the whole picture's vector is of people, 0..1"""
        s = 100 * np.concatenate([self.Tp, self.To]) @ v
        p = np.exp(s - s.max()); p /= p.sum()
        return float(p[:len(self.Tp)].sum())

    def head(self, img):
        """the cut for this picture (see place), or None"""
        img = img.convert("RGB"); img.thumbnail((512, 512)); self.faces = []
        if self.people(self.embed([img])[0]) < PEOPLE: return None
        wins = windows(img)
        F = np.concatenate([self.embed([img.crop((x, y, x + s, y + s)) for x, y, s in wins[k:k + 64]]) for k in range(0, len(wins), 64)])
        lg = 100 * F @ np.concatenate([self.Tf, self.Tr]).T
        p = np.exp(lg - lg.max(axis=1, keepdims=True)); p = p[:, :len(self.Tf)].sum(axis=1) / p.sum(axis=1)
        self.faces = [(*wins[i], float(p[i])) for i in range(len(wins)) if p[i] >= FACE]
        return place(self.faces, *img.size)


def fetch(im):
    from PIL import Image
    for attempt in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(im[2:], headers={"User-Agent": UA}), timeout=60) as r:
                img = Image.open(io.BytesIO(r.read())); img.draft("RGB", (1280, 1280)); img.load()
                return im, img
        except Exception: time.sleep(2 + 2 * attempt)
    return im, None


if __name__ == "__main__":
    W = json.load(open(os.environ.get("MUSEAAL_DATA", os.path.join(HERE, "data.json")), encoding="utf-8"))["works"]   # local_cuts.sh: the published data.json
    trim = json.load(open(os.path.join(HERE, "gallery_trim.json"), encoding="utf-8"))
    ims = {}
    for w in W:
        im = w.get("im") or ""
        if w.get("kind") == "gallery" and im.startswith("g:https://") and w.get("pr") and w.get("ir") \
           and abs(w["ir"] - 1) > SQUARE and w["ir"] < 1.8 and urlparse(im[2:]).netloc not in REFUSED:
            ims[im] = w
    have = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    have = {im: v for im, v in have.items() if im in ims}
    todo = [im for im in sorted(ims) if im not in have]
    print(f"stock heads: {len(ims):,} pictures not square, {len(have):,} searched, {len(todo):,} to read", flush=True)
    if todo:
        fd = Finder()
        # the whole picture's vector, where lookalikes.py kept it, says without a fetch that there are no people in it
        cache = os.path.join(HERE, "embcache", "ids.json")
        if os.path.exists(cache):
            ids = {im: n for n, im in enumerate(json.load(open(cache)))}
            E = np.load(os.path.join(HERE, "embcache", "emb.npy"))
            for im in todo:
                if im in ids:
                    v = E[ids[im]].astype(np.float32); v /= np.linalg.norm(v) + 1e-9
                    if fd.people(v) < PEOPLE / 3: have[im] = None
            todo = [im for im in todo if im not in have]
            print(f"{len(todo):,} left after the kept vectors", flush=True)
        with ThreadPoolExecutor(4) as ex:                    # the galleries' servers, four at a time
            for n, (im, img) in enumerate(ex.map(fetch, todo)):
                if img is None: continue
                try: have[im] = fd.head(frame(img, trim.get(im[2:]) or 0))
                except Exception as e: print("  unread:", im, e, flush=True)
                if n % 200 == 199:
                    print(f"  {n + 1:,}", flush=True)
                    json.dump(dict(sorted(have.items())), open(OUT, "w", encoding="utf-8"), separators=(",", ":"))
    json.dump(dict(sorted(have.items())), open(OUT, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"stock_heads.json: {len(have):,} pictures, {sum(1 for v in have.values() if v is not None):,} cut away from the middle", flush=True)
