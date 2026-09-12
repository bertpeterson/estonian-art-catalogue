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
import json, re, ssl, time, urllib.request, os, unicodedata
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
MED = {"maal": "p", "painting": "p", "graafika": "g", "print": "g", "graphics": "g", "skulptuur": "s",
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
