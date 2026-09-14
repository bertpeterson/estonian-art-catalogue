# -*- coding: utf-8 -*-
"""Vernissage kunstigalerii -> appends to gallery_records.json.

Uses WooCommerce's public Store API rather than scraping: the product grid is
JS-rendered, but /wp-json/wc/store/v1/products is a documented read-only endpoint
meant for machine access, and returns clean JSON. Prices are present in the payload
and are deliberately not read.

Product names are period-separated and pack several fields into one string:
  "Liisi Örd. Valgus. Rabajärv. 2026. Õli. Lõuend. 60 × 50 cm. MÜÜDUD"
Artist first, a bare four-digit segment is the year, the segment carrying "cm" is the
measurement, and what sits between them is title and medium. A record whose artist or
title cannot be identified is skipped rather than guessed at.
"""
import re, json, os, time, urllib.request, ssl
UA="EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
API="https://vernissage.ee/wp-json/wc/store/v1/products"
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def api(page, per=100):
    for attempt in range(3):
        try:
            r=urllib.request.Request(f"{API}?per_page={per}&page={page}",
                                     headers={"User-Agent":UA,"Accept":"application/json"})
            with urllib.request.urlopen(r,timeout=45,context=ctx) as f:
                return json.loads(f.read().decode("utf-8","replace"))
        except Exception as e:
            if attempt==2: print("ERR page",page,repr(e)[:60],flush=True); return []
            time.sleep(3*(attempt+1))

from vern_parse import parse, DROP

recs, page, seen, skipped = [], 1, set(), 0
while True:
    batch=api(page)
    if not batch: break
    for p in batch:
        # Vernissage is an auction house as well as a shop, and the product list
        # carries every lot from every past auction, hammer price in the name.
        # Those are not for sale: a lot that sold in 2023 is in someone's home.
        # The API says which is which -- is_purchasable is false for every auction
        # lot, past or unsold -- so only the shop stock is taken.
        if not p.get("is_purchasable"): skipped+=1; continue
        # ...and a shop item marked sold in its own name is not stock either
        if re.search(r'\b(müüdud|sold|reserveeritud|reserved)\b', p.get("name") or "", re.I): skipped+=1; continue
        # p also carries prices; they are not read, and the name must not carry one
        # either: "Alghind: 1800 € Haamrihind: 1800 €" is a price in disguise.
        name=re.sub(r'\b(alghind|haamrihind|hind|price|starting price|hammer price)\s*:?\s*[\d\s.,]*\s*(€|eur)?', ' ', p.get("name") or "", flags=re.I)
        got=parse(name)
        if not got: continue
        artist,title,year,tech,dims = got
        gid="vern-"+str(p.get("id"))
        if gid in seen: continue
        seen.add(gid)
        recs.append({"gid":gid,"artist":artist,"title":title,"year":year,"tech":tech,
                     "dims":dims,"gallery":"Vernissage","city":"Tallinn",
                     "url":p.get("permalink") or "https://vernissage.ee"})
    if page%5==0: print(f"  page {page}  kept {len(recs)}",flush=True)
    page+=1; time.sleep(1.0)
    if page>40: break

prev=json.load(open("gallery_records.json",encoding="utf-8"))
keep=[r for r in prev if not r["gid"].startswith("vern-")]
json.dump(keep+recs,open("gallery_records.json","w",encoding="utf-8"),ensure_ascii=False)
print(f"\nVERNISSAGE WORKS: {len(recs)}   artists: {len({r['artist'] for r in recs})}   auction lots skipped: {skipped}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:5]: print(f"   {r['artist'][:20]:20} {r['title'][:30]:30} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
