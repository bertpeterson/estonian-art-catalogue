# -*- coding: utf-8 -*-
"""The boundary check: everything in data.json that came from someone else's website.

Museum records come from two catalogues with schemas; gallery stock, auction lots,
the coming sales and the Mägi catalogue are scraped from pages that change without
notice. merge.py makes their text plain; this checks that it is, and that what the
site will link to and embed is what the rules allow. A failure stops the build, as
validate.py does.

  text   plain: no HTML tag, no script URL, no control character, nothing a
         spreadsheet opening the CSV exports would run as a formula
  links  http(s) with a host
  images a gallery's own pictures, from the gallery's own site (or its named image
         host), and only for works on show or for sale now -- never a sold listing
         or an auction lot
  prices whole euros in a plausible range
"""
import json, re, sys, collections, html
from urllib.parse import urlparse

# real tag names, as a browser reads them, so a lot titled "<NO-23A>" and "a < b" are text and "<p>Oil" is markup
TAG = re.compile(r"</?(?:a|b|i|u|p|br|hr|em|strong|small|big|sup|sub|span|div|font|h[1-6]|ul|ol|li|dl|dt|dd|"
                 r"table|thead|tbody|tr|td|th|img|figure|figcaption|picture|source|svg|script|style|iframe|"
                 r"object|embed|link|meta|form|input|button|textarea|select|option|label|nav|section|article|"
                 r"header|footer|aside|main|blockquote|pre|code|time|mark|del|ins|wbr|noscript|template|base)\b[^<>]*>", re.I)
SCRIPTY = re.compile(r"javascript:|vbscript:|data:text/html|\bon[a-z]+\s*=|&#x?[0-9a-f]+;?", re.I)


def plain(s, cut=False):
    """Scraped text made plain, as merge.py takes it: entities decoded, tags dropped,
    spaces collapsed. cut=True (dimensions) drops everything from the first tag, since
    what follows one is never a measurement -- the Mägi catalogue's "66 x 59 cm</span>
    <span class='is-long'>Nathan Altmann oli..." carried a paragraph into dims."""
    if not isinstance(s, str): return s
    s = html.unescape(s)
    if cut:
        m = TAG.search(s)
        if m: s = s[:m.start()]
    return re.sub(r"\s+", " ", TAG.sub(" ", s)).strip()


# what a spreadsheet would run from the CSV exports: "=HYPERLINK(...)", "@SUM", "+cmd|..."
# (a title may start with "+2/" or "- untitled"; it may not call anything)
FORMULA = re.compile(r"^\s*(?:[=@]|[+-].*[|(!])")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# where a gallery keeps its pictures, when it is not its own site
IMAGE_HOSTS = {"tokkoarrak.ee": {"squarespace.com"}}
WITH_IMAGES = {"gallery", "shown", "known"}            # for sale, on show, the Mägi catalogue
NO_IMAGES = {"sold", "auction"}                         # past listings and lots: never a picture
PRICE = {"pr": (20, 500_000), "as": (0, 2_000_000), "ap": (1, 2_000_000), "p": (1, 2_000_000)}
URL_FIELDS = {"url", "u", "im"}


def site(host):
    """registrable part of a host, enough for .ee/.com/.art/.ac: cms.tutar.ee -> tutar.ee"""
    parts = (host or "").lower().removeprefix("www.").split(".")
    return ".".join(parts[-2:])


def web(u):
    p = urlparse(u or "")
    return p.scheme in ("http", "https") and bool(p.hostname) and not CONTROL.search(u) and " " not in u.strip()


def check(d):
    """{problem: [examples]} for data.json as loaded; empty when it may ship"""
    W, V, A = d["works"], d.get("vocab", {}), d["artists"]
    bad = collections.defaultdict(list)

    def text(where, field, v):
        if isinstance(v, int) and field in V and 0 <= v < len(V[field]): v = V[field][v]
        if not isinstance(v, str) or field in URL_FIELDS: return
        if TAG.search(v): bad["HTML in text"].append(f"{where} {field}: {v[:70]!r}")
        elif SCRIPTY.search(v): bad["script or entity in text"].append(f"{where} {field}: {v[:70]!r}")
        elif CONTROL.search(v): bad["control character in text"].append(f"{where} {field}: {v[:70]!r}")
        elif FORMULA.search(v): bad["spreadsheet formula in text"].append(f"{where} {field}: {v[:70]!r}")

    def price(where, field, v):
        if v is None or field not in PRICE: return
        lo, hi = PRICE[field]
        if not (isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi):
            bad["price out of range"].append(f"{where} {field}={v!r}")

    for w in W:
        kind = w.get("kind", "held")
        if kind == "held": continue
        where = f"{kind} {w.get('url') or w.get('t')}"
        for f, v in w.items():
            if isinstance(v, list):
                for x in v: text(where, f, x)
            else:
                text(where, f, v); price(where, f, v)
        if not web(w.get("url")): bad["link not http(s)"].append(f"{where}: {w.get('url')!r}")
        im = w.get("im")
        if not im: continue
        if kind in NO_IMAGES or kind not in WITH_IMAGES:
            bad["picture on a work that may not show one"].append(f"{where}: {im}"); continue
        src, _, u = im.partition(":")
        if src != "g" or not web(u):
            bad["picture not an http(s) gallery image"].append(f"{where}: {im}"); continue
        own, img = site(urlparse(w["url"]).hostname), site(urlparse(u).hostname)
        if img != own and img not in IMAGE_HOSTS.get(own, ()):
            bad["picture from another site than the work's page"].append(f"{where}: {u}")

    for u in d.get("upcoming", []):
        where = f"upcoming {u.get('u')}"
        for f, v in u.items():
            if f == "pr": continue          # the lot's earlier sales, already checked as auction works
            text(where, f, v); price(where, f, v)
        if not web(u.get("u")): bad["link not http(s)"].append(f"{where}: {u.get('u')!r}")

    for a in A:
        text(f"artist {a.get('n')!r}", "n", a.get("n"))
    return bad


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    bad = check(json.load(open(path, encoding="utf-8")))
    if not bad:
        print("boundary: scraped text plain, links http(s), pictures from the galleries' own sites, prices sane")
        sys.exit(0)
    for k, v in bad.items():
        print(f"BOUNDARY FAIL: {len(v)} {k}")
        for x in v[:5]: print("   ", x)
    sys.exit(1)
