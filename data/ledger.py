# -*- coding: utf-8 -*-
"""The ledger of gallery listings -> gallery_seen.json, gallery_past.json

A gallery listing that sells simply left the catalogue at the next harvest: a work
seen with a real holder one month, gone the next, with nothing to say it had been
there. The ledger keeps every gallery record the catalogue has ever verified, with
the month it was first and last seen for sale.

    python3 ledger.py        # after every gallery harvest, before merge.py

gallery_records.json is this month's harvest. Each record goes into the ledger (or
has its last-seen month moved up). A ledger record not in this month's harvest is a
past listing: sold if the gallery said so when it was last seen, otherwise no longer
listed -- sold or withdrawn, which cannot be told apart from outside. Those are
written to gallery_past.json for merge.py, which gives them their own kind. A
record that reappears goes back to being stock; the ledger just keeps counting.
"""
import json, os, datetime

here = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(here, "gallery_seen.json")
month = datetime.date.today().strftime("%Y-%m")

now = {g["gid"]: g for g in json.load(open(os.path.join(here, "gallery_records.json"), encoding="utf-8"))}
seen = json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}

new = returned = 0
for gid, g in now.items():
    e = seen.get(gid)
    if not e: seen[gid] = {"first": month, "last": month, "rec": g}; new += 1
    else:
        if e["last"] != month and e.get("gone"): returned += 1
        e["last"] = month; e["rec"] = g; e.pop("gone", None)
past = []
for gid, e in seen.items():
    if gid in now: continue
    e["gone"] = e.get("gone") or month                   # the first month it was missing
    r = dict(e["rec"]); r["last"] = e["last"]
    r["sold"] = bool(e["rec"].get("sold"))               # the gallery's word, if it gave one
    past.append(r)

json.dump(seen, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False)
json.dump(past, open(os.path.join(here, "gallery_past.json"), "w", encoding="utf-8"), ensure_ascii=False)
marked = sum(1 for g in now.values() if g.get("sold"))
print(f"ledger: {len(seen)} listings ever seen; this month {len(now)} ({marked} the gallery marks sold), new {new}, back {returned}; "
      f"no longer listed {len(past)} ({sum(1 for r in past if r['sold'])} sold, {sum(1 for r in past if not r['sold'])} gone)")
