# -*- coding: utf-8 -*-
"""Circle pages: the schools, studios and groups artists stood in, and who taught whom.

One page per circle in data/lineage.json (data/lineage.py) -- Pallas, Laikmaa's studio
school, ANK '64 and the rest -- in English and Estonian, plus an index of them: the
members with their dates, a wall of their pictures, and the teacher links that touch
the circle. Generated, never edited by hand; run after build_hubs.py (it appends to
the sitemap) and before csp.py.

  EN /circles/<id>   /circles/
  ET /ringid/<id>    /ringid/
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
                members="Members in the catalogue", teach="Teachers and pupils", born="born", artists="artists", links="teacher links",
                t="{c} – {n} artists in the Estonian Art Catalogue · museaal.ee",
                d="{c}: {d} {n} artists in the catalogue, with their works, pictures and who taught whom."),
     "et": dict(dir="ringid", art="k", site="Eesti Kunstikataloog", site_link="#lang=et", other="In English", h="Ringid ja koolkonnad",
                lede="Koolid, ateljeed ja rühmitused, kus Eesti kunstnikud õppisid ja töötasid, ning kes keda õpetas — Wikidata ja kunstnike elulugude järgi.",
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
                + f'<p class="nb"><a href="{BASE}/{T["dir"]}/">{T["h"]}</a> · {others}</p>'
                + f'<p class="m">{CONTACT[lang]}</p></body></html>')
            open(f"site/{T['dir']}/{c['id']}.html", "w", encoding="utf-8").write(body)
            urls.append((me, href(c, "en"), href(c, "et")))
        me, other = f"{BASE}/{T['dir']}/", f"{BASE}/{O['dir']}/"
        lst = "".join(f'<li><a href="{href(c, lang)}">{e(c[lang])}</a><span class="n">{fmt(len(c["members"]), lang)}</span><br><span class="m">{e(c["d_" + lang])}</span></li>' for c in CIRCLES)
        open(f"site/{T['dir']}/index.html", "w", encoding="utf-8").write(
            head(lang, me, other, f"{BASE}/{L['en']['dir']}/", f"{T['h']} · museaal.ee", T["lede"])
            + f'<nav><a href="{BASE}/{T["site_link"]}">{T["site"]}</a> › {T["h"]} <span class="m">· <a href="{other}">{T["other"]}</a></span></nav>'
            + f'<h1>{T["h"]}</h1><p class="lede">{T["lede"]}</p><p class="m">{fmt(len(LINKS), lang)} {T["links"]}</p><ul class="tl">{lst}</ul>'
            + f'<p class="nb"><a href="{BASE}/{T["art"]}/">{"Artists A–Z" if lang == "en" else "Kunstnikud A–Ü"}</a></p><p class="m">{CONTACT[lang]}</p></body></html>')
        urls.append((me, f"{BASE}/{L['en']['dir']}/", f"{BASE}/{L['et']['dir']}/"))
    today = datetime.date.today().isoformat()
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    add = "".join(f'<url><loc>{me}</loc><lastmod>{today}</lastmod><xhtml:link rel="alternate" hreflang="en" href="{en}"/><xhtml:link rel="alternate" hreflang="et" href="{et}"/></url>' for me, en, et in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  circle pages   {len(urls):,} ({len(CIRCLES)} circles and an index, both languages; {len(LINKS)} teacher links)")

if __name__ == "__main__":
    main()
