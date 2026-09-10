# -*- coding: utf-8 -*-
"""Expand data/raw/*.gz into data/, for anyone starting from a fresh clone.

The 643 MB of cached source pages are not in the repo and do not need to be — but
the parsed harvest they produced does. records.json is the output of 48,655 fetches
against MuIS, whose robots.txt disallows us; we decided not to re-crawl, which is
exactly what makes that file irreplaceable rather than merely inconvenient to lose.

Run this once after cloning, then merge.py and build_site.sh work as they do here.
"""
import gzip, os, shutil, sys

raw = os.path.join(os.path.dirname(__file__) or ".", "raw")
if not os.path.isdir(raw):
    sys.exit("no data/raw — nothing to expand")
n = 0
for name in sorted(os.listdir(raw)):
    if not name.endswith(".gz"): continue
    dest = os.path.join(os.path.dirname(raw), name[:-3])
    if os.path.exists(dest):
        print(f"  keeping existing {name[:-3]}")
        continue
    with gzip.open(os.path.join(raw, name), "rb") as f, open(dest, "wb") as o:
        shutil.copyfileobj(f, o)
    print(f"  {name} -> {name[:-3]}  ({os.path.getsize(dest)/1048576:.1f} MB)")
    n += 1
print(f"\nexpanded {n} file(s)")
