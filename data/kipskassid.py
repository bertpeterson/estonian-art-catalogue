# -*- coding: utf-8 -*-
"""Lihtsad Kipskassid (Taavi Eelmaa) -> appends to gallery_records.json. Metadata only.

Taavi Eelmaa's art-brut plaster cats -- cast in building plaster, painted with water-based
acrylic, varnished, each one named -- from the artist's own site, lihtsadkipskassid.ee
(Next.js; no robots.txt). Three things are read, the addresses its own pages read:

- /vota-kass, the full-size cats on sale, from their photographs' names:
  "<title>--<edition>--lihtne--<price | müüdud>.jpg". A price is read only as "for sale";
  "müüdud" is the artist's word that it sold: kept, flagged.
- /kassikesed, the kittens, in sets of seven ("7 LIHTSAT TOITU", each with a piece of music
  and a scenographer, Liisi Eelmaa): "grupp-NNN/<title>--<price>--<saadaval | müüdud>.png".
  The set is the kitten's collection.
- /api/media/gallery, the archive the page /kassigalerii shows: one photograph a file,
  "<title> (n).jpg", kept in the site's storage bucket (R2), from which its page shows it. A cat the artist shows, not one he offers: kept as shown, with its
  photograph, as a gallery's portfolio page is. Several photographs of one cat are one
  work (case aside: "White Noise" is "WHITE NOISE"); a photograph of two cats is none;
  the festival and the artist's own portraits are not cats. A cat also in the shop is
  the shop's.

The photographs weigh 0.4-3.5 MB; the site's own resizer (/_next/image, 640 px), which its
pages use, gives 3-20 KB, and that is what the wall shows. Prices are never kept. Pages
cached a day.
"""
import json, re, os, gzip, ssl, time, html, urllib.request, urllib.parse
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
BASE = "https://www.lihtsadkipskassid.ee"
R2 = "https://pub-f1ff4e6b13aa42b9a2f600dbf2dd13a5.r2.dev"      # the archive's photographs, as /kassigalerii builds their address
GALLERY, ARTIST, TECH, CAT = "Lihtsad Kipskassid", "Taavi Eelmaa", "kips, akrüülvärv, lakk", "Sculpture"
NOT_CATS = {"arvamusfestival", "taavi"}          # festival photographs; the artist himself
ctx = ssl.create_default_context()
os.makedirs("gcache", exist_ok=True)

def get(path, key):
    p = f"gcache/{key}.gz"
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > 86400: os.remove(p)
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    body = ""
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE + path, headers={"User-Agent": UA}), timeout=60, context=ctx) as f:
                body = f.read().decode("utf-8", "replace"); break
        except Exception as e:
            if k == 2: print("ERR", path, repr(e)[:60], flush=True)
            time.sleep(3 * (k + 1))
    if body:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(body)
    time.sleep(1.5)
    return body

fold = lambda s: re.sub(r"[^a-zõäöüšž0-9]", "", s.lower())
slug = lambda s: re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower().translate(str.maketrans("õäöüšž", "oaousz")))).strip("-")
# the site's own 640 px copy; the path as the site serves it (percent-encoded once, whether
# the page wrote it encoded or not), then encoded again as the resizer's parameter
small = lambda src: f"{BASE}/_next/image?url={urllib.parse.quote(urllib.parse.quote(urllib.parse.unquote(src), safe='/'), safe='')}&w=640&q=75"
# ...and for a photograph in the storage bucket: the name alone, as the gallery page writes it
small_r2 = lambda file: f"{BASE}/_next/image?url={urllib.parse.quote(R2 + '/' + urllib.parse.quote(re.sub(r'^.*?/kassigalerii/|^/+', '', file), safe=''), safe='')}&w=640&q=75"
rec = lambda gid, title, url, **kw: {"gid": gid, "artist": ARTIST, "title": title, "year": None, "tech": TECH, "cat": CAT,
                                     "dims": "", "gallery": GALLERY, "city": "", "url": url, **kw}
recs = []

# the full-size cats on sale
h = get("/vota-kass", "kipskassid_vota")
for src in dict.fromkeys(re.findall(r'(/kipskassid/[^"\\]+?\.(?:jpe?g|png|webp))', h)):
    parts = urllib.parse.unquote(src).rsplit("/", 1)[1].rsplit(".", 1)[0].split("--")
    if len(parts) != 4: continue
    title, edition, _, state = [html.unescape(x).strip() for x in parts]
    sold = state.lower() == "müüdud"
    if not sold and not state.isdigit(): continue                      # "tulekul": a cat still to come
    recs.append(rec(f"kipskass-{slug(title)}", title, f"{BASE}/vota-kass",
                    **({"sold": True} if sold else {"img": small(src)})))

# the kittens, set by set
h = get("/kassikesed", "kipskassid_kassikesed")
sets = {}
for src in dict.fromkeys(re.findall(r'(/kassikesed/grupp-\d+/[^"\\]+?--taust\.(?:jpe?g|png))', h)):
    g, name = urllib.parse.unquote(src).split("/")[2:4]
    t = name.split("--")[0].strip()
    sets[g] = t[:1] + t[1:].lower()                                     # "7 LIHTSAT TOITU" -> "7 lihtsat toitu"
for src in dict.fromkeys(re.findall(r'(/kassikesed/grupp-\d+/[^"\\]+?\.png)', h)):
    g, name = urllib.parse.unquote(src).split("/")[2:4]
    parts = name.rsplit(".", 1)[0].split("--")
    if len(parts) != 3: continue
    title, _, state = [html.unescape(x).strip() for x in parts]
    sold = state.lower() == "müüdud"
    if not sold and state.lower() != "saadaval": continue
    recs.append(rec(f"kipskass-kassike-{g}-{slug(title)}", title, f"{BASE}/kassikesed", series=sets.get(g),
                    **({"sold": True} if sold else {"img": small(src)})))

# the archive: cats shown
shop = {fold(r["title"]) for r in recs}
try: items = json.loads(get("/api/media/gallery", "kipskassid_gallery")).get("items", [])
except ValueError: items = []
names = {}
for it in items:
    title = re.sub(r"\s*\(\d+\)\s*$", "", it["name"].rsplit(".", 1)[0]).strip()
    k = fold(title)
    if not k or k in NOT_CATS or "&" in title: continue
    if k not in names: names[k] = {"title": title, "file": it["file"]}
    elif title != title.upper() and names[k]["title"] == names[k]["title"].upper():
        names[k]["title"] = title                                       # the spelling with small letters, where there are two
# "Puhkus Nizzas ja Ühtsuse Vaikus": two cats that each have their own photographs
for k in [k for k, v in names.items() if " ja " in v["title"] and all(fold(p) in names for p in v["title"].split(" ja "))]:
    del names[k]
for k, v in names.items():
    if k in shop: continue
    recs.append(rec(f"kipskass-arhiiv-{slug(v['title'])}", v["title"], f"{BASE}/kassigalerii", shown=True,
                    img=small_r2(v["file"])))

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("kipskass-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
on_sale = [r for r in recs if not r.get("sold") and not r.get("shown")]
print(f"LIHTSAD KIPSKASSID: {len(recs)} cats -- on sale {len(on_sale)}, sold {sum(1 for r in recs if r.get('sold'))}, "
      f"shown in the archive {sum(1 for r in recs if r.get('shown'))}; kitten sets {len(sets)}")
for r in on_sale[:4]: print(f"   {r['title'][:34]:34} {r.get('series') or '':22} {r['img'][:70]}")
