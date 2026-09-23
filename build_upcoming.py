# -*- coding: utf-8 -*-
"""The coming sales: /upcoming.html and /tulemas.html.

Every lot in a sale still to come (data/upcoming.py, joined to the artists by merge.py),
by date and house: the artist, the work, the starting price as the house published it,
a link to the lot, and beside it the artist's record at auction from the catalogue --
how many lots, how many sold, the range of the hammer prices -- and, where the same
title was offered before, those results. No bids, no pictures. A record, not a valuation.
Run after build_pages.py (it adds to the sitemap) and before csp.py.
"""
import json, os, re, html, datetime, collections
import build_hubs as H

BASE, A, W, e = H.BASE, H.A, H.W, H.e
d = json.load(open("data/data.json", encoding="utf-8"))
UP = d.get("upcoming", [])
MUS_EN = H.MUSEUM_EN
lots_of = collections.defaultdict(list)
for w in W:
    if w.get("kind") == "auction": lots_of[w["a"]].append(w)

T = {"en": dict(file="upcoming.html", other="tulemas.html", h="Coming up at auction", site="Estonian Art Catalogue", art="a",
                lede="Every lot in the Estonian auction houses' coming sales by an artist in the catalogue, with the starting price as the house published it and the artist's record at auction beside it. Bids are not shown; the houses' own pages have them.",
                none="No coming sale has published its lots yet. The houses put their catalogues online two to four weeks before a sale; this page is refreshed every week.",
                start="starting price", rec="At auction: {n} lots, {s} sold{r}", rec0="First time at auction in the catalogue", prior="Same title before", unsold="unsold",
                lots="lots", other_l="Eesti keeles", note="A record, not a valuation. Refreshed weekly.", month=["January","February","March","April","May","June","July","August","September","October","November","December"]),
     "et": dict(file="tulemas.html", other="upcoming.html", h="Tulemas oksjonil", site="Eesti Kunstikataloog", art="k",
                lede="Kõik Eesti oksjonimajade tulevate oksjonite partiid kataloogi kunstnikelt, alghind nii, nagu maja selle avaldas, ja kõrval kunstniku senine oksjonitulemus. Pakkumisi ei näidata; need on majade endi lehtedel.",
                none="Ükski tulev oksjon pole veel oma partiisid avaldanud. Majad panevad kataloogi üles kaks kuni neli nädalat enne oksjonit; see leht uueneb iga nädal.",
                start="alghind", rec="Oksjonil: {n} partiid, {s} müüdud{r}", rec0="Kataloogis esimest korda oksjonil", prior="Sama pealkiri varem", unsold="müümata",
                lots="partiid", other_l="In English", note="Ülestähendus, mitte hinnang. Uueneb iga nädal.", month=["jaanuar","veebruar","märts","aprill","mai","juuni","juuli","august","september","oktoober","november","detsember"])}

fmt = lambda n, lang: f"{n:,}" if lang == "en" else f"{n:,}".replace(",", " ")
eur = lambda n, lang: "€" + fmt(n, lang)
house = lambda h, lang: MUS_EN.get(h, h) if lang == "en" else h
def day(dd, lang):
    if not dd: return ""
    y, m, *rest = str(dd).split("-")
    mo = T[lang]["month"][int(m) - 1]
    return (f"{int(rest[0])} {mo} {y}" if lang == "en" else f"{int(rest[0])}. {mo} {y}") if rest else f"{mo} {y}"
def record(ai, lang):
    L = lots_of.get(ai, [])
    if not L: return T[lang]["rec0"]
    ps = sorted(w["ap"] for w in L if w.get("ao") and w.get("ap"))
    r = f" · {eur(ps[0], lang)}–{eur(ps[-1], lang)}" if len(ps) > 1 else (f" · {eur(ps[0], lang)}" if ps else "")
    return T[lang]["rec"].format(n=fmt(len(L), lang), s=fmt(sum(1 for w in L if w.get("ao")), lang), r=r)

def main():
    urls = []
    for lang in ("en", "et"):
        t = T[lang]
        groups = collections.OrderedDict()
        for u in sorted(UP, key=lambda u: (u.get("d") or "9", u["h"], u["s"] or "", A[u["a"]]["n"], u["t"])):
            groups.setdefault((u.get("d"), u["h"], u["s"]), []).append(u)
        body = ""
        for (dd, h, s), lots in groups.items():
            body += f'<h2>{e(day(dd, lang))} · {e(house(h, lang))}{" · " + e(s) if s else ""} <span class="m">{fmt(len(lots), lang)} {t["lots"]}</span></h2><table><tbody>'
            for u in lots:
                sl = H.ARTIST_SLUG[u["a"]]
                prior = (f'<br><span class="m">{t["prior"]}: ' + " · ".join(f'{e(str(p[0])[:4])} {e(house(p[1], lang))} {eur(p[2], lang) if p[2] else t["unsold"]}' for p in u["pr"]) + "</span>") if u.get("pr") else ""
                lot = f'<a href="{e(u["u"])}" rel="noopener">{e(house(h, lang))} ↗</a>' if str(u.get("u") or "").startswith("http") else ""
                body += (f'<tr><td><a href="{BASE}/{t["art"]}/{sl}.html">{e(A[u["a"]]["n"])}</a><br><span class="m">{e(record(u["a"], lang))}</span></td>'
                         f'<td><i>{e(u["t"])}</i>{", " + e(u["yl"]) if u.get("yl") else ""}<br><span class="m">{e(" · ".join(x for x in (u.get("tc"), u.get("dm")) if x))}</span>{prior}</td>'
                         f'<td class="n">{(t["start"] + " " + eur(u["p"], lang)) if u.get("p") else ""}<br>{lot}</td></tr>')
            body += "</tbody></table>"
        me, other = f"{BASE}/{t['file']}", f"{BASE}/{t['other']}"
        n = len(UP)
        title = f'{t["h"]} – {fmt(n, lang)} {t["lots"]} · museaal.ee' if n else f'{t["h"]} · museaal.ee'
        page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{e(title)}</title><meta name="description" content="{e(t["lede"][:290])}">'
                f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
                f'<style>{H.CSS}table{{border-collapse:collapse;width:100%;font-size:.9rem;margin:6px 0 18px}}td{{padding:7px 10px 7px 0;border-bottom:1px solid #2b2e34;vertical-align:top}}'
                f':root[data-theme=light] td{{border-color:#e3e5e9}}td.n{{text-align:right;white-space:nowrap}}h2 .m{{font-size:.8rem;margin-left:8px}}</style>{H.GC}</head><body>'
                f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{t["site"]}</a> › {t["h"]} <span class="m">· <a href="{other}">{t["other_l"]}</a></span></nav>'
                f'<h1>{t["h"]}</h1><p class="lede">{e(t["lede"])}</p>'
                + (body or f'<p class="m">{e(t["none"])}</p>')
                + f'<p class="m">{e(t["note"])}</p></body></html>')
        open(f"site/{t['file']}", "w", encoding="utf-8").write(page)
        urls.append(me)
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  coming sales   {len(UP):,} lots in {len({(u.get('d'), u['h'], u['s']) for u in UP})} sale day(s); upcoming.html, tulemas.html")

if __name__ == "__main__":
    main()
