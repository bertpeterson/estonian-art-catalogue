# -*- coding: utf-8 -*-
"""What the gallery and auction scrapers share: the text of a piece of HTML, and a page read
through the day's cache.

Each script carried its own copy of both. The copies of `cached` had drifted apart in the one
way that matters: a page that could not be read came back empty, and the script went on as if
the page held nothing. For a listing that is a gallery with a page of works missing; for a
gallery read a page a work (Artisoon, Tokko & Arrak, Artrovert) it is that work left out --
and a work left out of a harvest becomes a past listing, "no longer for sale", until the next
weekly run. harvest_guard.py only refuses a gallery that lost over 40%.

So, as store_api.py does for the WooCommerce galleries: a page is tried four times, waiting
longer each time, and one that still cannot be read stops the script before it writes
anything -- the gallery keeps last week's records (fetch_galleries.py), the daily stock check
counts it "not read today". A page the server says is not there (404, 410) is the one answer
taken as empty: a work withdrawn between the listing and its own page, a listing's page past
its last.
"""
import gzip, html, os, re, ssl, sys, time, urllib.error, urllib.request

UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
CACHE = "gcache"
WAITS = (3, 10, 30)
_ctx = ssl.create_default_context()   # certificate and host checked: a forged answer must not become a listing

def U(s):
    """The text of a piece of HTML: tags out, entities read, white space single"""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def cached(url, key, lang="", timeout=60, pause=0, day=86400):
    """The page at url, from gcache/<key>.html.gz when that is under a day old (stock changes
    month to month, so a cached page older than that is read again); "" for a 404 or 410"""
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, key + ".html.gz")
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > day: os.remove(p)
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    head = {"User-Agent": UA, **({"Accept-Language": lang} if lang else {})}
    for k in range(len(WAITS) + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=head), timeout=timeout, context=_ctx) as f:
                h = f.read().decode("utf-8", "replace")
            break
        except Exception as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 410):
                print("  not there:", url, e.code, flush=True); return ""
            if k == len(WAITS): sys.exit(f"ERR {url}: {repr(e)[:80]} -- not read, so nothing written")
            time.sleep(WAITS[k])
    with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    if pause: time.sleep(pause)
    return h
