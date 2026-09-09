import json, re, urllib.request, ssl
from concurrent.futures import ThreadPoolExecutor
UA = "EstonianArtCatalogue/1.0 (venue link check; contact via claude.ai)"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
def check(v):
    req = urllib.request.Request(v["url"], headers={"User-Agent": UA, "Accept-Language":"et,en"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            code, final = r.status, r.geturl()
            html = r.read(60000).decode("utf-8", "replace")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S|re.I)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:90] if m else ""
        return {**v, "http": code, "final": final, "title": title}
    except Exception as e:
        return {**v, "http": None, "final": None, "title": "", "err": repr(e)[:70]}
V = json.load(open("venues_seed.json", encoding="utf-8"))
with ThreadPoolExecutor(max_workers=6) as ex:
    out = list(ex.map(check, V))
json.dump(out, open("venues_checked.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
ok = [v for v in out if v["http"] == 200]
print("reachable: %d/%d\n" % (len(ok), len(out)))
for v in out:
    flag = "ok " if v["http"]==200 else "!! "
    print(f"{flag}{v['n'][:34]:34} {str(v['http']):4} {v.get('title','')[:52]}")
    if v.get("err"): print(f"      {v['err']}")
