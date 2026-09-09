import re, json, os, sys, time, urllib.request, urllib.parse, http.cookiejar
from concurrent.futures import ThreadPoolExecutor

BASE = "https://www.muis.ee"
UA = "EstonianArtRegister/1.0 (one-off research compile; contact via claude.ai)"
MAXPAGES = int(os.environ.get("MAXPAGES", "3"))

def opener():
    cj = http.cookiejar.CookieJar()
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    o.addheaders = [("User-Agent", UA), ("Accept-Language", "et,en")]
    return o

def get(o, url, tries=3):
    for i in range(tries):
        try:
            with o.open(url, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == tries - 1: return ""
            time.sleep(1.5 * (i + 1))
    return ""

def post(o, url, data, tries=3):
    body = urllib.parse.urlencode(data).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(url, body, {"X-Requested-With": "XMLHttpRequest",
                                                     "Content-Type": "application/x-www-form-urlencoded"})
            with o.open(req, timeout=90) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == tries - 1: return ""
            time.sleep(1.5 * (i + 1))
    return ""

def formdata(html, form_id):
    i = html.find('id="%s"' % form_id)
    seg = html[max(0, i - 3000): i + 3000] if i >= 0 else html
    m = re.search(r'name="t:formdata"[^>]*value="([^"]+)"', seg)
    if not m: m = re.search(r'value="([^"]+)"[^>]*name="t:formdata"', seg)
    return m.group(1) if m else None

ROW = re.compile(
  r'<a href="/museaalview/(\d+)"><h3>\s*(.*?)<br/>\s*(.*?)\s*</h3>\s*(.*?)<br/>\s*(.*?)<br/>\s*<i>(.*?)</i>',
  re.S)

def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', s).replace('&nbsp;', ' ').replace('&amp;', '&').strip()

def rows(html):
    out = []
    for m in ROW.finditer(html):
        mid, author, title, num, essence, coll = [clean(x) for x in m.groups()]
        out.append({"id": mid, "author": author, "title": title,
                    "num": num, "essence": essence, "coll": coll})
    return out

def harvest(name):
    o = opener()
    # 1. seed session on the search page
    h = get(o, BASE + "/otsivaade/lihtotsing")
    fd = formdata(h, "globalSearchFrom")
    if not fd: return name, 0, []
    post(o, BASE + "/index.layout.globalsearchfrom",
         {"t:formdata": fd, "globalSearchInput": name.split(",")[0], "submit_0": "Otsi"})
    # 2. detailed person search
    h = get(o, BASE + "/search")
    fd2 = formdata(h, "searchForm")
    if not fd2: return name, 0, []
    r = post(o, BASE + "/search.searchform",
             {"t:formdata": fd2, "searchName": "", "searchDescription": "",
              "searchPaev1": "", "searchKuu1": "", "searchAasta1": "",
              "searchPaev2": "", "searchKuu2": "", "searchAasta2": "",
              "textfield": "", "searchPerson": name, "submitSearch": "Otsi"})
    total = 0
    m = re.search(r'Kokku:\s*(\d+)', r)
    if m: total = int(m.group(1))
    get(o, BASE + "/search.pagination:pageitemcountevent/100")
    acc, seen = [], set()
    for p in range(MAXPAGES):
        if p: get(o, BASE + "/search.pagination:page/%d" % p)
        h = get(o, BASE + "/search")
        rs = rows(h)
        if not rs: break
        new = 0
        for x in rs:
            if x["id"] in seen: continue
            seen.add(x["id"]); acc.append(x); new += 1
        if new == 0 or len(rs) < 100: break
        time.sleep(0.3)
    return name, total, acc

names = [l.strip() for l in open("artists.txt", encoding="utf-8") if l.strip()]
res = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for name, total, acc in ex.map(harvest, names):
        res[name] = {"total": total, "rows": acc}
        print("%-28s total=%-6d fetched=%d" % (name, total, len(acc)), flush=True)
json.dump(res, open("harvest.json", "w", encoding="utf-8"), ensure_ascii=False)
print("ARTISTS WITH HITS:", sum(1 for v in res.values() if v["rows"]))
print("ROWS:", sum(len(v["rows"]) for v in res.values()))
