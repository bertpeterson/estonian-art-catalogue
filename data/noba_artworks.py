# -*- coding: utf-8 -*-
"""NOBA's artwork pages, read from each artist's page -> noba_artworks.json

The Store API's permalink is the bare WooCommerce product page (/toode/): no price,
no add-to-cart, no link to the artist. NOBA's real page for a work is /kunst/<slug>/
(Estonian) or /artwork/<slug>/ (English) -- one slug for both languages, made from
the English title, so it cannot be derived from an Estonian listing. The art-sale
listing was tried first and repeats itself after 200 pages; an artist's own page
lists every work of theirs once, in both site languages, with title, medium, size
and year -- enough to match each product to its artwork page within the artist.

Cached by artist: a later run fetches only artists it has not seen.
"""
import json, re, ssl, time, urllib.request, os, html, unicodedata
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
OUT = "noba_artworks.json"

def get(u):
    for attempt in range(3):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f: return f.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == 2: return ""
            time.sleep(3 * (attempt + 1))
        except Exception:
            if attempt == 2: return ""
            time.sleep(3 * (attempt + 1))
    return ""

def slugify(n):
    s = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s))

CARD = re.compile(r'class="artwork"\s+data-key="(\d+)".*?href="https://noba\.ac/(?:et|en)/(?:kunst|artwork)/([^"/]+)/"(.*?)(?=class="artwork"\s+data-key=|<div class="pagination|</footer)', re.S)
def parse(h):
    out = []
    for aid, slug, body in CARD.findall(h):
        t = re.search(r'<div class="title"[^>]*>(.*?)</div>', body, re.S)
        ty = re.search(r'<div class="type">(.*?)</div>', body, re.S)
        title = html.unescape(re.sub(r"<[^>]+>|&nbsp;", " ", t.group(1) if t else "")).strip()
        title = re.sub(r",\s*(?:19|20)\d\d\s*$", "", title).strip()      # "Emased IV, 2021" -> the year is a field
        typ = html.unescape(re.sub(r"<[^>]+>", "", ty.group(1) if ty else ""))
        dims = re.search(r"(\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?(?:\s*x\s*\d+(?:[.,]\d+)?)?)\s*cm", typ)
        year = re.search(r"\b((?:19|20)\d\d)\b", typ)
        out.append({"id": aid, "slug": slug, "title": title,
                    "dims": re.sub(r"\s+", " ", dims.group(1)).strip() if dims else "", "year": year.group(1) if year else ""})
    return out

recs = [g for g in json.load(open("gallery_records.json", encoding="utf-8")) if g["gid"].startswith("noba-")]
names = sorted({g["artist"] for g in recs})
url_of = {g["artist"]: g["url"] for g in recs}
have = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = [n for n in names if n not in have]
print(f"NOBA artists: {len(names)}, cached {len(have)}, to fetch {len(todo)}", flush=True)

def artist_slug(n):
    s = slugify(n)
    if parse(get(f"https://noba.ac/et/kunstnik/{s}/")): return s
    lh = get(url_of[n].replace("/en/", "/et/"))
    m = re.search(r'href="https://noba\.ac/et/kunstnik/([^"/]+)/"', lh or "")
    return m.group(1) if m else None

for i, n in enumerate(todo, 1):
    s = artist_slug(n)
    works = {}
    if s:
        for lang, base in (("et", "https://noba.ac/et/kunstnik/%s/"), ("en", "https://noba.ac/en/artist/%s/")):
            for c in parse(get(base % s)):
                w = works.setdefault(c["slug"], {"id": c["id"], "dims": c["dims"], "year": c["year"], "title": {}})
                w["title"][lang] = c["title"]
            time.sleep(0.6)
    have[n] = {"slug": s, "works": works}
    if i % 50 == 0:
        json.dump(have, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  {i}/{len(todo)}  artworks so far {sum(len(v['works']) for v in have.values())}", flush=True)
json.dump(have, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(f"\nartists resolved: {sum(1 for v in have.values() if v['slug'])} of {len(have)}; artwork pages: {sum(len(v['works']) for v in have.values())}")
