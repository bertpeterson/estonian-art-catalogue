# -*- coding: utf-8 -*-
"""Static, crawlable page per artist, plus sitemap.xml and robots.txt.

The catalogue is a single-page app addressed by URL fragment, and a fragment is
never sent to the server — so every one of its 52,000 works is invisible to search
engines. Nobody looking up "Eduard Wiiralt Põrgu" can find it.

These pages give each artist real HTML that a crawler can read, and link into the
live app for anyone who arrives. They are generated, never edited by hand.

BASE is the only thing that changes when the site moves to its own domain; GitHub
Pages 301-redirects the github.io address to a custom domain, so indexing done now
carries over.
"""
import json, os, re, html, unicodedata, datetime

BASE = "https://museaal.ee"
OUT  = "site/a"
d = json.load(open("data/data.json", encoding="utf-8"))
A, W, V = d["artists"], d["works"], d.get("vocab", {})
os.makedirs(OUT, exist_ok=True)

def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))

def val(w, f):
    v = w.get(f)
    if isinstance(v, int) and f in V: return V[f][v] if 0 <= v < len(V[f]) else None
    return v

e = lambda s: html.escape(str(s or ""), quote=True)
KIND = {"school": "trained at", "movement": "movement", "member": "member of"}
by_artist = {}
for w in W: by_artist.setdefault(w["a"], []).append(w)

CSS = ("body{margin:0;padding:28px;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
       "background:#fff;color:#111;max-width:940px}"
       "@media(prefers-color-scheme:dark){body{background:#0b0c0e;color:#f1f2f4}a{color:#9ec5ff}"
       "th,td{border-color:#2b2e34!important}.m{color:#8b9098!important}}"
       "h1{font-size:1.7rem;margin:0 0 4px;font-weight:600}"
       ".m{color:#666;font-size:.85rem;margin:0 0 14px}"
       "table{border-collapse:collapse;width:100%;font-size:.88rem;margin-top:14px}"
       "th,td{text-align:left;padding:5px 9px 5px 0;border-bottom:1px solid #e3e5e9;vertical-align:top}"
       "th{font-size:.7rem;text-transform:uppercase;letter-spacing:.09em;color:#666;font-weight:500}"
       "p.bio{max-width:66ch}a.cta{display:inline-block;margin:12px 0}nav{font-size:.85rem;margin-bottom:18px}"
       ".rel{font-size:.85rem;color:#666;margin:6px 0;max-width:80ch;line-height:1.7}"
       ".rel.nb{margin-top:22px;padding-top:12px;border-top:1px solid #e3e5e9}"
       "@media(prefers-color-scheme:dark){.rel{color:#8b9098}.rel.nb{border-color:#2b2e34}}"
       # The app offers this as "printable page for this artist", so make that true:
       # drop the navigation and the call to action, force black on white regardless of
       # the reader's theme, and keep table rows from splitting across pages.
       "@media print{body{background:#fff;color:#000;padding:0;max-width:none;font-size:11pt}"
       "nav,a.cta,.rel{display:none}a{color:#000;text-decoration:none}"
       "th,td{border-color:#999!important}tr{break-inside:avoid}"
       "thead{display:table-header-group}h1{font-size:16pt}"
       "table{font-size:9pt}}")


def jsonld(a, ws, sl, dates):
    """schema.org description of the artist and a sample of their works.

    Plain HTML tells a crawler these are words; this tells it they are an artist and
    artworks, which is what lets an art-specific query match. Only the first 50 works
    are described — enough to characterise the page without a megabyte of JSON."""
    life = a.get("l") or ["", ""]
    person = {"@type": "Person", "name": a["n"], "url": f"{BASE}/a/{sl}.html"}
    if life[0]: person["birthDate"] = life[0]
    if life[1]: person["deathDate"] = life[1]
    if a.get("born"): person["birthPlace"] = {"@type": "Place", "name": a["born"]}
    if a.get("qid"): person["sameAs"] = f"https://www.wikidata.org/wiki/{a['qid']}"
    if a.get("wdesc"): person["description"] = a["wdesc"]
    if a.get("aff"): person["nationality"] = a["aff"]
    for g in a.get("grp", []):
        kind, label = g.split(":", 1)
        key = {"school": "alumniOf", "member": "memberOf", "movement": "movement"}[kind]
        org = {"@type": "Organization", "name": label} if kind != "movement" else label
        person.setdefault(key, []).append(org)
    works = []
    for w in ws[:50]:
        it = {"@type": "VisualArtwork", "name": w.get("t") or "—",
              "creator": {"@type": "Person", "name": a["n"]}}
        if w.get("y"): it["dateCreated"] = str(w["y"])
        if val(w, "tc") or val(w, "tce"): it["artMedium"] = val(w, "tc") or val(w, "tce")
        if val(w, "e"): it["artform"] = val(w, "e")
        if val(w, "mu"): it["holdingArchive"] = {"@type": "Organization", "name": val(w, "mu")}
        works.append(it)
    return json.dumps({"@context": "https://schema.org", "@graph": [person,
        {"@type": "CollectionPage", "name": f"Works by {a['n']}",
         "url": f"{BASE}/a/{sl}.html", "about": person,
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(ws),
                        "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": it}
                                            for i, it in enumerate(works)]}}]},
        ensure_ascii=False, separators=(",", ":"))

# ---- related artists -------------------------------------------------------
# Until now every artist page was an orphan: it linked up to the catalogue and
# across to the app, never sideways to another artist. That is a dead end for a
# reader who has just found a name they did not know, and for a crawler it means
# each page is reachable only from the A-Z index, with no reason to go deeper.
#
# Three relations, and every page gets at least one. Alphabetical neighbours are
# always available and chain all 3,664 pages into a single traversable sequence.
# A shared school or movement is the strongest link we hold, but only 745 artists
# carry one. Contemporaries -- nearest in working period within the same
# collection -- covers the rest.
LIVE   = [i for i in range(len(A)) if by_artist.get(i)]
SLUG   = {i: (slug(A[i]["n"]) or f"artist-{i}") for i in LIVE}
NWORKS = {i: len(by_artist[i]) for i in LIVE}

def period(i):
    """One year placing an artist in time, for ordering only.

    The median year of their dated works is the most honest single number: it is
    what the catalogue actually knows. Birth year plus 35 stands in when nothing
    is dated, which is roughly when a painter's catalogued work begins."""
    ys = sorted(w["y"] for w in by_artist[i] if w.get("y"))
    if ys: return ys[len(ys) // 2]
    m = re.search(r"\d{4}", str((A[i].get("l") or [""])[0] or ""))
    return int(m.group()) + 35 if m else None

by_grp = {}
for i in LIVE:
    for g in A[i].get("grp", []): by_grp.setdefault(g, []).append(i)

# Bucket by the artist's principal holder, ordered by period, so contemporaries
# are the neighbours in that ordering -- no 3,664-squared comparison needed.
PERIOD, principal, by_holder = {}, {}, {}
for i in LIVE:
    PERIOD[i] = period(i)
    c = {}
    for w in by_artist[i]:
        h = val(w, "mu")
        if h: c[h] = c.get(h, 0) + 1
    if c and PERIOD[i]:
        principal[i] = max(c, key=c.get)
        by_holder.setdefault(principal[i], []).append(i)
for h in by_holder:
    by_holder[h].sort(key=lambda i: PERIOD[i])
HPOS = {h: {i: n for n, i in enumerate(lst)} for h, lst in by_holder.items()}

ALPHA = sorted(LIVE, key=lambda i: A[i]["n"])
APOS  = {i: n for n, i in enumerate(ALPHA)}

def link(i):
    return f'<a href="{BASE}/a/{SLUG[i]}.html">{e(A[i]["n"])}</a>'

def related(i):
    """Rendered related-artist lines for artist i, or an empty string."""
    seen, out = {i}, []
    # Rarest shared group first: "Atelier School of Ants Laikmaa" tells a reader
    # far more than "Estonian Academy of Arts", which 343 artists share.
    for g in sorted(A[i].get("grp", []), key=lambda g: len(by_grp[g]))[:2]:
        peers = [j for j in sorted(by_grp[g], key=lambda j: -NWORKS[j]) if j not in seen][:5]
        if not peers: continue
        seen.update(peers)
        kind, label = g.split(":", 1)
        lead = {"school": f"Also trained at {label}",
                "movement": f"Also working in {label}",
                "member": f"Also in {label}"}[kind]
        out.append(f'<p class="rel">{e(lead)}: ' + " · ".join(link(j) for j in peers) + "</p>")
    h = principal.get(i)
    if h:
        lst, pos = by_holder[h], HPOS[h][i]
        near = [lst[n] for n in range(max(0, pos - 6), min(len(lst), pos + 7)) if lst[n] not in seen]
        near.sort(key=lambda j: (abs(PERIOD[j] - PERIOD[i]), -NWORKS[j]))
        near = near[:5]
        if near:
            seen.update(near)
            out.append(f'<p class="rel">Contemporaries in {e(h)}: '
                       + " · ".join(link(j) for j in near) + "</p>")
    return "".join(out)

def neighbours(i):
    """Previous and next alphabetically -- the chain that connects every page."""
    n, parts = APOS[i], []
    if n > 0:            parts.append("&larr; " + link(ALPHA[n - 1]))
    parts.append(f'<a href="{BASE}/a/">All artists A&ndash;Z</a>')
    if n < len(ALPHA) - 1: parts.append(link(ALPHA[n + 1]) + " &rarr;")
    return '<p class="rel nb">' + " · ".join(parts) + "</p>"

pages, index_rows = 0, []
for i, a in enumerate(A):
    ws = by_artist.get(i, [])
    if not ws: continue
    sl = slug(a["n"]) or f"artist-{i}"
    life = a.get("l") or ["", ""]
    dates = f"{life[0]}–{life[1]}" if life[0] or life[1] else ""
    years = sorted({w["y"] for w in ws if w.get("y")})
    span = f"{years[0]}–{years[-1]}" if years else ""
    holders = sorted({val(w, "mu") for w in ws if val(w, "mu")})
    desc = (f"{a['n']}{' (' + dates + ')' if dates else ''} — {len(ws)} works in Estonian public "
            f"collections{' and galleries' if any(w.get('kind')=='gallery' for w in ws) else ''}"
            f"{', ' + span if span else ''}. " + (a.get("wdesc") or ""))[:300]

    rows = "".join(
        f"<tr><td>{e(w.get('y') or w.get('yl') or '—')}</td><td>{e(w.get('t'))}</td>"
        f"<td>{e(val(w,'tc') or val(w,'tce') or '')}</td><td>{e(w.get('dm') or '')}</td>"
        f"<td>{e(val(w,'mu') or '')}</td></tr>"
        for w in sorted(ws, key=lambda x: (x.get("y") is None, x.get("y") or 0, x.get("t") or ""))[:600])

    doc = (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
           f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           f"<title>{e(a['n'])}{' (' + dates + ')' if dates else ''} — Estonian Art Catalogue</title>"
           f"<meta name=\"description\" content=\"{e(desc)}\">"
           f"<link rel=\"canonical\" href=\"{BASE}/a/{sl}.html\">"
           f"<meta property=\"og:type\" content=\"profile\">"
           f"<meta property=\"og:title\" content=\"{e(a['n'])}{' (' + dates + ')' if dates else ''}\">"
           f"<meta property=\"og:description\" content=\"{e(desc)}\">"
           f"<meta property=\"og:url\" content=\"{BASE}/a/{sl}.html\">"
           f"<meta property=\"og:site_name\" content=\"Estonian Art Catalogue\">"
           f"<meta name=\"twitter:card\" content=\"summary\">"
           f"<script type=\"application/ld+json\">{jsonld(a, ws, sl, dates)}</script>"
           f"<style>{CSS}</style></head><body>"
           f"<nav><a href=\"{BASE}/\">Estonian Art Catalogue</a> › {e(a['n'])}</nav>"
           f"<h1>{e(a['n'])}</h1>"
           f"<p class=\"m\">{e(dates)}{' · ' if dates and a.get('wdesc') else ''}{e(a.get('wdesc') or '')}"
           f"{'<br>' if holders else ''}{e('; '.join(holders[:6]))}</p>"
           + (f"<p class=\"m\">{e(' · '.join(KIND[g.split(':',1)[0]] + ' ' + g.split(':',1)[1] for g in a.get('grp', [])))}</p>"
              if a.get("grp") else "")
           + (f"<p class=\"bio\">{e(a.get('b') or a.get('ben') or '')}</p>" if (a.get('b') or a.get('ben')) else "")
           + f"<p><a class=\"cta\" href=\"{BASE}/#artist={sl}\">Browse {len(ws)} works in the catalogue →</a></p>"
           + related(i)
           + (f"<p class=\"m\">Showing the first 600 of {len(ws):,} works — "
              f"<a href=\"{BASE}/#artist={sl}\">see all in the catalogue</a>.</p>" if len(ws) > 600 else "")
           + f"<table><thead><tr><th>Year</th><th>Title</th><th>Technique</th><th>Dimensions</th>"
           f"<th>Held by</th></tr></thead><tbody>{rows}</tbody></table>"
           + neighbours(i)
           + f"<p class=\"m\">Museum records from MuIS and the EKM Digital Collection; gallery stock from the galleries' own catalogues. "
           f"<a href=\"{BASE}/\">Full catalogue</a></p></body></html>")
    open(f"{OUT}/{sl}.html", "w", encoding="utf-8").write(doc)
    pages += 1
    index_rows.append((sl, a["n"], len(ws)))

today = datetime.date.today().isoformat()
urls = "".join(f"<url><loc>{BASE}/a/{sl}.html</loc><lastmod>{today}</lastmod></url>" for sl, _, _ in index_rows)
open("site/sitemap.xml", "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    f'<url><loc>{BASE}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>{urls}</urlset>')
open("site/robots.txt", "w", encoding="utf-8").write(
    f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

# a plain index so crawlers reach every artist page from one place
lst = "".join(f'<li><a href="{BASE}/a/{sl}.html">{html.escape(n)}</a> <span class="m">{c}</span></li>'
              for sl, n, c in sorted(index_rows, key=lambda r: r[1]))
open("site/a/index.html", "w", encoding="utf-8").write(
    f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
    f'<meta name="viewport" content="width=device-width,initial-scale=1">'
    f'<title>Artists A–Z — Estonian Art Catalogue</title>'
    f'<meta name="description" content="Every artist in the Estonian Art Catalogue: {len(index_rows):,} '
    f'artists represented in Estonian public collections and galleries.">'
    f'<link rel="canonical" href="{BASE}/a/"><style>{CSS}ul{{columns:260px;list-style:none;padding:0}}'
    f'li{{break-inside:avoid;padding:2px 0}}</style></head><body>'
    f'<nav><a href="{BASE}/">Estonian Art Catalogue</a> › Artists</nav>'
    f'<h1>Artists A–Z</h1><p class="m">{len(index_rows):,} artists</p><ul>{lst}</ul></body></html>')

# ---- retired names: redirect stubs --------------------------------------------
# A spelling merged away in merge.py had an artist page of its own, indexed and
# bookmarked. Each old URL now carries a stub that says where the artist went and
# sends the reader there; the canonical tag tells a crawler the same.
_retired = os.path.join("data", "retired_names.json")
stubs = 0
if os.path.exists(_retired):
    live = {a["n"]: SLUG[i] for i, a in enumerate(A) if i in SLUG}
    for old, new in json.load(open(_retired, encoding="utf-8")).items():
        if new not in live: continue
        osl, nsl = slug(old), live[new]
        if osl == nsl or os.path.exists(f"{OUT}/{osl}.html"): continue
        open(f"{OUT}/{osl}.html", "w", encoding="utf-8").write(
            f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{e(old)} — see {e(new)} — Estonian Art Catalogue</title>"
            f"<link rel=\"canonical\" href=\"{BASE}/a/{nsl}.html\">"
            f"<meta http-equiv=\"refresh\" content=\"0; url={BASE}/a/{nsl}.html\">"
            f"<meta name=\"robots\" content=\"noindex\"><style>{CSS}</style></head><body>"
            f"<nav><a href=\"{BASE}/\">Estonian Art Catalogue</a> › {e(old)}</nav>"
            f"<h1>{e(old)}</h1><p class=\"m\">This spelling has been merged. The artist is catalogued as "
            f"<a href=\"{BASE}/a/{nsl}.html\">{e(new)}</a> — taking you there.</p></body></html>")
        stubs += 1

# ---- 404 --------------------------------------------------------------------
# GitHub Pages serves 404.html for any missing path. A stale link usually names
# an artist, so the page offers a search prefilled from the path, and the A-Z.
open("site/404.html", "w", encoding="utf-8").write(
    f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
    f"<title>Not found — Estonian Art Catalogue</title><meta name=\"robots\" content=\"noindex\">"
    f"<style>{CSS}form{{display:flex;gap:8px;max-width:520px;margin:18px 0}}"
    f"input{{flex:1;font:inherit;padding:8px 10px;border:1px solid #bbb}}button{{font:inherit;padding:8px 14px}}</style></head><body>"
    f"<nav><a href=\"{BASE}/\">Estonian Art Catalogue</a> › Not found</nav>"
    f"<h1>There is no page here</h1>"
    f"<p class=\"m\" id=\"why\">The address may be misspelt, or the page has moved.</p>"
    f"<form id=\"f\"><input id=\"q\" placeholder=\"Search the catalogue\" aria-label=\"Search\"><button>Search</button></form>"
    f"<p><a href=\"{BASE}/a/\">Artists A–Z / Kunstnikud A–Ü</a> · <a href=\"{BASE}/\">Full catalogue</a></p>"
    f"<script>"
    f"var m=location.pathname.match(/\\/a\\/([^\\/]+?)(?:\\.html)?$/);"
    f"if(m){{var w=decodeURIComponent(m[1]).replace(/-/g,' ');document.getElementById('q').value=w;"
    f"document.getElementById('why').textContent='No artist page at this address. The name may have been merged with another spelling — try the search.';}}"
    f"document.getElementById('f').onsubmit=function(ev){{ev.preventDefault();var q=document.getElementById('q').value.trim();"
    f"location.href='{BASE}/#'+(q?'q='+encodeURIComponent(q):'');}};"
    f"</script></body></html>")

print(f"  redirect stubs {stubs:,}")
print(f"  artist pages   {pages:,}")
print(f"  sitemap        {len(index_rows)+1:,} urls")
print(f"  total size     {sum(os.path.getsize(os.path.join(OUT,f)) for f in os.listdir(OUT))/1048576:.1f} MB")
