# -*- coding: utf-8 -*-
"""Which country each NOBA artist is based in -> noba_artists.json

NOBA is the seller of record for every listing, so "Estonian seller" is not a
distinction the site makes. Its artist pages carry the one that matters here:
"Kunstniku asukohariik: Eesti" -- the artist's country of location -- plus a short
biography the artist or NOBA wrote. One page per artist, fetched once and cached;
merge.py lets a NOBA record through for an artist the catalogue does not hold only
when that country is Estonia.

The slug is guessed from the name (folded, hyphenated), which is how NOBA forms it;
a miss is looked up from one of the artist's listing pages instead.
"""
import json, re, ssl, time, urllib.request, os, unicodedata, sys
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
OUT = "noba_artists.json"

def get(u):
    for attempt in range(3):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "et"})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f:
                return f.geturl(), f.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404: return None, ""
            if attempt == 2: return None, ""
            time.sleep(3 * (attempt + 1))
        except Exception:
            if attempt == 2: return None, ""
            time.sleep(3 * (attempt + 1))
    return None, ""

def slugify(n):
    s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s))

def text(h):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t); t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)

def parse(h):
    t = text(h)
    m = re.search(r"Kunstniku asukohariik:\s*\n?\s*([^\n]+)", t)
    if not m: return None
    country = m.group(1).strip()
    # the biography follows the country line; it ends where the work listing begins
    after = t[m.end():].strip()
    bio = after.split("\n")[0].strip() if after else ""
    if len(bio) < 40 or re.match(r"^(Graafika|Maal|Skulptuur|Foto|Joonistus|Video)\b", bio): bio = ""
    return {"country": country, "bio": bio[:1200]}

recs = [g for g in json.load(open("gallery_records.json", encoding="utf-8")) if g["gid"].startswith("noba-")]
names = sorted({g["artist"] for g in recs})
have = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = [n for n in names if n not in have]
print(f"NOBA artists: {len(names)}, cached {len(have)}, to fetch {len(todo)}", flush=True)
url_of = {g["artist"]: g["url"] for g in recs}
miss = 0
for i, n in enumerate(todo, 1):
    got = None
    _, h = get(f"https://noba.ac/et/kunstnik/{slugify(n)}/")
    if h: got = parse(h)
    if not got:
        # the artist page is linked from every listing; take the slug from there
        _, lh = get(url_of[n].replace("/en/", "/et/"))
        m = re.search(r'href="https://noba\.ac/et/kunstnik/([^"/]+)/"', lh or "")
        if m:
            _, h = get(f"https://noba.ac/et/kunstnik/{m.group(1)}/")
            if h: got = parse(h)
    if not got: miss += 1
    have[n] = got or {"country": None, "bio": ""}
    if i % 50 == 0:
        json.dump(have, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  {i}/{len(todo)}  misses {miss}", flush=True)
    time.sleep(0.8)
json.dump(have, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
import collections
print("\ncountries:", collections.Counter(v["country"] for v in have.values()).most_common(12))
print("with a biography:", sum(1 for v in have.values() if v["bio"]))
