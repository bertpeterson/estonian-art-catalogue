# -*- coding: utf-8 -*-
"""EKM Digital Collection: the image path of every object -> ekm_images.json

The object pages of digikogu.ekm.ee sit behind a login and show, to anyone else, a
carousel of the collection's highlights -- which is what an earlier pass read as
the object's image, so 34,000 ids pointed at the wrong work. The search listing
is public and pairs each object with its own picture:
    <a href="/ekm/search/oid-11113/..."><img src="/static/preview/image/.../t_..jpg">
The listing needs a session cookie from /search first. Three sizes exist on the
server, tss_ (80 px), t_ (128) and t2_ (480); the path is kept without its prefix.
1,906 pages of 18, four at a time, about ten minutes.
"""
import re, json, os, time, urllib.request, http.cookiejar, threading
from concurrent.futures import ThreadPoolExecutor

BASE = "https://digikogu.ekm.ee"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
_t = {}
def op():
    k = threading.get_ident()
    if k not in _t:
        cj = http.cookiejar.CookieJar()
        o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); o.addheaders = [("User-Agent", UA), ("Accept-Language", "et,en")]
        o.open(f"{BASE}/search?searchtype=simple&searchtext=", timeout=60).read()      # the session
        _t[k] = o
    return _t[k]
def get(url):
    for i in range(3):
        try:
            with op().open(url, timeout=60) as r: return r.read().decode("utf-8", "replace")
        except Exception:
            if i == 2: return ""
            time.sleep(2 * (i + 1))

ITEM = re.compile(r'oid-(\d+)/[^"]*"\s*>\s*<img src="/static/preview/image/([^"]+?)"')
def page(p):
    h = get(f"{BASE}/search?searchtype=simple&searchtext=" if p == 1 else f"{BASE}/ekm/search/?_page={p}&_count_all={TOTAL}&searchtype=simple&searchtext=")
    i = h.find('id="imageList"')
    out = {}
    for oid, path in ITEM.findall(h[i:]) if i >= 0 else []:
        path = re.sub(r"/(?:tss_|t_|t2_|t0_)", "/", path, count=1)      # the size prefix goes; the page adds the one it wants
        out.setdefault(oid, path)
    return out

first = get(f"{BASE}/search?searchtype=simple&searchtext=")
TOTAL = int(re.search(r"_count_all=(\d+)", first).group(1)); PAGES = (TOTAL + 17) // 18
print(f"EKM: {TOTAL:,} objects, {PAGES:,} listing pages", flush=True)
imgs, done = {}, 0
with ThreadPoolExecutor(4) as ex:
    for out in ex.map(page, range(1, PAGES + 1)):
        imgs.update(out); done += 1
        if done % 200 == 0: print(f"  {done}/{PAGES} pages, {len(imgs):,} images", flush=True)
json.dump(imgs, open("ekm_images.json", "w", encoding="utf-8"))
print(f"\nEKM IMAGES: {len(imgs):,} objects with an image path")
