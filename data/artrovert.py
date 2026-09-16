# -*- coding: utf-8 -*-
"""Artrovert (Tallinn) -> appends to gallery_records.json. WooCommerce; metadata only.
robots.txt permits product pages (only wp-admin, wc-logs and add-to-cart are disallowed)."""
import re, json, os, gzip, time, urllib.request, ssl
UA="EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
BASE="https://www.artrovert.ee"
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
os.makedirs("gcache",exist_ok=True)
def get(u,key):
    p=f"gcache/{key}.html.gz"
    # stock changes month to month: a cached page older than a day is fetched again
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > 86400: os.remove(p)
    if os.path.exists(p):
        with gzip.open(p,"rt",encoding="utf-8") as f: return f.read()
    try:
        r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"en"})
        with urllib.request.urlopen(r,timeout=35,context=ctx) as f: h=f.read().decode("utf-8","replace")
    except Exception as e:
        print("ERR",u,repr(e)[:50],flush=True); h=""
    with gzip.open(p,"wt",encoding="utf-8") as f: f.write(h)
    time.sleep(1.2); return h
def txt(s):
    s=re.sub(r'<[^>]+>',' ',s)
    for a,b in (("&amp;","&"),("&#8217;","’"),("&#8220;","“"),("&#8221;","”"),("&times;","×"),("&nbsp;"," ")): s=s.replace(a,b)
    s=re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), s)   # numeric entities, incl. &#215; (×)
    return re.sub(r'\s+',' ',s).strip()

slugs=set()
for page in range(1,6):
    u=f"{BASE}/en/teosed/" if page==1 else f"{BASE}/en/teosed/page/{page}/"
    h=get(u,f"artro_list{page}")
    found=set(re.findall(r'/en/toode/([a-z0-9-]+)/', h))
    if not found: break
    slugs |= found
print("products:", len(slugs), flush=True)

# "Alar Tuul “A Day in Paradise” (2026) 140 x 120 cm, oil on canvas"
LINE=re.compile(r'^(.{2,45}?)\s*[“"”]([^“"”]{1,90})[”"“]\s*(?:\((\d{4})\))?\s*,?\s*'
                r'([\d.,]+\s*[x×]\s*[\d.,]+\s*(?:cm|mm))?\s*,?\s*(.*)$', re.I)
recs=[]
for sl in sorted(slugs):
    h=get(f"{BASE}/en/toode/{sl}/", f"artro_{sl}")
    if not h: continue
    m=re.search(r'<div[^>]*class="[^"]*woocommerce-product-details__short-description[^"]*"[^>]*>(.*?)</div>', h, re.S)
    body=txt(m.group(1)) if m else ""
    if not body:
        m2=re.search(r'id="tab-description".*?<p>(.*?)</p>', h, re.S)
        body=txt(m2.group(1)) if m2 else ""
    dm=re.search(r'Dimensions\s*([\d.,]+\s*[×x]\s*[\d.,]+)\s*(cm|mm)', txt(h), re.I)
    lm=LINE.match(body)
    if not lm: continue
    artist,title,year,dims,tech = lm.groups()
    dims = (f"{dm.group(1)} {dm.group(2)}" if dm else (dims or "")).strip()
    # the description often repeats the measurements inside the technique clause
    tech = re.sub(r'[\d.,]+\s*[x×]\s*[\d.,]+(?:\s*[x×]\s*[\d.,]+)?\s*(?:cm|mm)?', '', tech or '')
    tech = re.sub(r'\s{2,}', ' ', tech).strip(" ,.;")
    # the product's own page says whether it is still for sale: "outofstock" is the
    # gallery's Sold badge. A sold work is kept, flagged, as a past listing.
    main = re.search(r'<(?:article|div)[^>]*class="[^"]*\bast-article-single\b[^"]*"', h)   # the work itself, not the related-works row
    is_sold = bool(main and "outofstock" in main.group(0))
    og = re.search(r'property="og:image" content="([^"]+)"', h)
    recs.append({"gid":"artro-"+sl,"artist":artist.strip(" ,"),"title":title.strip(),
                 "year":year,"tech":tech,"dims":dims,
                 "gallery":"Artrovert","city":"Tallinn","url":f"{BASE}/en/toode/{sl}/", **({"sold": True} if is_sold else {}),
                 **({"img": re.sub(r"-\d+x\d+(?=\.\w+$)", "", og.group(1))} if og else {})})
prev=json.load(open("gallery_records.json",encoding="utf-8"))
keep=[r for r in prev if not r["gid"].startswith("artro-")]
json.dump(keep+recs,open("gallery_records.json","w",encoding="utf-8"),ensure_ascii=False)
print(f"ARTROVERT WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
