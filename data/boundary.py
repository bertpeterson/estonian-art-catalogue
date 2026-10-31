# -*- coding: utf-8 -*-
"""The boundary check: everything in data.json that came from someone else's website.

Museum records come from two catalogues with schemas; gallery stock, auction lots,
the coming sales and the Mägi catalogue are scraped from pages that change without
notice. merge.py makes their text plain; this checks that it is, and that what the
site will link to and embed is what the rules allow. A failure stops the build, as
validate.py does.

  text   plain: no HTML tag, no script URL, no control character, nothing a
         spreadsheet opening the CSV exports would run as a formula
  links  http(s) with a host; a gallery's listing on that gallery's own site (GALLERY_SITES);
         a coming lot, and a past lot with a picture, on the auction house's own (HOUSE_SITES)
  images a gallery's own pictures, from the gallery's own site (or its named image
         host), and only for works on show or for sale now, or a past listing of a
         public-domain work -- never one by a later artist; a lot's from the house's
         own site, for every coming lot and for past lots of public-domain artists
  prices whole euros in a plausible range
"""
import json, re, sys, collections, html, datetime
from urllib.parse import urlparse

# real tag names, as a browser reads them, so a lot titled "<NO-23A>" and "a < b" are text and "<p>Oil" is markup
TAG = re.compile(r"</?(?:a|b|i|u|p|br|hr|em|strong|small|big|sup|sub|span|div|font|h[1-6]|ul|ol|li|dl|dt|dd|"
                 r"table|thead|tbody|tr|td|th|img|figure|figcaption|picture|source|svg|script|style|iframe|"
                 r"object|embed|link|meta|form|input|button|textarea|select|option|label|nav|section|article|"
                 r"header|footer|aside|main|blockquote|pre|code|time|mark|del|ins|wbr|noscript|template|base)\b[^<>]*>", re.I)
# characters that show as nothing (soft hyphen, zero-width, joiners, bidi marks, BOM): in a name they made
# "Krist\u00adjan Raud" a second artist who reads, and is addressed, like the first
INVISIBLE = re.compile("[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180f\u200b-\u200f\u202a-\u202e\u2060-\u206f"
                       "\u3164\ufe00-\ufe0f\ufeff\uffa0\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0000-\U000e0fff]")
SCRIPTY = re.compile(r"javascript:|vbscript:|data:text/html|\bon[a-z]+\s*=|&#x?[0-9a-f]+;?", re.I)


def plain(s, cut=False):
    """Scraped text made plain, as merge.py takes it: entities decoded, tags dropped,
    spaces collapsed. cut=True (dimensions) drops everything from the first tag, since
    what follows one is never a measurement -- the Mägi catalogue's "66 x 59 cm</span>
    <span class='is-long'>Nathan Altmann oli..." carried a paragraph into dims."""
    if not isinstance(s, str): return s
    s = INVISIBLE.sub("", html.unescape(s))
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
# each gallery's own site, kept here by hand: a listing for sale, on show or sold links there and nowhere else, so a
# page answered by someone else (a forged reply, a hijacked site) cannot send the site's visitors to another address.
# A new gallery needs its line here before its works ship; the Mägi catalogue's works ("known") all link to it.
GALLERY_SITES = {
    "Allee galerii": "alleegalerii.ee", "Art & Tonic": "artandtonic.art", "Artman": "artman.ee", "Artner": "artner.ee",
    "Artrovert": "artrovert.ee", "E-Kunstisalong": "e-kunstisalong.ee", "Haus Galerii": "haus.ee",
    "Kogo galerii": "kogogallery.ee", "NOBA": "noba.ac", "Ruki galerii": "rukigalerii.ee", "Tokko & Arrak": "tokkoarrak.ee",
    "Tütar galerii": "tutar.ee", "Vernissage": "vernissage.ee", "Temnikova & Kasela": "temnikova.ee",
    "Veneetsia biennaal, Eesti paviljon": "cca.ee",
}
KIND_SITES = {"known": "konradmagi.ee"}
# each auction house's own site, kept here by hand: a coming lot, and a past lot shown with its picture, link there and
# nowhere else, and the picture comes from the same site (below), as CLAUDE.md has it: "embedded from the house's own
# server". A past lot without a picture may link to the press report of a sale (postimees.ee, err.ee). A new house
# needs its line here before its coming lots, or its past lots with pictures, ship
HOUSE_SITES = {
    "Allee galerii": "alleegalerii.ee", "E-Kunstisalong": "e-kunstisalong.ee", "Eesti Kunsti Oksjonid": "eestikunstioksjonid.ee",
    "Haus Galerii": "haus.ee", "Kunstikoda": "kunstikoda.ee", "Osta Noort Kunsti": "ostanoortkunsti.ee",
    "Vaal galerii": "vaal.ee", "Vernissage": "vernissage.ee",
}
PINNED = {"gallery", "shown", "sold", "known"}
WITH_IMAGES = {"gallery", "shown", "known"}            # for sale, on show, the Mägi catalogue
NO_IMAGES = set()
PD_ONLY = {"sold", "auction"}                           # past listings and lots: only of a public-domain work
PRICE = {"pr": (20, 500_000), "lp": (20, 500_000), "as": (0, 2_000_000), "ap": (1, 2_000_000), "p": (1, 2_000_000)}
URL_FIELDS = {"url", "u", "im"}


def site(host):
    """registrable part of a host, enough for .ee/.com/.art/.ac: cms.tutar.ee -> tutar.ee"""
    parts = (host or "").lower().removeprefix("www.").split(".")
    return ".".join(parts[-2:])


def public_domain(a, year=None):
    """the artist dead by the end of year-71, or born by year-156 with no death recorded, as merge.py has it"""
    y = year or datetime.date.today().year
    b, d = (int(m.group()) if (m := re.search(r"\d{4}", str(x or ""))) else None for x in (a.get("l") or ["", ""])[:2])
    return bool((d and d <= y - 71) or (b and not d and b <= y - 156))


# the host as a browser reads it: letters, digits, dots and dashes up to the first / ? or #. Python's urlparse takes
# "https://evil.example\@www.kogogallery.ee/" for kogogallery.ee, a browser for evil.example: a "\" or a "user@"
# before the host, or anything else there, is no gallery's address
AUTHORITY = re.compile(r"^https?://[A-Za-z0-9.-]+(?::\d+)?(?:[/?#]|$)", re.I)


def web(u):
    p = urlparse(u or "")
    # no quote or angle bracket either: a link goes into attributes, and one that needs them is not a gallery's
    return p.scheme in ("http", "https") and bool(p.hostname) and not CONTROL.search(u) and " " not in u.strip() \
        and not re.search(r"[\"'<>`]", u) and AUTHORITY.match(u) is not None


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
        elif kind in PINNED:
            mu = V["mu"][w["mu"]] if isinstance(w.get("mu"), int) and 0 <= w["mu"] < len(V.get("mu", [])) else w.get("mu")
            want = KIND_SITES.get(kind) or GALLERY_SITES.get(mu)
            if not want: bad["gallery with no registered site (GALLERY_SITES)"].append(f"{where}: {mu!r}")
            elif site(urlparse(w["url"]).hostname) != want: bad["link off the gallery's own site"].append(f"{where}: {mu!r}")
        elif kind == "auction" and w.get("im"):
            house = V["mu"][w["mu"]] if isinstance(w.get("mu"), int) and 0 <= w["mu"] < len(V.get("mu", [])) else w.get("mu")
            want = HOUSE_SITES.get(house)
            if not want: bad["auction house with no registered site (HOUSE_SITES)"].append(f"{where}: {house!r}")
            elif site(urlparse(w["url"]).hostname) != want: bad["lot off the auction house's own site"].append(f"{where}: {house!r}")
        im = w.get("im")
        if not im: continue
        if kind in NO_IMAGES or kind not in WITH_IMAGES | PD_ONLY or (kind in PD_ONLY and not public_domain(A[w["a"]])):
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
        if not web(u.get("u")): bad["link not http(s)"].append(f"{where}: {u.get('u')!r}"); continue
        want = HOUSE_SITES.get(u.get("h"))
        if not want: bad["auction house with no registered site (HOUSE_SITES)"].append(f"{where}: {u.get('h')!r}"); continue
        if site(urlparse(u["u"]).hostname) != want: bad["lot off the auction house's own site"].append(f"{where}: {u.get('h')!r}"); continue
        im = u.get("im")
        if not im: continue
        src, _, iu = im.partition(":")
        if src != "g" or not web(iu): bad["picture not an http(s) gallery image"].append(f"{where}: {im}")
        elif site(urlparse(iu).hostname) != site(urlparse(u["u"]).hostname):
            bad["picture from another site than the work's page"].append(f"{where}: {iu}")

    # the holder's own site, linked on every card of it: a web address, and a gallery's on the gallery's own site
    for k, u in (d.get("meta", {}).get("sites") or {}).items():
        where = f"site of {k!r}"
        if not web(u): bad["link not http(s)"].append(f"{where}: {u!r}")
        elif k in GALLERY_SITES and site(urlparse(u).hostname) != GALLERY_SITES[k]:
            bad["link off the gallery's own site"].append(f"{where}: {u!r}")

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
