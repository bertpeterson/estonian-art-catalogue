# -*- coding: utf-8 -*-
"""Upcoming auction lots -> upcoming_records.json

Each auction harvester reads the house's sales and keeps the results; a sale still to
come used to be skipped. Its lots are now kept here instead -- artist, title, year,
technique, size, the starting price as the house publishes it, the sale, its date and
a link to the lot, the house's picture of it -- and replaced wholesale on every run, so a
lot is here only while its sale is ahead. A lot on offer is shown like a gallery's stock:
its picture embedded from the house's server, never copied, and gone with the sale. No
live bids (they change by the hour and would be stale on the page), and never a work's
own price beyond the house's published starting price. merge.py joins them to the artists.
"""
import json, os, datetime
OUT = os.path.join(os.path.dirname(__file__) or ".", "upcoming_records.json")

def emit(house, lots):
    """replace this house's upcoming lots with these; drop any whose sale date has passed"""
    today = datetime.date.today().isoformat()
    # a sale over several days has its lots dated by the first (sales_by_hand.json gives the last); a sale known
    # only by its month ("2026-11") lasts the month -- as build_upcoming.py reads them
    hand = os.path.join(os.path.dirname(OUT), "sales_by_hand.json")
    end = {(x["house"], x["date"]): x["end"] for x in (json.load(open(hand, encoding="utf-8")) if os.path.exists(hand) else []) if x.get("end")}
    ahead = lambda r: not r.get("date") or (end.get((r["house"], r["date"])) or r["date"]) >= today[:len(r["date"])]
    lots = [r for r in lots if ahead(r)]
    prev = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    keep = [r for r in prev if r["house"] != house and ahead(r)]
    json.dump(sorted(keep + lots, key=lambda r: (r.get("date") or "9", r["house"], r["artist"], r["title"])),
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"  UPCOMING {house}: {len(lots)} lots in {len({r['sale'] for r in lots})} sale(s)")
