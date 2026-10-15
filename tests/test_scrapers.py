# -*- coding: utf-8 -*-
"""Each gallery scraper, run offline against a few saved pages of its gallery's site
(tests/replay.py, tests/fixtures/scrapers/<adapter>/): what it writes must be what it
wrote when the pages were saved. A parser change that alters the records fails here;
if the change is meant, `python3 tests/replay.py expect <adapter>` writes the new
expectation, and the diff of expected.json shows what changed.

    python3 -m unittest discover tests
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(__file__))
import replay   # noqa: E402


class Scrapers(unittest.TestCase):
    maxDiff = 4000

    def check(self, name):
        got, out = replay.run(name)
        want = replay.expected(name)
        for f in want:
            if got[f] != want[f]:
                byid = lambda rs: {r.get("gid") or r.get("url"): r for r in rs} if isinstance(rs, list) else rs
                self.assertEqual(byid(got[f]), byid(want[f]), "%s: %s differs\n%s" % (name, f, out[-1500:]))
                self.assertEqual(got[f], want[f], "%s: %s in another order" % (name, f))
        # every adapter that writes gallery_records.json leaves the other galleries' records standing
        if "gallery_records.json" in got:
            self.assertTrue(any(r["gid"] == "other-1" for r in got["gallery_records.json"]), name)
        return got


def _case(name):
    def test(self):
        got = self.check(name)
        self.assertTrue(any(len(v) > (1 if f == "gallery_records.json" else 0) for f, v in got.items()),
                        "%s: the fixtures yield no records" % name)
    test.__name__ = "test_" + name
    return test


for _n in replay.RULES:
    setattr(Scrapers, "test_" + _n, _case(_n))


if __name__ == "__main__":
    unittest.main()
