# -*- coding: utf-8 -*-
"""The lighter address of a picture, for a tile: {im: lighter im}.

A tile is under 300 pixels wide, and some holders' smallest picture is not:
- a gallery's own 768-pixel copy of its stock where data/img_small.py found one;
- MuIS has one size only. Its "pisipilt" (thumbnail) is the full scan -- 3,421 x 4,060
  pixels and 1.8 MB for one Laikmaa, 312 KB on average across the landing's wall. EKM
  publishes a 480-pixel preview of its own works (t2_, about 35 KB), and 9,500 of the
  MuIS-pictured works are EKM's. The tile takes that preview where the two photographs
  have the same shape (within 3%), so the preview frames the work as the MuIS scan the
  tile's shape was measured on does; where they differ -- one photograph with a colour
  chart, the other cropped -- the MuIS scan stays.
The opened record still reads the full picture from its shard, and links to the MuIS
file. Every picture stays on its holder's server; nothing is copied.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
_j = lambda f: json.load(open(os.path.join(HERE, f), encoding="utf-8")) if os.path.exists(os.path.join(HERE, f)) else {}

def thumbs(works):
    small = {k: v for k, v in _j("img_small.json").items() if v}
    ekm, er, mr = _j("ekm_images.json"), _j("ekm_shapes.json"), _j("muis_shapes.json")
    for w in works:
        im, oi = w.get("im") or "", str(w.get("oi") or "")
        if im.startswith("m:") and oi in ekm:
            a, b = mr.get(im[2:]), er.get(oi)
            if a and b and abs(a - b) / a <= 0.03: small[im] = "e:" + ekm[oi]
    return small
