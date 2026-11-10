# -*- coding: utf-8 -*-
"""The small pieces the scheduled runs lean on, each on a few records made up here:

  auction_keep.py     a sale this run could not read keeps its lots
  harvest_guard.py    a gallery or house that collapsed stops the run
  data_guard.py       a merge that lost records stops the run
  stock_check.py      `apply`: the works the daily check found gone become past listings
  scrape_util.py      a page not read stops the script; a page that is not there is empty
  build_alerts.py     `new`: only what the live site had not announced
  .github/publish.py  takes a data file the run may change, refuses anything else

    python3 -m unittest discover tests
"""
import gzip, io, json, os, shutil, subprocess, sys, tempfile, unittest, urllib.error, urllib.request
from email.message import Message

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, DATA)
sys.path.insert(0, ROOT)
from auction_keep import merged   # noqa: E402
import scrape_util                # noqa: E402
import build_alerts               # noqa: E402


def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False)

def load(path):
    with open(path, encoding="utf-8") as f: return json.load(f)

def run(args, cwd):
    r = subprocess.run([sys.executable, "-B"] + args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class Folder(unittest.TestCase):
    """A folder of its own, with the scripts under test copied in: they read and write beside themselves"""
    scripts = ()
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="guards-")
        for s in self.scripts: shutil.copy(os.path.join(DATA, s), self.d)
    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)
    def path(self, name): return os.path.join(self.d, name)


class AuctionKeep(unittest.TestCase):
    lot = staticmethod(lambda house, sale, aid: {"house": house, "sale": sale, "aid": aid})

    def test_a_sale_not_read_keeps_its_lots(self):
        prev = [self.lot("Vaal", "Spring 2025", "v1"), self.lot("Vaal", "Autumn 2025", "v2"), self.lot("Haus", "XL", "h1")]
        out = merged(prev, "Vaal", [self.lot("Vaal", "Autumn 2025", "v2"), self.lot("Vaal", "Autumn 2025", "v3")])
        self.assertEqual(sorted(r["aid"] for r in out), ["h1", "v1", "v2", "v3"])

    def test_a_sale_read_again_is_replaced(self):
        prev = [self.lot("Vaal", "Autumn 2025", "v2"), self.lot("Vaal", "Autumn 2025", "v9")]
        out = merged(prev, "Vaal", [self.lot("Vaal", "Autumn 2025", "v2")])
        self.assertEqual([r["aid"] for r in out], ["v2"])

    def test_a_renamed_sale_is_not_kept_twice(self):
        prev = [self.lot("Vaal", "SPRING SALE", "v1")]
        out = merged(prev, "Vaal", [self.lot("Vaal", "Spring sale", "v1")])
        self.assertEqual([(r["sale"], r["aid"]) for r in out], [("Spring sale", "v1")])

    def test_nothing_read_keeps_everything(self):
        prev = [self.lot("Vaal", "Spring 2025", "v1"), self.lot("Haus", "XL", "h1")]
        self.assertEqual(sorted(r["aid"] for r in merged(prev, "Vaal", [])), ["h1", "v1"])


class HarvestGuard(Folder):
    scripts = ("harvest_guard.py",)

    def harvest(self, galleries, houses=None):
        dump(self.path("gallery_records.json"), [{"gallery": g} for g, n in galleries.items() for _ in range(n)])
        if houses is not None:
            dump(self.path("auction_records.json"), [{"house": h} for h, n in houses.items() for _ in range(n)])
        return run(["harvest_guard.py", "after"], self.d)

    def before(self, galleries, houses=None):
        self.harvest(galleries, houses)   # writes the files; its own check has no snapshot yet
        code, out = run(["harvest_guard.py", "before"], self.d)
        self.assertEqual(code, 0, out)

    def test_selling_and_growing_pass(self):
        self.before({"Haus": 100, "Kogo": 10}, {"Vaal": 50})
        code, out = self.harvest({"Haus": 70, "Kogo": 30, "New": 5}, {"Vaal": 60})
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(self.path("harvest_before.json")))

    def test_a_gallery_gone_is_refused(self):
        self.before({"Haus": 100, "Kogo": 10})
        code, out = self.harvest({"Haus": 100})
        self.assertEqual(code, 1, out); self.assertIn("Kogo", out)

    def test_a_gallery_that_lost_half_is_refused(self):
        self.before({"Haus": 100})
        code, out = self.harvest({"Haus": 50})
        self.assertEqual(code, 1, out); self.assertIn("REFUSED", out)

    def test_a_house_that_lost_its_lots_is_refused(self):
        self.before({"Haus": 100}, {"Vaal": 400})
        code, out = self.harvest({"Haus": 100}, {"Vaal": 100})
        self.assertEqual(code, 1, out); self.assertIn("Vaal auctions", out)


class DataGuard(Folder):
    scripts = ("data_guard.py",)

    def data(self, name, works):
        """works: (artist index, kind, pictured) each"""
        dump(self.path(name), {"artists": [{"n": "A", "c": 1}, {"n": "B", "c": 1}],
                               "works": [{"a": a, **({} if kind == "held" else {"kind": kind}), **({"im": "x"} if im else {})} for a, kind, im in works]})
        return name

    def guard(self, old, new):
        return run(["data_guard.py", self.data("old.json", old), self.data("new.json", new)], self.d)

    def test_small_moves_pass(self):
        old = [(0, "held", True)] * 60 + [(1, "auction", False)] * 40
        code, out = self.guard(old, old[:-1] + [(0, "gallery", True)] * 3)
        self.assertEqual(code, 0, out)

    def test_lost_works_are_refused(self):
        old = [(0, "held", True)] * 60 + [(1, "auction", False)] * 40
        code, out = self.guard(old, old[:90])
        self.assertEqual(code, 1, out); self.assertIn("auction lots", out)

    def test_lost_pictures_are_refused(self):
        old = [(0, "held", True)] * 100
        code, out = self.guard(old, [(0, "held", True)] * 90 + [(0, "held", False)] * 10)
        self.assertEqual(code, 1, out); self.assertIn("pictured", out)

    def test_one_artist_emptied_is_refused(self):
        old = [(0, "held", True)] * 990 + [(1, "held", True)] * 10
        code, out = self.guard(old, [(0, "held", True)] * 995 + [(1, "held", True)] * 5)
        self.assertEqual(code, 1, out); self.assertIn("B", out)


class StockApply(Folder):
    scripts = ("stock_check.py",)

    def test_gone_works_become_past_listings(self):
        works = [{"k": "Ghaus1", "kind": "gallery", "im": "g:1", "pr": 900},
                 {"k": "Ghaus2", "kind": "gallery", "im": "g:2", "pr": 400},
                 {"k": "Ghaus3", "kind": "gallery", "im": "g:3", "pr": 250},
                 {"k": "M1", "im": "m:1"}]
        dump(self.path("data.json"), {"works": works, "meta": {"gallery": 3, "past": 5, "past_sold": 2}})
        dump(self.path("stock_gone.json"), {"Ghaus1": ["2026-11-09", 1], "Ghaus2": ["2026-11-10", 0], "M1": ["2026-11-10", 1]})
        code, out = run(["stock_check.py", "apply"], self.d)
        self.assertEqual(code, 0, out)
        d = load(self.path("data.json")); w = {x["k"]: x for x in d["works"]}
        self.assertEqual((w["Ghaus1"]["kind"], w["Ghaus1"]["gs"], w["Ghaus1"]["im"], w["Ghaus1"]["gl"]), ("sold", 1, None, "2026-11"))
        self.assertEqual((w["Ghaus2"]["kind"], w["Ghaus2"]["gs"]), ("sold", 0))
        self.assertNotIn("pr", w["Ghaus1"]); self.assertNotIn("pr", w["Ghaus2"])       # a sold work keeps no price
        self.assertEqual(w["Ghaus3"], works[2])                                         # still for sale: untouched
        self.assertEqual(w["M1"], works[3])                                             # a museum work is never stock
        self.assertEqual(d["meta"], {"gallery": 1, "past": 7, "past_sold": 3})

    def test_unapply_puts_the_file_back_as_it_was(self):
        dump(self.path("data.json"), {"works": [{"k": "Ghaus1", "kind": "gallery", "pr": 900}], "meta": {"gallery": 1, "past": 0, "past_sold": 0}})
        dump(self.path("stock_gone.json"), {"Ghaus1": ["2026-11-09", 1]})
        with open(self.path("data.json"), "rb") as f: before = f.read()
        self.assertEqual(run(["stock_check.py", "apply"], self.d)[0], 0)
        self.assertEqual(run(["stock_check.py", "apply"], self.d)[0], 0)      # a second build before the first one's unapply
        self.assertEqual(load(self.path("data.json"))["works"][0]["kind"], "sold")
        self.assertEqual(run(["stock_check.py", "unapply"], self.d)[0], 0)
        with open(self.path("data.json"), "rb") as f: self.assertEqual(f.read(), before)
        self.assertEqual(sorted(os.listdir(self.d)), ["data.json", "stock_check.py", "stock_gone.json"])

    def test_unapply_leaves_a_file_written_since(self):
        dump(self.path("data.json"), {"works": [{"k": "Ghaus1", "kind": "gallery"}], "meta": {"gallery": 1, "past": 0, "past_sold": 0}})
        dump(self.path("stock_gone.json"), {"Ghaus1": ["2026-11-09", 1]})
        run(["stock_check.py", "apply"], self.d)
        dump(self.path("data.json"), {"works": [], "meta": {"merged": "since"}})          # merge.py ran meanwhile
        self.assertEqual(run(["stock_check.py", "unapply"], self.d)[0], 0)
        self.assertEqual(load(self.path("data.json"))["meta"], {"merged": "since"})
        self.assertEqual(sorted(os.listdir(self.d)), ["data.json", "stock_check.py", "stock_gone.json"])

    def test_nothing_gone_writes_nothing(self):
        dump(self.path("data.json"), {"works": [{"k": "Ghaus1", "kind": "gallery"}], "meta": {"gallery": 1, "past": 0, "past_sold": 0}})
        before = os.path.getmtime(self.path("data.json"))
        code, out = run(["stock_check.py", "apply"], self.d)
        self.assertEqual((code, os.path.getmtime(self.path("data.json"))), (0, before), out)


class Cached(Folder):
    """scrape_util.cached with urlopen answered here"""
    def setUp(self):
        super().setUp()
        self.cwd, self.real, self.sleep = os.getcwd(), urllib.request.urlopen, scrape_util.time.sleep
        os.chdir(self.d)
        scrape_util.time.sleep = lambda s: None
        self.calls = []
    def tearDown(self):
        urllib.request.urlopen, scrape_util.time.sleep = self.real, self.sleep
        os.chdir(self.cwd)
        super().tearDown()

    def answers(self, *seq):
        """each answer in turn, the last one again after that: a body, an HTTP status, or an exception"""
        seq = list(seq)
        def urlopen(req, timeout=None, context=None):
            self.calls.append(req.full_url)
            a = seq.pop(0) if len(seq) > 1 else seq[0]
            if isinstance(a, int): raise urllib.error.HTTPError(req.full_url, a, "made up", Message(), io.BytesIO(b""))
            if isinstance(a, Exception): raise a
            return io.BytesIO(a.encode("utf-8"))
        urllib.request.urlopen = urlopen

    def test_read_once_then_from_the_cache(self):
        self.answers("<p>Õhtu</p>")
        self.assertEqual(scrape_util.cached("https://example.org/a", "a"), "<p>Õhtu</p>")
        self.assertEqual(scrape_util.cached("https://example.org/a", "a"), "<p>Õhtu</p>")
        self.assertEqual(len(self.calls), 1)
        with gzip.open(self.path("gcache/a.html.gz"), "rt", encoding="utf-8") as f: self.assertEqual(f.read(), "<p>Õhtu</p>")

    def test_a_page_that_is_not_there_is_empty_and_not_kept(self):
        self.answers(404)
        self.assertEqual(scrape_util.cached("https://example.org/gone", "gone"), "")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(os.path.exists(self.path("gcache/gone.html.gz")))

    def test_a_page_that_fails_once_is_tried_again(self):
        self.answers(503, OSError("timed out"), "<p>ok</p>")
        self.assertEqual(scrape_util.cached("https://example.org/b", "b"), "<p>ok</p>")
        self.assertEqual(len(self.calls), 3)

    def test_a_page_not_read_stops_the_script(self):
        self.answers(503)
        with self.assertRaises(SystemExit) as e: scrape_util.cached("https://example.org/c", "c")
        self.assertIn("not read", str(e.exception.code))
        self.assertEqual(len(self.calls), len(scrape_util.WAITS) + 1)
        self.assertFalse(os.path.exists(self.path("gcache/c.html.gz")))

    def test_text(self):
        self.assertEqual(scrape_util.U(" <b>Konrad</b>\n M&auml;gi &amp;  <i>s&otilde;brad</i> "), "Konrad Mägi & sõbrad")
        self.assertEqual(scrape_util.U(None), "")


class AlertsNew(Folder):
    def setUp(self):
        super().setUp()
        self.argv, self.for_sale = sys.argv, build_alerts.for_sale
        row = lambda i: [i, "Title " + i, 100, "s", "Haus", "", "https://example.org/" + i, ""]
        build_alerts.for_sale = lambda: {"konrad-magi": {"n": "Konrad Mägi", "w": [row("aaa"), row("bbb")]},
                                         "ado-vabbe": {"n": "Ado Vabbe", "w": [row("ccc")]}}
    def tearDown(self):
        sys.argv, build_alerts.for_sale = self.argv, self.for_sale
        super().tearDown()

    def new(self, live):
        if live is not None: dump(self.path("live.json"), live)
        sys.argv = ["build_alerts.py", "new", self.path("live.json"), self.path("new.json")]
        out, sys.stdout = sys.stdout, io.StringIO()
        try: build_alerts.main()
        finally: sys.stdout = out
        return load(self.path("new.json")) if os.path.exists(self.path("new.json")) else None

    def test_only_what_the_live_site_had_not(self):
        new = self.new({"konrad-magi": ["aaa"], "ado-vabbe": ["ccc"], "someone-else": ["zzz"]})
        self.assertEqual(list(new), ["konrad-magi"])
        self.assertEqual([r[0] for r in new["konrad-magi"]["w"]], ["bbb"])

    def test_an_id_already_announced_under_another_artist_is_not_new(self):
        self.assertIsNone(self.new({"x": ["aaa", "bbb", "ccc"]}))

    def test_no_live_file_nothing_is_new(self):
        self.assertIsNone(self.new(None))

    def test_ids(self):
        self.assertEqual(build_alerts.sid("https://example.org/1"), build_alerts.sid("https://example.org/1"))
        self.assertRegex(build_alerts.sid("https://example.org/1"), r"^[0-9a-f]{12}$")
        self.assertEqual([build_alerts.euros(v) for v in ("1 200", "950,50", None, "on request")], [1200, 950, 0, 0])


class Publish(Folder):
    """publish.py in a repository made here: data/a.json and data/mood_api.json tracked, code.py tracked"""
    def setUp(self):
        super().setUp()
        self.repo, self.src = self.path("repo"), self.path("changed")
        os.makedirs(os.path.join(self.repo, "data")); os.makedirs(os.path.join(self.src, "data"))
        for f, body in (("data/a.json", "[1]"), ("data/mood_api.json", "{}"), ("code.py", "x = 1\n")):
            with open(os.path.join(self.repo, f), "w") as fh: fh.write(body)
        git = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", *a], cwd=self.repo, capture_output=True, check=True)
        git("init", "-q"); git("add", "-A"); git("commit", "-q", "-m", "start")

    def give(self, rel, body):
        os.makedirs(os.path.dirname(os.path.join(self.src, rel)), exist_ok=True)
        with open(os.path.join(self.src, rel), "wb") as f: f.write(body if isinstance(body, bytes) else body.encode())

    def publish(self, *patterns):
        return run(["-I", os.path.join(ROOT, ".github", "publish.py"), self.src, *patterns], self.repo)

    def read(self, rel):
        with open(os.path.join(self.repo, rel)) as f: return f.read()

    def test_a_data_file_is_taken(self):
        self.give("data/a.json", "[1, 2]")
        code, out = self.publish("data/*.json")
        self.assertEqual(code, 0, out); self.assertEqual(self.read("data/a.json"), "[1, 2]")

    def test_anything_else_refuses_the_whole_run(self):
        for rel, body, why in (("code.py", "x = 2\n", "not a file this run may change"),
                               ("data/mood_api.json", '{"url": "https://evil.example"}', "not a file this run may change"),
                               ("data/new.json", "[]", "not a tracked file"),
                               ("data/sub/a.json", "[]", "not a file this run may change"),
                               ("data/a.json", "[1, 2", "not a whole JSON document")):
            with self.subTest(rel=rel, why=why):
                shutil.rmtree(self.src); os.makedirs(os.path.join(self.src, "data"))
                self.give("data/a.json", "[1, 2]") if rel != "data/a.json" else None
                self.give(rel, body)
                code, out = self.publish("data/*.json")
                self.assertEqual(code, 1, out); self.assertIn(why, out)
                self.assertEqual(self.read("data/a.json"), "[1]")           # the good file was not taken either

    def test_a_link_is_refused(self):
        os.symlink(os.path.join(self.repo, "code.py"), os.path.join(self.src, "data", "a.json"))
        code, out = self.publish("data/*.json")
        self.assertEqual(code, 1, out); self.assertIn("not a regular file", out)

    def test_no_patterns_takes_nothing(self):
        self.give("data/a.json", "[1, 2]")
        code, out = self.publish()
        self.assertNotEqual(code, 0, out); self.assertEqual(self.read("data/a.json"), "[1]")


if __name__ == "__main__":
    unittest.main()
