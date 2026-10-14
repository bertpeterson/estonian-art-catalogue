# -*- coding: utf-8 -*-
"""Circle pages: the schools, studios and groups artists stood in, and who taught whom.

One page per circle in data/lineage.json (data/lineage.py) -- Pallas, Laikmaa's studio
school, ANK '64 and the rest -- in English and Estonian, plus an index of them: the
members with their dates, a wall of their pictures, and the teacher links that touch
the circle. Generated, never edited by hand; run after build_hubs.py (it appends to
the sitemap) and before csp.py.

  EN /circles/<id>   /circles/   /circles/network
  ET /ringid/<id>    /ringid/     /ringid/vorgustik

The network is a lineage chart: every artist with a teacher link, placed left to right
by year of birth, so a line runs from a teacher to a later pupil; coloured by circle.
The layout is computed here and written as plain SVG of links -- crawlable, and whole
without its script, which only lights up an artist's lines on hover or tap.
"""
import json, os, re, datetime, collections
import build_hubs as H
from build_hubs import BASE, A, W, e, fmt, CSS, STAMP, GC, CONTACT, ARTIST_SLUG

LIN = json.load(open("data/lineage.json", encoding="utf-8"))
CIRCLES, LINKS = LIN["circles"], LIN["links"]
I = {a["n"]: i for i, a in enumerate(A) if a.get("c", 0) > 0}
by_artist = collections.defaultdict(list)
for w in W: by_artist[w["a"]].append(w)

L = {"en": dict(dir="circles", art="a", site="Estonian Art Catalogue", site_link="", other="Eesti keeles", h="Circles and lineages",
                lede="The schools, studios and groups Estonian artists learnt and worked in, and who taught whom — from Wikidata and the artists' biographies.",
                net="The network", net_h="Who taught whom", net_lede="{n} artists joined by {k} teacher links. Each artist stands at their year of birth, so a line runs from a teacher to a pupil born later; the colour is the circle. Point at an artist to light up their teachers and pupils, click to open their page.",
                net_t="Who taught whom in Estonian art – {n} artists, {k} links · museaal.ee", top="Teachers with the most pupils", none="no circle",
                members="Members in the catalogue", teach="Teachers and pupils", born="born", artists="artists", links="teacher links",
                t="{c} – {n} artists in the Estonian Art Catalogue · museaal.ee",
                d="{c}: {d} {n} artists in the catalogue, with their works, pictures and who taught whom."),
     "et": dict(dir="ringid", art="k", site="Eesti Kunstikataloog", site_link="#lang=et", other="In English", h="Ringid ja koolkonnad",
                lede="Koolid, ateljeed ja rühmitused, kus Eesti kunstnikud õppisid ja töötasid, ning kes keda õpetas — Wikidata ja kunstnike elulugude järgi.",
                net="Võrgustik", net_h="Kes keda õpetas", net_lede="{n} kunstnikku, keda ühendab {k} õpetaja-õpilase seost. Iga kunstnik on oma sünniaasta kohal, nii et joon viib õpetajalt hiljem sündinud õpilaseni; värv näitab ringi. Osuta kunstnikule, et näha tema õpetajaid ja õpilasi, klõpsa, et avada tema leht.",
                net_t="Kes keda õpetas Eesti kunstis – {n} kunstnikku, {k} seost · museaal.ee", top="Kõige rohkemate õpilastega õpetajad", none="ringita",
                members="Liikmed kataloogis", teach="Õpetajad ja õpilased", born="sündinud", artists="kunstnikku", links="õpetaja-õpilase seost",
                t="{c} – {n} kunstnikku Eesti Kunstikataloogis · museaal.ee",
                d="{c}: {d} {n} kunstnikku kataloogis, nende teosed, pildid ja kes keda õpetas.")}

def born(i):
    m = re.search(r"\d{4}", str((A[i].get("l") or [""])[0] or ""))
    return int(m.group()) if m else None
def dates(i):
    l = A[i].get("l") or ["", ""]
    return f"{l[0]}–{l[1]}" if l[0] or l[1] else ""
def alink(i, lang): return f'<a href="{BASE}/{L[lang]["art"]}/{ARTIST_SLUG[i]}">{e(A[i]["n"])}</a>'
def href(c, lang): return f"{BASE}/{L[lang]['dir']}/{c['id']}"

COLOURS = {"pallas": "#e8a33d", "laikmaa": "#3fb59a", "group-of-estonian-artists": "#b77ce0", "ank-64": "#5b9cf5",
           "soup-69": "#ef6f6c", "vikerla": "#8cbf4f", "young-estonia": "#d4b84a", "visarid": "#e07cb5"}
def net_href(lang): return f"{BASE}/{L[lang]['dir']}/{'network' if lang == 'en' else 'vorgustik'}"

def layout():
    """x by year of birth, y by relaxation within each connected group, the groups packed into lanes."""
    links = [(I[t], I[p]) for t, p, *_ in LINKS if t in I and p in I]
    nodes = sorted({x for l in links for x in l})
    adj = collections.defaultdict(set)
    for t, p in links: adj[t].add(p); adj[p].add(t)
    yr = {i: born(i) for i in nodes}
    for _ in range(3):                                     # no birth year: a generation from a dated neighbour
        for i in nodes:
            if yr[i] is None:
                g = [yr[t] + 25 for t, p in links if p == i and yr[t]] + [yr[p] - 25 for t, p in links if t == i and yr[p]]
                if g: yr[i] = sum(g) // len(g)
    for i in nodes: yr[i] = yr[i] or 1900
    WID, PAD = 1160, 20
    def X(y):                                              # the centuries before 1800 are few artists: a narrower band
        y0 = min(yr.values()) - 5
        cut = 1800 if y0 < 1780 else y0
        lo = 0.16 if y0 < 1780 else 0
        f = lo * (min(y, cut) - y0) / max(cut - y0, 1) + (1 - lo) * max(0, y - cut) / (1995 - cut)
        return PAD + f * (WID - 2 * PAD)
    x = {i: X(yr[i]) for i in nodes}
    comps, seen = [], set()
    for i in sorted(nodes, key=lambda i: -len(adj[i])):
        if i in seen: continue
        st, c = [i], []
        while st:
            k = st.pop()
            if k in seen: continue
            seen.add(k); c.append(k); st += adj[k]
        comps.append(c)
    y, lanes, H = {}, [], 0
    for c in sorted(comps, key=len, reverse=True):
        loc = {k: n * 14.0 for n, k in enumerate(c)}
        for it in range(500):                              # pull towards neighbours, push apart whatever stands too close;
            for k in c if it < 400 else ():                # the last rounds only push, so no two names sit on each other
                nb = adj[k]
                loc[k] += 0.15 * (sum(loc[j] for j in nb) / len(nb) - loc[k])
            for a_ in range(len(c)):
                for b_ in range(a_ + 1, len(c)):
                    a, b = c[a_], c[b_]
                    if abs(x[a] - x[b]) < 90:
                        d = loc[a] - loc[b]
                        if abs(d) < 24:
                            push = (24 - abs(d)) / 2 * (1 if d > 0 or (d == 0 and a < b) else -1)
                            loc[a] += push; loc[b] -= push
        lo_, hi_ = min(loc.values()), max(loc.values())
        # room for the names shown: the labelled artists' (three links or more), else just the dots
        x0 = min(x[k] for k in c) - 10
        x1 = max([x[k] + 12 for k in c] + [x[k] + 7 * len(A[k]["n"]) for k in c if len(adj[k]) >= 3])
        # the first lane this group fits beside without overlapping in time; else a new lane
        for ln in lanes:
            if ln["h"] >= hi_ - lo_ and all(x1 < a or x0 > b for a, b in ln["spans"]):
                break
        else:
            ln = dict(top=H, h=hi_ - lo_, spans=[]); lanes.append(ln); H += hi_ - lo_ + 22
        ln["spans"].append((x0, x1))
        for k in c: y[k] = ln["top"] + 24 + (loc[k] - lo_)
    ticks = [(X(t), t) for t in (1600, 1700, 1800, 1850, 1900, 1950) if min(yr.values()) - 5 <= t <= 1995]
    return nodes, links, adj, x, y, H + 30, WID, ticks

def network(lang):
    T = L[lang]
    nodes, links, adj, x, y, H, WID, ticks = layout()
    first = {}
    for c in CIRCLES:
        for n in c["members"]:
            if n in I: first.setdefault(I[n], c["id"])
    deg = {i: len(adj[i]) for i in nodes}
    pos = {i: n for n, i in enumerate(nodes)}
    svg = [f'<svg id="net" viewBox="0 0 {WID} {H:.0f}" role="img" aria-label="{e(T["net_h"])}">']
    for tx, ty in ticks:                                   # the time axis, as faint rules
        svg.append(f'<g class="tk"><line x1="{tx:.0f}" y1="0" x2="{tx:.0f}" y2="{H:.0f}"/><text x="{tx + 3:.0f}" y="12">{ty}</text></g>')
    for t, p in links:
        mx = (x[t] + x[p]) / 2
        svg.append(f'<path class="ed" data-a="{pos[t]}" data-b="{pos[p]}" d="M{x[t]:.1f},{y[t]:.1f} C{mx:.1f},{y[t]:.1f} {mx:.1f},{y[p]:.1f} {x[p]:.1f},{y[p]:.1f}"/>')
    for i in nodes:
        r = 3 + deg[i] ** 0.5 * 1.6
        col = COLOURS.get(first.get(i), "#8b9098")
        lab = A[i]["n"] if deg[i] >= 3 else ""
        svg.append(f'<a class="nd" id="{ARTIST_SLUG[i]}" data-i="{pos[i]}" href="{BASE}/{T["art"]}/{ARTIST_SLUG[i]}">'
                   f'<title>{e(A[i]["n"])}{" (" + e(dates(i)) + ")" if dates(i) else ""}</title>'
                   f'<circle cx="{x[i]:.1f}" cy="{y[i]:.1f}" r="{r:.1f}" fill="{col}"/>'
                   f'<text x="{x[i] + r + 3:.1f}" y="{y[i] + 3.5:.1f}"{"" if lab else " class=hid"}>{e(re.sub(r" *[(].*?[)]", "", A[i]["n"]))}</text></a>')
    svg.append("</svg>")
    used = [c for c in CIRCLES if any(first.get(i) == c["id"] for i in nodes)]
    legend = '<p class="lg">' + "".join(f'<button type="button" data-c="{c["id"]}"><i style="background:{COLOURS[c["id"]]}"></i>{e(c[lang])}</button>' for c in used) \
             + f'<span><i style="background:#8b9098"></i>{T["none"]}</span></p>'
    members = {c["id"]: [pos[I[n]] for n in c["members"] if n in I and I[n] in pos] for c in used}
    pupils = collections.Counter(t for t, p in links)
    top = "".join(f'<li>{alink(t, lang)}<span class="n">{k}</span></li>' for t, k in pupils.most_common(12))
    js = ("(function(){var s=document.getElementById('net');if(!s)return;var M=" + json.dumps(members) + ";"
          "var E=[].slice.call(s.querySelectorAll('.ed')),N=[].slice.call(s.querySelectorAll('.nd')),nb={};"
          "E.forEach(function(p){var a=p.dataset.a,b=p.dataset.b;(nb[a]=nb[a]||[]).push(b);(nb[b]=nb[b]||[]).push(a);});"
          "function clear(){s.classList.remove('on');E.concat(N).forEach(function(x){x.classList.remove('hl')});}"
          "function show(set,edges){clear();s.classList.add('on');N.forEach(function(n){if(set[n.dataset.i])n.classList.add('hl')});"
          "E.forEach(function(p){if(edges(p))p.classList.add('hl')});}"
          "function one(i){var set={};set[i]=1;(nb[i]||[]).forEach(function(j){set[j]=1});show(set,function(p){return p.dataset.a==i||p.dataset.b==i});}"
          "var cur=null,touch=false;s.addEventListener('touchstart',function(){touch=true},{passive:true});"
          "N.forEach(function(n){n.addEventListener('mouseenter',function(){if(!touch)one(n.dataset.i)});n.addEventListener('mouseleave',function(){if(!touch)clear()});"
          "n.addEventListener('click',function(ev){if(touch&&cur!==n){ev.preventDefault();cur=n;one(n.dataset.i);}});});"
          "[].slice.call(document.querySelectorAll('.lg button')).forEach(function(b){b.addEventListener('click',function(){"
          "if(b.classList.contains('on')){b.classList.remove('on');clear();return;}"
          "[].slice.call(document.querySelectorAll('.lg button')).forEach(function(x){x.classList.remove('on')});b.classList.add('on');"
          "var set={};M[b.dataset.c].forEach(function(i){set[i]=1});show(set,function(p){return set[p.dataset.a]&&set[p.dataset.b]});});});"
          "var h=decodeURIComponent(location.hash.slice(1)),t=h&&document.getElementById(h);"
          "if(t&&t.dataset.i){one(t.dataset.i);t.scrollIntoView({block:'center',inline:'center'});}})();")
    css = ("div.nw{overflow-x:auto;margin:14px 0}#net{display:block;min-width:900px;width:100%;height:auto}"
           "#net .tk line{stroke:#2b2e34;stroke-width:1}#net .tk text{fill:#8b9098;font-size:10px}"
           ":root[data-theme=light] #net .tk line{stroke:#e3e4e6}"
           "#net .ed{fill:none;stroke:#8b9098;stroke-opacity:.45;stroke-width:1}"
           "#net .nd text{fill:#c7cace;font-size:10px}:root[data-theme=light] #net .nd text{fill:#333}#net .nd text.hid{display:none}"
           "#net .nd circle{stroke:#0b0c0e;stroke-width:1}:root[data-theme=light] #net .nd circle{stroke:#fff}"
           "#net.on .ed{stroke-opacity:.08}#net.on .nd{opacity:.25}#net.on .ed.hl{stroke-opacity:.95;stroke-width:1.6}"
           "#net.on .nd.hl{opacity:1}#net.on .nd.hl text.hid{display:inline}"
           ".lg{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.85rem;margin:8px 0}"
           ".lg button,.lg span{font:inherit;color:inherit;background:none;border:1px solid transparent;border-radius:3px;padding:2px 6px;cursor:pointer}"
           ".lg span{cursor:default;color:#8b9098}.lg button.on{border-color:#8b9098}"
           ".lg i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:0}")
    me, other = net_href(lang), net_href("et" if lang == "en" else "en")
    n, k = len(nodes), len(links)
    lede = T["net_lede"].format(n=n, k=k)
    open(f"site/{T['dir']}/{'network' if lang == 'en' else 'vorgustik'}.html", "w", encoding="utf-8").write(
        head(lang, me, other, net_href("en"), T["net_t"].format(n=n, k=k), lede).replace("</style>", css + "</style>")
        + f'<nav><a href="{BASE}/{T["site_link"]}">{T["site"]}</a> › <a href="{BASE}/{T["dir"]}/">{T["h"]}</a> › {T["net"]} <span class="m">· <a href="{other}">{T["other"]}</a></span></nav>'
        + f'<h1>{T["net_h"]}</h1><p class="lede">{e(lede)}</p>{legend}<div class="nw">{"".join(svg)}</div>'
        + f'<h2>{T["top"]}</h2><ul class="cols">{top}</ul>'
        + f'<p class="nb"><a href="{BASE}/{T["dir"]}/">{T["h"]}</a> · ' + " · ".join(f'<a href="{href(x, lang)}">{e(x[lang])}</a>' for x in CIRCLES) + "</p>"
        + f'<p class="m">{CONTACT[lang]}</p><script>{js}</script></body></html>')
    return me

def head(lang, me, other, xdefault, title, desc):
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><meta name="description" content="{e(desc[:300])}">'
            f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}"><link rel="alternate" hreflang="x-default" href="{xdefault}">'
            f'<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc[:300])}"><meta property="og:url" content="{me}">'
            f'<style>{CSS}ul.tl{{list-style:none;padding:0;margin:0}}ul.tl li{{padding:2px 0}}</style>{GC}</head><body>')

def main():
    urls = []
    for lang in ("en", "et"):
        T, O = L[lang], L["et" if lang == "en" else "en"]
        os.makedirs(f"site/{T['dir']}", exist_ok=True)
        for c in CIRCLES:
            mem = sorted((I[n] for n in c["members"] if n in I), key=lambda i: (born(i) or 9999, A[i]["n"]))
            ms = set(mem)
            name = c[lang]; desc_ = c["d_" + lang]
            ys = [born(i) for i in mem if born(i)]
            me, other = href(c, lang), href(c, "et" if lang == "en" else "en")
            # the teacher links with at least one end in the circle, the teacher's birth first
            tl = sorted((l for l in LINKS if l[0] in I and l[1] in I and (I[l[0]] in ms or I[l[1]] in ms)),
                        key=lambda l: (born(I[l[0]]) or 9999, l[0], l[1]))
            ws = [w for i in mem for w in by_artist[i]]
            others = " · ".join(f'<a href="{href(x, lang)}">{e(x[lang])}</a>' for x in CIRCLES if x is not c)
            body = (head(lang, me, other, href(c, "en"), T["t"].format(c=name, n=len(mem)), T["d"].format(c=name, d=desc_, n=len(mem)))
                + f'<nav><a href="{BASE}/{T["site_link"]}">{T["site"]}</a> › <a href="{BASE}/{T["dir"]}/">{T["h"]}</a> › {e(name)} <span class="m">· <a href="{other}">{T["other"]}</a></span></nav>'
                + f'<h1>{e(name)}</h1><p class="m">{fmt(len(mem), lang)} {T["artists"]}'
                + (f' · {T["born"]} {min(ys)}–{max(ys)}' if ys else "") + "</p>"
                + f'<p class="lede">{e(desc_)}</p>'
                + H.wall(ws, lang)
                + f'<h2>{T["members"]}</h2><ul class="cols">'
                + "".join(f'<li>{alink(i, lang)}<span class="n">{e(dates(i))}</span></li>' for i in mem) + "</ul>"
                + (f'<h2>{T["teach"]}</h2><ul class="tl">' + "".join(
                    f'<li{" title=" + chr(34) + e(l[3]) + chr(34) if l[3] else ""}>{alink(I[l[0]], lang)} → {alink(I[l[1]], lang)}</li>' for l in tl) + "</ul>" if tl else "")
                + f'<p class="nb"><a href="{BASE}/{T["dir"]}/">{T["h"]}</a> · <a href="{net_href(lang)}">{T["net"]}</a> · {others}</p>'
                + f'<p class="m">{CONTACT[lang]}</p></body></html>')
            open(f"site/{T['dir']}/{c['id']}.html", "w", encoding="utf-8").write(body)
            urls.append((me, href(c, "en"), href(c, "et")))
        me, other = f"{BASE}/{T['dir']}/", f"{BASE}/{O['dir']}/"
        lst = "".join(f'<li><a href="{href(c, lang)}">{e(c[lang])}</a><span class="n">{fmt(len(c["members"]), lang)}</span><br><span class="m">{e(c["d_" + lang])}</span></li>' for c in CIRCLES)
        open(f"site/{T['dir']}/index.html", "w", encoding="utf-8").write(
            head(lang, me, other, f"{BASE}/{L['en']['dir']}/", f"{T['h']} · museaal.ee", T["lede"])
            + f'<nav><a href="{BASE}/{T["site_link"]}">{T["site"]}</a> › {T["h"]} <span class="m">· <a href="{other}">{T["other"]}</a></span></nav>'
            + f'<h1>{T["h"]}</h1><p class="lede">{T["lede"]}</p><p class="m"><a href="{net_href(lang)}">{fmt(len(LINKS), lang)} {T["links"]} — {T["net"].lower()} →</a></p><ul class="tl">{lst}</ul>'
            + f'<p class="nb"><a href="{BASE}/{T["art"]}/">{"Artists A–Z" if lang == "en" else "Kunstnikud A–Ü"}</a></p><p class="m">{CONTACT[lang]}</p></body></html>')
        urls.append((me, f"{BASE}/{L['en']['dir']}/", f"{BASE}/{L['et']['dir']}/"))
        urls.append((network(lang), net_href("en"), net_href("et")))
    today = datetime.date.today().isoformat()
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    add = "".join(f'<url><loc>{me}</loc><lastmod>{today}</lastmod><xhtml:link rel="alternate" hreflang="en" href="{en}"/><xhtml:link rel="alternate" hreflang="et" href="{et}"/></url>' for me, en, et in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  circle pages   {len(urls):,} ({len(CIRCLES)} circles and an index, both languages; {len(LINKS)} teacher links)")

if __name__ == "__main__":
    main()
