# -*- coding: utf-8 -*-
import re, json, os, gzip, time, subprocess, urllib.request, urllib.parse, http.cookiejar
from concurrent.futures import ThreadPoolExecutor
UA = "EstonianArtCatalogue/1.0 (one-off research compile; contact via claude.ai)"
class Redir308(urllib.request.HTTPRedirectHandler):
    # urllib does not follow 308 Permanent Redirect; ekkm.ee uses it
    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_307(req, fp, code, msg, headers)

def opener():
    cj = http.cookiejar.CookieJar()
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), Redir308())
    o.addheaders = [("User-Agent", UA), ("Accept-Language", "en,et")]
    return o
_t = {}
def op():
    import threading
    k = threading.get_ident()
    if k not in _t: _t[k] = opener()
    return _t[k]
def curl(url):
    # ekkm.ee answers 308 Permanent Redirect, which urllib will not follow
    try:
        r = subprocess.run(["curl","-sL","-m","40","-A",UA,url],
                           capture_output=True, timeout=60)
        return r.stdout.decode("utf-8","replace")
    except Exception:
        return ""

def page(url, key, use_curl=False):
    p = "cca_cache/%s.html.gz" % re.sub(r'[^A-Za-z0-9_.-]', '_', key)
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    for i in range(3):
        try:
            if use_curl:
                h = curl(url)
                if not h: raise RuntimeError("empty")
            else:
                with op().open(url, timeout=45) as r:
                    h = r.read().decode("utf-8", "replace")
            with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
            return h
        except Exception:
            if i == 2: return ""
            time.sleep(1.5 * (i + 1))
    return ""
def lines(h):
    t = re.sub(r'<script.*?</script>', '', h, flags=re.S)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
    t = re.sub(r'<[^>]+>', '\n', t)
    t = (t.replace('&#8217;', "'").replace('&#8216;', "'").replace('&#8220;', '“')
          .replace('&#8221;', '”').replace('&#8211;', '–').replace('&#8230;', '…')
          .replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"'))
    return [x.strip() for x in t.split('\n') if x.strip()]
NAV = {"cca","Menu","Events","News","Artists database","Venice biennale","Archive","A Shade Colder",
       "About us","Publications","Statistics of Estonian art exhibitions","Open calls","Contact",
       "Facebook","Instagram","Intro","Extra","Selected projects"}
CAPTION = re.compile(r'Photo:|Photos:|Exhibition view|Installation view|Courtesy|Foto:', re.I)

# ---------- 1. artists ----------
idx = page("https://cca.ee/en/artists-database", "artists-index")
slugs = sorted({s for s in re.findall(r'href="/en/artists-database/([a-z0-9-]+)"', idx)})
def artist(slug):
    h = page("https://cca.ee/en/artists-database/" + slug, "a_" + slug)
    if not h: return None
    L = lines(h)
    raw = next((x for x in L if x not in NAV and len(x) < 90 and not x.startswith("Artists")), slug)
    name = raw.split("|")[0].replace("✝", "").strip()
    body = [x for x in L if len(x) > 150 and not CAPTION.search(x)]
    return {"slug": slug, "name": name, "bio": "\n\n".join(body[:4])[:2600] if body else None}
A = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for r in ex.map(artist, slugs):
        if r: A.append(r)
print("CCA artists:", len(A), " with bio:", sum(1 for x in A if x["bio"]), flush=True)

# ---------- 2. Venice pavilion ----------
vidx = page("https://cca.ee/en/venice-biennale", "venice-index")
vslugs = sorted({s for s in re.findall(r'href="/en/venice-biennale/([a-z0-9-]+)"', vidx)})
VIDX = {}
for ln in lines(vidx):
    m = re.match(r'^(\d{4})\s*[-–]\s*(.+)$', ln)
    if m: VIDX[int(m.group(1))] = m.group(2).split("|")[0].strip()

def venice(slug):
    h = page("https://cca.ee/en/venice-biennale/" + slug, "v_" + slug)
    if not h: return None
    L = lines(h)
    ym = re.match(r'^(\d{4})', slug)
    year = int(ym.group(1)) if ym else None
    who = VIDX.get(year, "")
    # Only trust a caption that names THIS edition's year, otherwise a caption for
    # another pavilion elsewhere on the page gets attributed to the wrong artist.
    CAP = re.compile(r'^(?P<artist>[^.]{2,60})\.\s*(?P<title>.{2,90}?)\.\s*'
                     r'The Estonian [Pp]avilion at the .{0,40}?(?P<year>\d{4})')
    title = None
    for x in L:
        m = CAP.match(x)
        if m and int(m.group("year")) == year:
            title = m.group("title").strip(' “”"')
            break
    if not title:
        m = re.search(r'exhibited\s+(.{2,70}?)\s+for the Estonian Pavilion', " ".join(L))
        if m: title = m.group(1).strip(' “”"')
    # CCA splits sentences across lines around inline links, so join rather than
    # keep only the long fragments — otherwise the text starts mid-sentence.
    ci = next((n for n, x in enumerate(L) if CAPTION.search(x)), 0)
    tail = [x for x in L[ci+1:] if x not in NAV and not CAPTION.search(x)
            and not re.match(r'^\d{4}\s*[-–]', x)]
    joined = re.sub(r'\s+', " ", " ".join(tail)).strip()
    m = re.search(r'[A-ZÕÄÖÜ]', joined)
    blurb = joined[m.start():][:1200] if m else None
    return {"slug": slug, "year": year, "who": who, "title": title, "blurb": blurb}
seen_year = {}
for sl in sorted(vslugs):
    r = venice(sl)
    if not r or not r["year"]: continue
    if r["year"] not in seen_year or (r["title"] and not seen_year[r["year"]]["title"]):
        seen_year[r["year"]] = r
for y, who in VIDX.items():                    # editions with no page of their own
    if y not in seen_year:
        seen_year[y] = {"slug": None, "year": y, "who": who, "title": None, "blurb": None}
V = [seen_year[y] for y in sorted(seen_year)]
print("Venice pavilions:", len(V), flush=True)

# ---------- 3. EKKM collection ----------
sm = page("https://admin.ekkm.ee/kollektsioon-sitemap.xml", "ekkm-sitemap", True)
urls = [u for u in re.findall(r'<loc>([^<]+)</loc>', sm) if "/en/kollektsioon/" in u and u.rstrip("/").count("/") > 4]
def ekkm(u):
    h = page(u, "e_" + u.rstrip("/").split("/")[-1], True)
    if not h: return None
    L = lines(h)
    try: i = L.index("EKKM COLLECTION")
    except ValueError: return None
    artist = L[i+1] if i+1 < len(L) else None
    ti, tm = None, None
    for j in range(i+2, min(i+7, len(L))):
        m = re.match(r'^[“"]?(.+?)[”"]?,\s*(\d{4})\s*$', L[j])
        if m: ti, tm = j, m; break
    if tm:
        title, year, medium = tm.group(1).strip('“”"'), int(tm.group(2)), (L[ti+1] if ti+1 < len(L) else None)
        nxt = ti + 2
    else:
        title, year, medium, nxt = L[i+2].strip('“”"') if i+2 < len(L) else None, None, (L[i+3] if i+3 < len(L) else None), i+4
    body = [x for x in L[nxt:] if len(x) > 120 and not CAPTION.search(x)]
    return {"url": u, "artist": artist, "title": title, "year": year,
            "medium": medium, "desc": "\n\n".join(body[:2])[:1400] if body else None}
with ThreadPoolExecutor(max_workers=4) as ex:
    E = [r for r in ex.map(ekkm, urls) if r and r["artist"]]
print("EKKM collection works:", len(E), flush=True)

json.dump({"artists": A, "venice": V, "ekkm": E}, open("cca_ekkm.json", "w", encoding="utf-8"), ensure_ascii=False)
print("saved cca_ekkm.json")
