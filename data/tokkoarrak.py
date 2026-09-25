# -*- coding: utf-8 -*-
"""Tokko & Arrak Galerii (Tallinn) -> appends to gallery_records.json. Metadata only.

A Tallinn gallery (Sõle 14) with ~450 works on sale in September 2026 -- Jüri Arrak
above all, and Raul Meel, Arno Arrak, Malle Leis, Peeter Pere. The shop is Squarespace.
Its robots.txt closes the JSON view (?format=json) to every agent, so this reads the
pages a visitor reads: the listing (/kunsti-muuk, 200 works a page, ?offset= for the
next) for the works' addresses, then each work's page -- "Artist - Title" in its title,
then the year, the technique and "Mõõdud: 25 × 50 cm". A listing that sells two works
together ("müügil komplektina") is left out: one record cannot say which is which.
A work whose stock is gone ("soldOut") is the gallery's word that it sold: kept,
flagged. Prices are not read. Pages are cached for a day.
"""
import json, re, os, gzip, ssl, time, html, urllib.request
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
BASE = "https://tokkoarrak.ee"
ctx = ssl.create_default_context()
os.makedirs("gcache", exist_ok=True)

def get(u, key):
    p = f"gcache/{key}.html.gz"
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > 86400: os.remove(p)
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    h = ""
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60, context=ctx) as f:
                h = f.read().decode("utf-8", "replace"); break
        except Exception as e:
            if k == 2: print("ERR", u, repr(e)[:60], flush=True)
            time.sleep(3 * (k + 1))
    if h:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    time.sleep(1.2)
    return h

slugs, off = [], 0
for n in range(10):
    h = get(f"{BASE}/kunsti-muuk" + (f"?offset={off}" if off else ""), f"tokko_list{n}")
    for s in re.findall(r"/kunsti-muuk/p/([a-z0-9-]+)", h):
        if s not in slugs: slugs.append(s)
    m = re.search(r'/kunsti-muuk\?offset=(\d+)', h)
    nxt = int(m.group(1)) if m else None
    if not nxt or nxt <= off: break
    off = nxt
print("works listed:", len(slugs), flush=True)

recs = []
for s in slugs:
    h = get(f"{BASE}/kunsti-muuk/p/{s}", f"tokko_{s}")
    og = re.search(r'property="og:title" content="([^"]+)"', h)
    if not og: continue
    t = re.sub(r"\s+—\s+Tokko.*$", "", html.unescape(og.group(1))).strip()
    if " - " not in t: continue
    artist, title = [x.strip() for x in t.split(" - ", 1)]
    # the work's own text: from its title to the add-to-cart button
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    parts = [p.strip() for p in html.unescape(re.sub(r"<[^>]+>", "|", body)).split("|") if p.strip()]
    i = next((k for k, p in enumerate(parts) if p == title), None)
    # up to the cart button ("Lisa ostukorvi", or "Add To Cart" on some pages), or ten lines
    j = next((k for k, p in enumerate(parts) if i is not None and k > i and re.match(r"(Lisa ostukorvi|Add to cart|Müüdud|Tokko & Arrak Galerii)", p, re.I)), None)
    seg = parts[i + 1:(j if j else i + 11)] if i is not None else []
    text = " | ".join(seg)
    if re.search(r"komplekt", text + title, re.I): continue
    yi = next((k for k, p in enumerate(seg) if re.fullmatch(r"(?:u\.?\s*)?\d{4}(?:\s*[/–-]\s*\d{2,4})?\.?", p)), None)
    year = re.search(r"\d{4}", seg[yi]).group(0) if yi is not None else None
    tech = next((p for p in seg if p is not (seg[yi] if yi is not None else None) and not re.match(r"(mõõ|signe|autori|raam|tiraa|\d)", p, re.I) and len(p) < 60), "")
    dm = re.search(r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*cm", text)
    sold = bool(re.search(r'&quot;soldOut&quot;:true|"soldOut":true', h)) and not re.search(r'&quot;soldOut&quot;:false|"soldOut":false', h)
    img = re.search(r'property="og:image" content="([^"]+)"', h)
    recs.append({"gid": f"tokko-{s}", "artist": artist, "title": title, "year": year, "tech": tech[:80],
                 "dims": re.sub(r"\s*[x×]\s*", " x ", dm.group(1)) + " cm" if dm else "",
                 "gallery": "Tokko & Arrak", "city": "Tallinn", "url": f"{BASE}/kunsti-muuk/p/{s}",
                 **({"sold": True} if sold else {}),
                 **({"img": img.group(1)} if img else {})})

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("tokko-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"TOKKO & ARRAK WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with technique {sum(1 for r in recs if r['tech'])}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
