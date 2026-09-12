# -*- coding: utf-8 -*-
"""Refuse a gallery re-harvest that looks like a broken parser.

    python3 harvest_guard.py before   # snapshot per-gallery counts
    python3 harvest_guard.py after    # compare; exit 1 if any gallery collapsed

A gallery redesigns its site, the parser finds nothing, and the monthly job would
otherwise commit a catalogue with that gallery quietly missing. Selling is normal;
vanishing is not. A gallery that lost more than 40% of its works, or all of them,
fails the run, and a human looks. A gallery that grew is never a problem.
"""
import json, os, sys, collections

here = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(here, "harvest_before.json")
counts = collections.Counter(g["gallery"] for g in json.load(open(os.path.join(here, "gallery_records.json"), encoding="utf-8")))

if sys.argv[1:2] == ["before"]:
    json.dump(counts, open(SNAP, "w"))
    print("before:", dict(counts)); sys.exit(0)

before = json.load(open(SNAP))
bad = []
for gal, was in before.items():
    now = counts.get(gal, 0)
    mark = ""
    if now == 0: mark = "  <- GONE"; bad.append(gal)
    elif now < was * 0.6: mark = f"  <- dropped {100 - now * 100 // was}%"; bad.append(gal)
    print(f"  {gal:22} {was:5} -> {now:5}{mark}")
for gal in counts:
    if gal not in before: print(f"  {gal:22}     new -> {counts[gal]:5}")
os.remove(SNAP)
if bad:
    print("\nREFUSED: a parser has probably broken for:", ", ".join(bad))
    sys.exit(1)
print("\nharvest looks sane")
