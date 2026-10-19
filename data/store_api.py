# -*- coding: utf-8 -*-
"""One page of a gallery's WooCommerce Store API listing (/wp-json/wc/store/v1/products).

Allee, Artner, Artman, Art & Tonic, Vernissage and NOBA are read a page of 100 at a time
until a page comes back empty -- which past the last page it does, with a 200. Each script
used to give up on a page after three quick tries and return it empty, so one page refused
or timed out midway ended the list there: the weekly runs of 8 and 15 Oct 2026 came back
with a gallery collapsed and harvest_guard.py refused them, and the daily stock check
skipped Allee (behind Cloudflare) day after day as "fewer than 70% still for sale".

Now a page is tried five times, waiting longer each time (or as long as the server's
Retry-After says), and a page that still cannot be read stops the script before it
writes anything: the gallery keeps last week's records (fetch_galleries.py), and the
daily stock check counts it "not read today".
"""
import json, sys, time, urllib.request

WAITS = (10, 30, 60, 120)

def page(url, ua, ctx, timeout=60):
    for k in range(len(WAITS) + 1):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=timeout, context=ctx) as f:
                return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:
            if k == len(WAITS): sys.exit(f"ERR {url}: {repr(e)[:80]} -- not read, so nothing written")
            ra = (getattr(e, "headers", None) or {}).get("Retry-After", "")
            time.sleep(min(int(ra), 300) if ra.isdigit() else WAITS[k])
