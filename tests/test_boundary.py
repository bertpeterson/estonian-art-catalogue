# -*- coding: utf-8 -*-
"""Fixture tests for the ingestion boundary: plain() as merge.py applies it, the boundary
check over data.json, and asking prices. The fixtures are strings the galleries' and
auction houses' pages really carried, plus the hostile ones a page could carry tomorrow.

    python3 -m unittest discover tests
"""
import copy, os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from boundary import plain, check          # noqa: E402
from asking_price import asking, euros, listed     # noqa: E402


class Plain(unittest.TestCase):
    def test_seen_in_the_wild(self):
        self.assertEqual(plain("<p>Õli, lõuend"), "Õli, lõuend")                                  # Tütar, 39 works
        self.assertEqual(plain("Publication &#8220;Reimagining Those Old Slopes&#8221;"),
                         "Publication “Reimagining Those Old Slopes”")                            # Temnikova
        self.assertEqual(plain("B&amp;M"), "B&M")
        self.assertEqual(plain("Puulõige. Plm 36. 0×27. 0 cm , lm 67&#215;48,2 cm"),
                         "Puulõige. Plm 36. 0×27. 0 cm , lm 67×48,2 cm")
        self.assertEqual(plain("66 x 59 cm</span><span class='is-long'>Nathan Altmann oli Venemaa juut.", cut=True),
                         "66 x 59 cm")                                                            # the Mägi catalogue

    def test_invisible_characters(self):
        # a name that reads like another but would be a second artist at the same address
        self.assertEqual(plain("Krist\u00adja\u00adn Raud"), "Kristjan Raud")                   # soft hyphens
        self.assertEqual(plain("Kris\u200btjan R\u2060aud\ufeff"), "Kristjan Raud")              # zero-width, word joiner, BOM
        self.assertEqual(plain("Navigeerin/Navigati\u200bng"), "Navigeerin/Navigating")          # a NOBA title
        self.assertEqual(plain("Pärnu Õie"), "Pärnu Õie")

    def test_brackets_that_are_not_markup(self):
        self.assertEqual(plain("<NO-23A>"), "<NO-23A>")                                           # an auction lot's title
        self.assertEqual(plain("a < b > c"), "a < b > c")

    def test_hostile(self):
        self.assertEqual(plain('Maastik<script>alert(1)</script>'), "Maastik alert(1)")
        self.assertEqual(plain('<img src=x onerror=alert(1)>Õli'), "Õli")
        self.assertEqual(plain("&lt;script&gt;x&lt;/script&gt;"), "x")                             # entity-encoded tags decode, then go
        self.assertEqual(plain("  two\n\tlines  "), "two lines")

    def test_not_text(self):
        self.assertIsNone(plain(None))
        self.assertEqual(plain(1200), 1200)


def data(**work):
    """a data.json with one museum work and one gallery work, the gallery work overridden"""
    g = {"a": 0, "t": "Repeating paths II", "y": 2026, "yl": "2026", "tc": 0, "tce": 0, "dm": "165 × 160 × 40 cm",
         "mu": 0, "kind": "gallery", "url": "https://www.kogogallery.ee/en/works/repeating-paths-ii/",
         "im": "g:https://www.kogogallery.ee/wp-content/uploads/2026/09/skulptuur-4.jpg", "pr": 4500}
    g.update(work)
    return {"artists": [{"n": "Example Artist", "c": 2}],
            "vocab": {"tc": ["Oil, canvas"], "tce": ["Õli, lõuend"], "mu": ["Kogo galerii"]},
            "works": [{"a": 0, "t": "Held", "kind": "held", "im": "e:whatever"}, {k: v for k, v in g.items() if v is not None}],
            "upcoming": [{"a": 0, "t": "Paar", "yl": "2011", "h": "Eesti Kunsti Oksjonid", "s": "EKO Sügisoksjon 2026",
                          "d": "2026-10-31", "p": 1500, "u": "https://eestikunstioksjonid.ee/o/paar/", "pr": None}]}


class Check(unittest.TestCase):
    def fails(self, d):
        return set(check(d))

    def test_clean_passes(self):
        self.assertEqual(self.fails(data()), set())

    def test_text(self):
        self.assertIn("HTML in text", self.fails(data(t="Maastik<script>alert(1)</script>")))
        self.assertIn("HTML in text", self.fails(data(dm="66 x 59 cm</span><span class='is-long'>")))
        self.assertIn("script or entity in text", self.fails(data(t="&#60;b&#62;")))
        self.assertIn("control character in text", self.fails(data(t="Maastik\x00")))
        self.assertIn("spreadsheet formula in text", self.fails(data(t='=HYPERLINK("http://x","click")')))
        self.assertIn("spreadsheet formula in text", self.fails(data(t="+cmd|' /C calc'!A0")))
        self.assertEqual(self.fails(data(t="+2/ sphere of influence")), set())                     # a real sold listing's title
        self.assertEqual(self.fails(data(t="<NO-23A>")), set())

    def test_vocab_text_is_checked_too(self):
        d = data(); d["vocab"]["tce"][0] = "<p>Õli, lõuend"
        self.assertIn("HTML in text", self.fails(d))

    def test_links(self):
        self.assertIn("link not http(s)", self.fails(data(url="javascript:alert(1)")))
        self.assertIn("link not http(s)", self.fails(data(url="//kogogallery.ee/x")))
        d = data(); d["upcoming"][0]["u"] = "data:text/html,<b>"
        self.assertIn("link not http(s)", self.fails(d))

    def test_gallery_site_pinned(self):
        # a forged reply: the link and its picture both on another host, which the picture rule alone lets through
        self.assertIn("link off the gallery's own site",
                      self.fails(data(url="https://evil.example/checkout/", im="g:https://evil.example/x.jpg")))
        self.assertEqual(self.fails(data(url="https://kogogallery.ee/en/works/x/")), set())        # with or without www
        d = data(); d["vocab"]["mu"][0] = "Uus galerii"
        self.assertIn("gallery with no registered site (GALLERY_SITES)", self.fails(d))
        self.assertEqual(self.fails(data(kind="auction", im=None, url="https://www.postimees.ee/lot")), set())  # lots: not pinned

    def test_pictures(self):
        self.assertIn("picture from another site than the work's page",
                      self.fails(data(im="g:https://images.example.com/x.jpg")))
        self.assertIn("picture not an http(s) gallery image", self.fails(data(im="g:javascript:alert(1)")))
        self.assertIn("picture on a work that may not show one", self.fails(data(kind="sold")))   # a past listing, living artist
        d = data(kind="sold"); d["artists"][0]["l"] = ["1882", "1925"]                             # ...and a public-domain one
        self.assertEqual(self.fails(d), set())
        d["artists"][0]["l"] = ["1882", ""]                                                       # born too late to assume dead long enough
        self.assertIn("picture on a work that may not show one", self.fails(d))
        self.assertIn("picture on a work that may not show one", self.fails(data(kind="auction")))
        # a gallery's own image host
        for mu, url, im in (("Tütar galerii", "https://www.tutar.ee/teosed/x", "g:https://cms.tutar.ee/x.jpg"),
                            ("Tokko & Arrak", "https://tokkoarrak.ee/x", "g:https://static1.squarespace.com/x.jpg")):
            d = data(url=url, im=im); d["vocab"]["mu"][0] = mu
            self.assertEqual(self.fails(d), set())

    def test_prices(self):
        self.assertIn("price out of range", self.fails(data(pr=0)))
        self.assertIn("price out of range", self.fails(data(pr=5_000_000)))
        self.assertIn("price out of range", self.fails(data(pr="1200")))
        self.assertIn("price out of range", self.fails(data(pr=True)))
        self.assertEqual(self.fails(data(pr=None)), set())

    def test_held_works_are_not_the_boundary(self):
        d = data(); d["works"][0]["t"] = "<p>museum text"       # the museums' records have their own checks
        self.assertEqual(self.fails(d), set())


class Prices(unittest.TestCase):
    def test_euros(self):
        self.assertEqual(euros("Hind 1 200 €"), {"price": 1200})
        self.assertEqual(euros("€1200"), {"price": 1200})
        self.assertEqual(euros("850 EUR"), {"price": 850})
        self.assertEqual(euros("1&nbsp;450,00&euro;"), {"price": 1450})
        for gone in ("Müüdud", "Sold – 1200 €", "Broneeritud", "Hind kokkuleppel", "Price on request", "", None):
            self.assertEqual(euros(gone), {}, gone)

    def test_store_api(self):
        p = {"is_in_stock": True, "prices": {"price": "120000", "currency_code": "EUR", "currency_minor_unit": 2}}
        self.assertEqual(asking(p), {"price": 1200})
        self.assertEqual(asking(p, sold=True), {})
        self.assertEqual(asking({**p, "is_in_stock": False}), {})
        self.assertEqual(asking({"prices": {**p["prices"], "currency_code": "USD"}}), {})
        self.assertEqual(asking({"prices": {**p["prices"], "price_range": {"min": 1}}}), {})
        self.assertEqual(asking({"prices": {"price": "abc", "currency_code": "EUR"}}), {})

    def test_listed(self):
        p = {"prices": {"price": "1200000", "currency_code": "EUR", "currency_minor_unit": 2}}
        self.assertEqual(listed({**p, "is_in_stock": False}), {"listed": 12000})
        self.assertEqual(listed({**p, "is_in_stock": True, "categories": [{"name": "Müüdud"}]}), {"listed": 12000})
        self.assertEqual(listed({**p, "is_in_stock": True}), {})            # stock has an asking price, not a listed one
        self.assertEqual(listed({"is_in_stock": False, "prices": {"price": "0", "currency_code": "EUR"}}), {})


if __name__ == "__main__":
    unittest.main()
