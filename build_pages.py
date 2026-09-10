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

BASE = "https://bertpeterson.github.io/estonian-art-catalogue"
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
       "p.bio{max-width:66ch}a.cta{display:inline-block;margin:12px 0}nav{font-size:.85rem;margin-bottom:18px}")

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
           f"<style>{CSS}</style></head><body>"
           f"<nav><a href=\"{BASE}/\">Estonian Art Catalogue</a> › {e(a['n'])}</nav>"
           f"<h1>{e(a['n'])}</h1>"
           f"<p class=\"m\">{e(dates)}{' · ' if dates and a.get('wdesc') else ''}{e(a.get('wdesc') or '')}"
           f"{'<br>' if holders else ''}{e('; '.join(holders[:6]))}</p>"
           + (f"<p class=\"bio\">{e(a.get('b') or a.get('ben') or '')}</p>" if (a.get('b') or a.get('ben')) else "")
           + f"<p><a class=\"cta\" href=\"{BASE}/#artist={sl}\">Browse {len(ws)} works in the catalogue →</a></p>"
           + (f"<p class=\"m\">Showing the first 600 of {len(ws):,} works — "
              f"<a href=\"{BASE}/#artist={sl}\">see all in the catalogue</a>.</p>" if len(ws) > 600 else "")
           + f"<table><thead><tr><th>Year</th><th>Title</th><th>Technique</th><th>Dimensions</th>"
           f"<th>Held by</th></tr></thead><tbody>{rows}</tbody></table>"
           f"<p class=\"m\">Data from MuIS and the EKM Digital Collection. "
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

print(f"  artist pages   {pages:,}")
print(f"  sitemap        {len(index_rows)+1:,} urls")
print(f"  total size     {sum(os.path.getsize(os.path.join(OUT,f)) for f in os.listdir(OUT))/1048576:.1f} MB")
