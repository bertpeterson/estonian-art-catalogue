# -*- coding: utf-8 -*-
"""A house's results, with the past sales this run could not read kept as they were.

Every *_auctions.py replaced its house's lots with what it read. A sale page that timed
out or was refused came back empty and that sale's lots went with it; read cold on
GitHub's runners (12 and 15 Oct 2026), enough went to trip data_guard.py's 3%. A past
sale's results do not change, so a sale this run has no lot of keeps its lots from the
last run -- unless a lot id came back under another sale name, which is a rename.
"""

def merged(prev, house, recs):
    sales, aids = {r["sale"] for r in recs}, {r["aid"] for r in recs}
    kept = [r for r in prev if r["house"] == house and r["sale"] not in sales and r["aid"] not in aids]
    if kept:
        names = sorted({r["sale"] for r in kept})
        print(f"  {house}: {len(kept)} lots of {len(names)} sale(s) not read this run, kept: {'; '.join(names)[:300]}", flush=True)
    return [r for r in prev if r["house"] != house] + kept + recs
