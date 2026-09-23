# -*- coding: utf-8 -*-
"""Upcoming auction lots -> upcoming_records.json

Each auction harvester reads the house's sales and keeps the results; a sale still to
come used to be skipped. Its lots are now kept here instead -- artist, title, year,
technique, size, the starting price as the house publishes it, the sale, its date and
a link to the lot -- and replaced wholesale on every run, so a lot is here only while
its sale is ahead. No live bids (they change by the hour and would be stale on the
page), no pictures (the rule for auction lots), and never a work's own price beyond
the house's published starting price. merge.py joins them to the artists.
"""
import json, os, datetime
OUT = os.path.join(os.path.dirname(__file__) or ".", "upcoming_records.json")

def emit(house, lots):
    """replace this house's upcoming lots with these; drop any whose sale date has passed"""
    today = datetime.date.today().isoformat()
    lots = [r for r in lots if not r.get("date") or r["date"] >= today]
    prev = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    keep = [r for r in prev if r["house"] != house and (not r.get("date") or r["date"] >= today)]
    json.dump(sorted(keep + lots, key=lambda r: (r.get("date") or "9", r["house"], r["artist"], r["title"])),
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"  UPCOMING {house}: {len(lots)} lots in {len({r['sale'] for r in lots})} sale(s)")
