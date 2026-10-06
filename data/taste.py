# -*- coding: utf-8 -*-
"""Taste: each museum picture as 48 small numbers -> taste_vecs.json

My list (the bookmark on a register row, a Buy art card, a mood tile) is the works a
visitor kept. Buy art's For you puts first the works for sale whose pictures are nearest
one of theirs, and that has to be worked out in the browser, where the list is. So each
picture's CLIP embedding (lookalikes.py, cached in embcache/) is brought down to its 48
main directions and to a byte each: 48 bytes a picture. Measured 2026-10-06 on the
37,760 cached pictures: 90% of a picture's true ten nearest are among the fifty nearest
by the 48 bytes (64 bytes: 94%, 32: 83%), and a ranking by taste needs no finer.

The directions (a PCA of the museum pictures) are fitted once and kept in
taste_proj.npz, because stock_moods.py puts the galleries' stock into the same space
in CI, week by week (stock_taste.json). Refit only with both files redone.

Only museum pictures (and the Mägi Foundation's known works): gallery stock changes
weekly and is stock_moods.py's. Kept per picture, as base64 of 48 signed bytes.

    python3 taste.py        (from data/; after lookalikes.py; numpy only)
"""
import base64, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ, OUT, DIMS = os.path.join(HERE, "taste_proj.npz"), os.path.join(HERE, "taste_vecs.json"), 48

def load():
    """the fixed projection: mean, directions, and the scale a unit vector's numbers are read in"""
    P = np.load(PROJ)
    return P["mu"], P["V"], float(P["q"])

def encode(E, mu, V, q):
    """embeddings (n x 512) -> base64 strings of DIMS signed bytes, each vector of unit length before rounding"""
    E = E.astype(np.float32); E /= np.linalg.norm(E, axis=1, keepdims=True) + 1e-9
    X = (E - mu) @ V.T; X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    B = np.clip(np.round(X / q * 127), -127, 127).astype(np.int8)
    return [base64.b64encode(b.tobytes()).decode() for b in B]

if __name__ == "__main__":
    W = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))["works"]
    ims = sorted({w["im"] for w in W if w.get("kind") != "gallery" and (w.get("im") or "")[:2] in ("e:", "m:")})
    ids = json.load(open(os.path.join(HERE, "embcache", "ids.json")))
    at = {im: n for n, im in enumerate(ids)}
    E = np.load(os.path.join(HERE, "embcache", "emb.npy"))
    have = [im for im in ims if im in at]
    M = E[[at[im] for im in have]].astype(np.float32)
    if not os.path.exists(PROJ):
        U = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
        mu = U.mean(0)
        S = U[np.random.default_rng(0).choice(len(U), min(12000, len(U)), replace=False)] - mu
        V = np.linalg.svd(S, full_matrices=False)[2][:DIMS]
        X = (U - mu) @ V.T; X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
        q = float(np.quantile(np.abs(X), 0.999))         # the rare larger number is clipped, the rest keep their steps
        np.savez_compressed(PROJ, mu=mu.astype(np.float32), V=V.astype(np.float32), q=np.float32(q))
        print(f"taste_proj.npz: {DIMS} directions fitted on {len(U):,} museum pictures")
    out = dict(zip(have, encode(M, *load())))
    json.dump(out, open(OUT, "w", encoding="utf-8"), separators=(",", ":"), sort_keys=True)
    print(f"taste_vecs.json: {len(out):,} of {len(ims):,} museum pictures ({len(ims) - len(have):,} not in embcache/: run lookalikes.py)")
