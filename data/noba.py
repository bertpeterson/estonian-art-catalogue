# -*- coding: utf-8 -*-
"""NOBA (noba.ac) -> gallery_records.json, for artists the catalogue already knows.

NOBA is a Nordic and Baltic art marketplace run from Tallinn; galleries and artists
list works on it directly. It runs WooCommerce, and /wp-json/wc/store/v1/products is
the documented read-only endpoint the site's own pages use -- the same one that
served Vernissage. robots.txt permits it. Every product name is one line in one
shape, "Title, Artist, Year, Medium WxHcm", which is parsed here.

Metadata only: artist, title, year, technique, dimensions, and a link to the listing.
Prices are not read. The seller is not in the API, so the holder is NOBA itself.

Records carry only_known=True: merge.py takes them for artists already in the
catalogue -- museum-held or in the seven galleries -- and otherwise only when
noba_artists.json says the artist is based in Estonia. Latvian, Lithuanian,
Finnish and Swedish artists on NOBA stay out.
"""
import json, re, ssl, time, urllib.request, os, unicodedata, html
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
API = "https://noba.ac/wp-json/wc/store/v1/products"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def api(page):
    for attempt in range(3):
        try:
            r = urllib.request.Request(f"{API}?per_page=100&page={page}", headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=60, context=ctx) as f:
                return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:
            if attempt == 2: print("ERR page", page, repr(e)[:60], flush=True); return []
            time.sleep(3 * (attempt + 1))

# "Punased jooned 1, Kaia Rähn, 2025, Maal 120x90cm"
NAME = re.compile(r"^(?P<t>.+?),\s*(?P<a>[^,]+?),\s*(?P<y>\d{4}[^,]*)?,?\s*(?P<m>[^,]*?)\s*"
                  r"(?P<d>\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?\s*cm)?\s*$")
PRICE = re.compile(r"(hind|price)\s*:?\s*[\d\s.,]*\s*(€|eur)?", re.I)
fold = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
key = lambda a, t, d: (fold(a), re.sub(r"[^a-z0-9]", "", fold(t)), re.sub(r"[^0-9x]", "", (d or "").lower().replace("×", "x")))

recs, seen, page, unparsed, dup = [], set(), 1, 0, 0
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        if not p.get("is_purchasable"): continue
        m = NAME.match(PRICE.sub(" ", p.get("name") or "").strip())
        if not m: unparsed += 1; continue
        artist, title = m.group("a").strip(), m.group("t").strip()
        if not re.match(r"^[^\d]{3,60}$", artist): unparsed += 1; continue
        year = (re.match(r"(\d{4})", m.group("y") or "") or [None, None])[1]
        tech = (m.group("m") or "").strip(" ,")
        dims = re.sub(r"\s*[x×]\s*", " x ", (m.group("d") or "")).replace("cm", " cm").strip()
        dims = re.sub(r"\s+", " ", dims)
        k = key(artist, title, dims)
        if k in seen: dup += 1; continue        # the same listing under both languages
        seen.add(k)
        recs.append({"gid": "noba-" + str(p["id"]), "artist": artist, "title": title, "year": year,
                     "tech": tech, "dims": dims, "gallery": "NOBA", "city": "Tallinn",
                     "url": p.get("permalink") or "https://noba.ac", "only_known": True})
    if page % 20 == 0: print(f"  page {page}  kept {len(recs)}", flush=True)
    page += 1; time.sleep(0.8)
    if page > 300: break

# Sellers list many works twice, once per site language, with the title translated:
# "Naine kohvitassiga" and "Woman with a cup of coffee" are one canvas. NOBA exposes no
# link between the two, so they are paired on everything else -- artist, year, size,
# medium -- and only where that leaves exactly one Estonian and one English listing.
# The Estonian listing is kept, as the catalogue keeps titles the way the holder
# wrote them in Estonian. Larger groups (Red lines 1 and 2, both languages) are left
# alone: nothing in the data says which is which.
MED = {"maal": "p", "painting": "p", "graafika": "g", "print": "g", "graphics": "g", "printmaking": "g", "skulptuur": "s",
       "sculpture": "s", "foto": "f", "photo": "f", "photography": "f", "joonistus": "d", "drawing": "d",
       "akvarell": "w", "watercolor": "w", "watercolour": "w", "video": "v", "segatehnika": "m", "mixed media": "m"}
lang = lambda r: (re.search(r"noba\.ac/(\w\w)/", r["url"]) or [None, "?"])[1]
groups = {}
for r in recs:
    t = (r["tech"] or "").lower().strip()
    groups.setdefault((fold(r["artist"]), r["year"], r["dims"], MED.get(t, t[:4])), []).append(r)
folded, out = 0, []
for g in groups.values():
    et = [r for r in g if lang(r) == "et"]; en = [r for r in g if lang(r) == "en"]
    if len(et) == 1 and len(en) == 1: out.append(et[0]); folded += 1
    else: out.extend(g)
recs = out
print(f"  translated pairs folded: {folded}")

# The permalink the API gives is the bare product page: no price, no add-to-cart, no
# artist. NOBA's real page for a work is /kunst/<slug>/ or /artwork/<slug>/, listed on
# the artist's page (noba_artworks.py). A product is matched to it within its artist
# on title in either language, then size, then size and year; one candidate or none.
# About a third of the products have no artwork page on the artist's page. Those are
# not for sale: NOBA takes a sold work's page private (it answers 401, where a live
# one answers 200 and a never-made one 404) and leaves the shop product standing --
# "1 in stock", no image, no way to reach it from the site. Videvik by Malle Leis was
# one. Only products matched to a listed artwork page are kept; a sample of the rest
# was 24 sold to 1 live listing the matching had missed.
AW = json.load(open("noba_artworks.json", encoding="utf-8")) if os.path.exists("noba_artworks.json") else {}
ntitle = lambda t: re.sub(r"[^a-z0-9]", "", fold(html.unescape(t)))
ndims  = lambda d: re.sub(r"[^0-9x]", "", (d or "").lower().replace("×", "x").replace(",", "."))
relinked = 0
for r in recs:
    a = AW.get(r["artist"])
    if not a or not a.get("slug"): continue
    ws = a["works"]
    c = [s for s, w in ws.items() if ntitle(r["title"]) in {ntitle(t) for t in w["title"].values()}]
    if len(c) > 1: c = [s for s in c if ndims(ws[s]["dims"]) == ndims(r["dims"])]
    if not c: c = [s for s, w in ws.items() if ndims(w["dims"]) == ndims(r["dims"]) and w["year"] == (r["year"] or "") and w["dims"]]
    if len(c) == 1:
        r["url"] = f"https://noba.ac/{lang(r)}/{'kunst' if lang(r) == 'et' else 'artwork'}/{c[0]}/"; relinked += 1
print(f"  linked to the artwork page: {relinked}")
# Two products that resolve to one artwork page are one work -- the translated pair
# the folding above could not settle because a sibling (Spruces I and II, same size,
# same year) made the group too big to pair. The Estonian listing is kept.
by_page = {}
for r in recs:
    m = re.search(r"noba\.ac/\w\w/(?:kunst|artwork)/([^/]+)/", r["url"])
    if m: by_page.setdefault((fold(r["artist"]), m.group(1)), []).append(r)
same_page = set()
for g in by_page.values():
    if len(g) > 1:
        keep_r = next((r for r in g if lang(r) == "et"), g[0])
        same_page.update(r["gid"] for r in g if r is not keep_r)
recs = [r for r in recs if r["gid"] not in same_page]
print(f"  same artwork page, folded: {len(same_page)}")
# The full harvest, before the drop, is what the artist-page scripts read: a new
# artist's works are unmatched until their page has been fetched.
json.dump(recs, open("noba_raw.json", "w", encoding="utf-8"), ensure_ascii=False)
# NOBA never says sold; it takes the artwork page private and leaves the shop
# product standing. That is a work no longer listed -- kept as a past listing, but
# not called sold, since the house does not.
# Its bare product page shows no picture, no artist, and "1 in stock" for a work
# that is not to be had: the record links to the artist's NOBA page instead, which
# shows what of theirs is available, or to nothing where NOBA has no page for the name.
n_gone = 0
for r in recs:
    if "/toode/" in r["url"]:
        r["past"] = True; n_gone += 1
        slug = (AW.get(r["artist"]) or {}).get("slug")
        r["url"] = f"https://noba.ac/{lang(r)}/{'kunstnik' if lang(r) == 'et' else 'artist'}/{slug}/" if slug else None
        r["urlkind"] = "artist" if slug else None
print(f"  no longer listed (no artwork page on the artist's page), kept as past listings: {n_gone}")

prev = json.load(open("gallery_records.json", encoding="utf-8")) if os.path.exists("gallery_records.json") else []
keep = [r for r in prev if not r["gid"].startswith("noba-")]
# A work a gallery lists on its own site and again on NOBA is one work; the gallery's
# own listing wins, since that is where the buyer ends up.
have = {key(r["artist"], r["title"], r.get("dims")) for r in keep}
recs = [r for r in recs if key(r["artist"], r["title"], r.get("dims")) not in have]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"\nNOBA WORKS: {len(recs)}   artists: {len({r['artist'] for r in recs})}   unparsed: {unparsed}   same-listing dups: {dup}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}")
for r in recs[:5]: print(f"   {r['artist'][:22]:22} {r['title'][:30]:30} {r['year'] or '—':6} {r['dims']:16} {r['tech'][:20]}")
