# -*- coding: utf-8 -*-
"""What a tile cuts from a gallery's picture: "tb" (the empty border, gallery_trim.json) and "hp"
(where a square tile is cut so the heads stay in, stock_heads.json), given to a work.

merge.py gives them to every work as it writes data.json. The two files are measured on one machine
(CLIP; local_cuts.sh, daily), after the weekly run has brought the new stock in, so a build gives them
to the works that came since and have none yet (stock_check.py apply -> late()): the measurements
go live with the next build, not with the next merge.
"""
import json, os

here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    f = os.path.join(here, name)
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}


def cut(w, trim, heads):
    """one work's "tb" and "hp", where it has none; True if either is new"""
    im = w.get("im") or ""
    new = False
    # "tb" is what the tiles cut away, as CSS inset() takes it (top right bottom left), and the shape
    # becomes the shape of what is left
    if "tb" not in w and im.startswith("g:") and trim.get(im[2:]):
        l, t, r, b = (x / 1000 for x in trim[im[2:]])
        w["tb"] = " ".join(f"{x * 100:.1f}%" for x in (t, r, b, l))
        if w.get("ir"): w["ir"] = round(w["ir"] * (1 - t - b) / (1 - l - r), 3)
        new = True
    # "hp", as CSS object-position takes it, along the picture's long side
    if "hp" not in w and heads.get(im) is not None and w.get("ir"):
        w["hp"] = f"50% {heads[im]}%" if w["ir"] > 1 else f"{heads[im]}% 50%"
        new = True
    return new


def late(works):
    """the works measured since data.json was written: how many were given a cut"""
    trim, heads = _load("gallery_trim.json"), _load("stock_heads.json")
    return sum(cut(w, trim, heads) for w in works)
