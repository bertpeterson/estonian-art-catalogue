# -*- coding: utf-8 -*-
"""Record and replay what the gallery scrapers fetch, so each runs offline in a test.

The scrapers (data/haus.py, kogo.py, ...) are scripts that fetch at the top level and
write their records into the folder they run in. Here each runs as it does in
fetch_galleries.py -- its own script, in a folder of its own -- with urllib's urlopen
answered from saved responses: tests/fixtures/scrapers/<adapter>/. The test compares
the files the script writes with expected.json there.

    python3 tests/replay.py record haus kogo      # fetch afresh: a handful of pages each, then expected.json
    python3 tests/replay.py expect haus           # expected.json again from the saved pages (after a parser change)
    python3 tests/replay.py run haus              # replay and print the script's output

What each adapter records is a handful of pages: RULES lists, per adapter, which
addresses are fetched and how many of each kind (the first matching rule with room
left takes a URL). Every other address answers 404, when recording and in replay
alike, so a listing's later pages and the works beyond the first few are simply not
there. TRIM cuts the JSON APIs' pages to their first products; SOURCES makes one saved page
out of several real ones, where the first page alone would not exercise the parser.

Files an adapter reads beside gallery_records.json (NOBA's artist pages, the cats'
photo checks) are snapshots in the fixture's inputs/. gallery_records.json starts as
one record of another gallery, which each script must leave standing.
"""
import gzip, io, json, os, re, runpy, shutil, socket, subprocess, sys, tempfile, threading, time
import urllib.error, urllib.request
from email.message import Message

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
FIX = os.path.join(HERE, "fixtures", "scrapers")
OTHER = [{"gid": "other-1", "artist": "Kristjan Raud", "title": "Kalevipoeg", "year": "1935", "tech": "", "dims": "",
          "gallery": "Another gallery", "city": "Tallinn", "url": "https://example.org/1"}]

# adapter -> [(regex on the URL, how many such URLs to keep)]
RULES = {
    "haus":        [(r"p=1$", 1), (r"p=\d+$", 1)],
    "kogo":        [(r"/art-store/$", 1), (r"/works/$", 1)],
    "temnikova":   [(r"c=exhibitions&", 1), (r"c=exhibition&", 2)],
    "tutar":       [(r"/kunstnikud$", 1), (r"/kunstnikud/", 3)],
    "artrovert":   [(r"/en/teosed/$", 1), (r"/en/toode/", 4)],
    "ruki":        [(r"/teosed/maal$", 1), (r"/teosed/graafika$", 1)],
    "allee":       [(r"page=1$", 1)],
    "eks":         [(r"/Teosed_702$", 1)],
    "vernissage":  [(r"page=1$", 1)],
    "artner":      [(r"page=1$", 1)],
    "artman":      [(r"page=1$", 1)],
    "tokkoarrak":  [(r"/kunsti-muuk$", 1), (r"/kunsti-muuk/p/", 4)],
    "artandtonic": [(r"page=1$", 1)],
    "kipskassid":  [(r"/vota-kass$", 1), (r"/kassikesed$", 1), (r"/collab-kassid$", 1), (r"/api/", 2)],
    "noba":        [(r"page=[12]$", 2), (r"noba\.ac/\w\w/(kunst|artwork)/", 3)],
    "noba_artists":  [(r"/kunstnik/", 3), (r"noba\.ac/\w\w/(toode|product|kunst|artwork)/", 2)],
    "noba_artworks": [(r"/(kunstnik|artist)/", 6), (r"noba\.ac/\w\w/(toode|product|kunst|artwork)/", 2)],
    "konradmagi":  [(r"/maalid/$", 1), (r"/eskiisid/$", 1), (r"/kadunud/$", 1)],
}
TRIM = {"allee": 20, "vernissage": 30, "artner": 25, "artman": 25, "artandtonic": 25, "kipskassid": 12, "noba": 20}
# where a page's products are taken from instead, when recording: Allee's first page
# of products is all auction lots, its stock comes later -- the saved page holds both
SOURCES = {"allee": lambda u: [u + "&type=simple", u]}
# the files each adapter writes that the test compares
OUTPUTS = {"konradmagi": ["konradmagi_records.json"], "noba_artists": ["noba_artists.json"],
           "noba_artworks": ["noba_artworks.json"], "noba": ["gallery_records.json", "noba_raw.json"]}


def key(url, data):
    return url + ("" if data is None else " <- " + data.decode("utf-8", "replace"))


class Response(io.BytesIO):
    """What urlopen hands back: the body, the final address, a status."""
    def __init__(self, body, url, status=200):
        super().__init__(body)
        self.url, self.status, self.code = url, status, status
        self.headers = self.msg = Message()
    def geturl(self): return self.url
    def getcode(self): return self.status
    def info(self): return self.headers


def child(mode, fix, script):
    """Runs in the scraper's own folder: patches urlopen, then runs the script."""
    index_p = os.path.join(fix, "responses.json")
    saved = {e["key"]: e for e in json.load(open(index_p, encoding="utf-8"))} if mode == "replay" else {}
    name = os.path.basename(script)[:-3]
    rules = [[re.compile(r), n] for r, n in RULES[name]]
    real, lock, log = urllib.request.urlopen, threading.Lock(), []
    fetched = [False]          # the last call went to the site: only then is a pause owed it

    def answer(e, url):
        if e["status"] == 0: raise urllib.error.URLError(e.get("reason", "recorded failure"))
        body = gzip.decompress(open(os.path.join(fix, e["file"]), "rb").read()) if e.get("file") else b""
        if e["status"] != 200: raise urllib.error.HTTPError(url, e["status"], "recorded", Message(), io.BytesIO(body))
        return Response(body, e.get("final_url") or url)

    def missing(url):
        raise urllib.error.HTTPError(url, 404, "not in the fixtures", Message(), io.BytesIO(b""))

    def urlopen(req, data=None, timeout=None, **kw):
        url = req.full_url if isinstance(req, urllib.request.Request) else req
        data = data if data is not None else getattr(req, "data", None)
        k = key(url, data)
        if mode == "replay":
            return answer(saved[k], url) if k in saved else missing(url)
        with lock:
            seen = next((e for e in log if e["key"] == k), None)
            if seen is None:
                rule = next((r for r in rules if r[0].search(url)), None)
                if rule is None or rule[1] == 0: fetched[0] = False; return missing(url)
                rule[1] -= 1
                seen = {"key": k, "url": url}; log.append(seen)
            elif "status" in seen:
                return answer(seen, url)
        fetched[0] = True
        parts = []
        for u in SOURCES[name](url) if name in SOURCES else [url]:
            try:
                with real(urllib.request.Request(u, headers=dict(req.header_items())) if u != url else req,
                          data, timeout or 60, **kw) as f:
                    body, status, final = f.read(), 200, f.geturl() if u == url else url
            except urllib.error.HTTPError as err:
                body, status, final = err.read() or b"", err.code, url
            except Exception as err:
                body, status, final = b"", 0, url
                seen["reason"] = repr(err)[:120]
            if status == 200 and name in TRIM:
                try:
                    j = json.loads(body.decode("utf-8"))
                    if isinstance(j, list): j = j[:TRIM[name]]
                    elif isinstance(j, dict): j = {a: v[:TRIM[name]] if isinstance(v, list) else v for a, v in j.items()}
                    body = json.dumps(j, ensure_ascii=False).encode("utf-8")
                except ValueError: pass
            parts.append(body)
            if status != 200: break
        if status == 200 and len(parts) > 1:        # one page made of several sources' products
            body = json.dumps(sum((json.loads(b.decode("utf-8")) for b in parts), []), ensure_ascii=False).encode("utf-8")
        with lock:
            seen.update(status=status, final_url=final if final != url else None)
            if body:
                seen["file"] = "%02d.gz" % (log.index(seen) + 1)
                with open(os.path.join(fix, seen["file"]), "wb") as f: f.write(gzip.compress(body, mtime=0))
            json.dump(log, open(index_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return answer(seen, url)

    urllib.request.urlopen = urlopen
    if mode == "replay":
        time.sleep = lambda s: None
        def offline(*a, **k): raise OSError("replay: no network")
        socket.socket.connect = offline
        socket.create_connection = offline
    else:
        sleep = time.sleep
        time.sleep = lambda s: sleep(min(s, 1.5)) if fetched[0] else None
    sys.path.insert(0, DATA)
    sys.argv = [script]
    runpy.run_path(script, run_name="__main__")


def run(name, mode="replay"):
    """Runs data/<name>.py in a folder of its own; returns ({file: content}, its output)."""
    fix = os.path.join(FIX, name)
    d = tempfile.mkdtemp(prefix="replay-%s-" % name)
    try:
        inputs = os.path.join(fix, "inputs")
        if os.path.isdir(inputs):
            for f in os.listdir(inputs): shutil.copy(os.path.join(inputs, f), d)
        if not os.path.exists(os.path.join(d, "gallery_records.json")):
            json.dump(OTHER, open(os.path.join(d, "gallery_records.json"), "w", encoding="utf-8"), ensure_ascii=False)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "child", mode, fix,
                            os.path.abspath(os.path.join(DATA, name + ".py"))],
                           cwd=d, capture_output=True, text=True, env=env, timeout=900)
        out = p.stdout + p.stderr
        if p.returncode: raise RuntimeError("%s.py exited %d:\n%s" % (name, p.returncode, out[-3000:]))
        got = {f: json.load(open(os.path.join(d, f), encoding="utf-8")) for f in OUTPUTS.get(name, ["gallery_records.json"])}
        return got, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def expected(name):
    return json.load(open(os.path.join(FIX, name, "expected.json"), encoding="utf-8"))


def write_expected(name):
    got, out = run(name)
    json.dump(got, open(os.path.join(FIX, name, "expected.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return got, out


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(*sys.argv[2:5]); sys.exit(0)
    cmd, names = sys.argv[1], sys.argv[2:] or sorted(RULES)
    for n in names:
        fix = os.path.join(FIX, n)
        if cmd == "record":
            for f in os.listdir(fix) if os.path.isdir(fix) else []:
                if f.endswith(".gz") or f == "responses.json": os.remove(os.path.join(fix, f))
            os.makedirs(fix, exist_ok=True)
            run(n, "record")
        if cmd in ("record", "expect"):
            got, out = write_expected(n)
        else:
            got, out = run(n)
        print("=== %s\n%s" % (n, out.rstrip()))
        print("--- %s: %s" % (n, ", ".join("%s %d" % (f, len(v)) for f, v in got.items())))
