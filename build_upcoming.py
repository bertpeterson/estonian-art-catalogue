# -*- coding: utf-8 -*-
"""The coming sales: /upcoming.html and /tulemas.html.

Every lot in a sale still to come (data/upcoming.py, joined to the artists by merge.py),
by date and house: the artist, the work, the starting price as the house published it,
a link to the lot, and beside it the artist's record at auction from the catalogue --
how many lots, how many sold, the range of the hammer prices -- and, where the same
title was offered before, those results. No bids, no pictures. A record, not a valuation.
Run after build_pages.py (it adds to the sitemap) and before csp.py.

A house whose lots are not read (Allee galerii) can be given its coming sales by hand in
data/sales_by_hand.json: a list of {"house", "sale", "date": first day, "end": last day
(optional), "lots": how many (optional), "url": the house's catalogue}. Each shows as a
sale with no lots, a link to the catalogue, until its last day has passed; a sale whose
lots were read after all is not shown twice, and its lots' heading takes the last day from here.
"""
import json, os, re, html, datetime, collections
import build_hubs as H

BASE, A, W, e = H.BASE, H.A, H.W, H.e
d = json.load(open("data/data.json", encoding="utf-8"))
UP = d.get("upcoming", [])
_today = datetime.date.today().isoformat()
_hand = json.load(open("data/sales_by_hand.json", encoding="utf-8")) if os.path.exists("data/sales_by_hand.json") else []
END = {(x["house"], x["date"]): x["end"] for x in _hand if x.get("end")}      # a sale over several days, its lots dated by the first
HAND = [x for x in _hand
        if (x.get("end") or x["date"]) >= _today
        and not any(u["h"] == x["house"] and x["date"] <= (u.get("d") or "") <= (x.get("end") or x["date"]) for u in UP)]
MUS_EN = H.MUSEUM_EN
lots_of = collections.defaultdict(list)
for w in W:
    if w.get("kind") == "auction": lots_of[w["a"]].append(w)

T = {"en": dict(file="upcoming", other="tulemas", h="Coming up at auction", site="Estonian Art Catalogue", art="a",
                lede="Every lot in the Estonian auction houses' coming sales by an artist in the catalogue, with the starting price as the house published it and the artist's record at auction beside it. Bids are not shown; the houses' own pages have them.",
                none="No coming sale has published its lots yet. The houses put their catalogues online two to four weeks before a sale; this page is refreshed every week.",
                start="starting price", rec="At auction: {n} lots, {s} sold{r}", rec0="First time at auction in the catalogue", prior="Same title before", unsold="unsold",
                lots="lots", lot1="lot", c_art="Artist", c_work="Work", c_price="Starting price", lot="Lot", hand="The catalogue is on the house's own site; its lots are not listed here.", cat="Catalogue", show="Show the lots ↓", hide="Hide the lots ↑", other_l="Eesti keeles", note="A record, not a valuation. Refreshed weekly.", month=["January","February","March","April","May","June","July","August","September","October","November","December"]),
     "et": dict(file="tulemas", other="upcoming", h="Tulemas oksjonil", site="Eesti Kunstikataloog", art="k",
                lede="Kõik Eesti oksjonimajade tulevate oksjonite partiid kataloogi kunstnikelt, alghind nii, nagu maja selle avaldas, ja kõrval kunstniku senine oksjonitulemus. Pakkumisi ei näidata; need on majade endi lehtedel.",
                none="Ükski tulev oksjon pole veel oma partiisid avaldanud. Majad panevad kataloogi üles kaks kuni neli nädalat enne oksjonit; see leht uueneb iga nädal.",
                start="alghind", rec="Oksjonil: {n} partiid, {s} müüdud{r}", rec0="Kataloogis esimest korda oksjonil", prior="Sama pealkiri varem", unsold="müümata",
                lots="partiid", lot1="partii", c_art="Kunstnik", c_work="Teos", c_price="Alghind", lot="Partii", hand="Kataloog on oksjonimaja enda lehel; selle partiisid siin ei loetleta.", cat="Kataloog", show="Näita partiisid ↓", hide="Peida partiid ↑", other_l="In English", note="Ülestähendus, mitte hinnang. Uueneb iga nädal.", month=["jaanuar","veebruar","märts","aprill","mai","juuni","juuli","august","september","oktoober","november","detsember"])}

CSS = (":root{--paper:#0B0C0E;--field:#15171A;--ink:#F1F2F4;--ink-soft:#C7CACE;--grey:#8B9098;--rule:#2B2E34;--rule-soft:#212429;"
       "--serif:'Newsreader','Iowan Old Style',Georgia,serif;--sans:'Archivo','Helvetica Neue',Arial,sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}"
       ":root[data-theme=light]{--paper:#FFFFFF;--field:#F5F6F8;--ink:#0B0C0E;--ink-soft:#33363B;--grey:#6C7178;--rule:#DCDFE3;--rule-soft:#EBEDF0}"
       "*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 var(--sans);-webkit-font-smoothing:antialiased}"
       ".pg{max-width:1080px;margin:0 auto;padding:22px 32px 40px}a{color:inherit}"
       ".top{display:flex;justify-content:space-between;align-items:baseline;gap:16px;padding-bottom:14px;border-bottom:1px solid var(--rule)}"
       ".wm{font-family:var(--serif);font-size:1.15rem;font-weight:500;text-decoration:none}.wm:hover{text-decoration:underline}"
       ".eb{font-family:var(--mono);font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}a.eb{text-decoration:none;border-bottom:1px solid var(--rule)}a.eb:hover{color:var(--ink)}"
       ".mast{padding:34px 0 22px;border-bottom:1px solid var(--ink)}"
       "h1{font-family:var(--serif);font-weight:500;font-size:2.6rem;line-height:1.05;letter-spacing:-.015em;margin:0 0 12px}"
       ".lede{margin:0;max-width:68ch;color:var(--ink-soft);font-size:.95rem}"
       ".sale{margin-top:28px;border-bottom:1px solid var(--rule)}.sale-h{display:block;padding-bottom:14px}"
       "summary.sale-h{list-style:none;cursor:pointer}summary.sale-h::-webkit-details-marker{display:none}summary.sale-h:hover h2{text-decoration:underline}"
       ".tog{margin-left:12px;font-family:var(--mono);font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);border-bottom:1px solid var(--rule)}"
       ".hd,details[open] .sh{display:none}details[open] .hd{display:inline}details[open]{padding-bottom:20px}"
       "h2{font-family:var(--serif);font-weight:500;font-size:1.6rem;line-height:1.1;margin:6px 0 4px}.sub{margin:0;color:var(--grey);font-size:.85rem}"
       "table{border-collapse:collapse;width:100%}"
       "th{font-family:var(--mono);font-weight:400;font-size:.66rem;letter-spacing:.13em;text-transform:uppercase;color:var(--grey);text-align:left;padding:0 16px 8px 0;border-bottom:1px solid var(--rule)}"
       "td{padding:13px 16px 13px 0;border-bottom:1px solid var(--rule-soft);vertical-align:top}"
       "td.a{width:34%}td.a a{font-family:var(--serif);font-size:1.08rem;text-decoration:none}td.a a:hover{text-decoration:underline}"
       "td.w i{font-family:var(--serif);font-size:1.02rem}"
       ".m{display:block;margin-top:3px;color:var(--grey);font-size:.78rem}td.a .m{font-family:var(--mono);font-size:.7rem;letter-spacing:.02em}"
       ".n{text-align:right;white-space:nowrap;padding-right:0}td.n b{display:block;font-family:var(--mono);font-weight:500;font-size:.95rem;font-variant-numeric:tabular-nums}"
       "a.lot{display:inline-block;margin-top:5px;font-family:var(--mono);font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--grey);text-decoration:none;border-bottom:1px solid var(--rule)}"
       "a.lot:hover{color:var(--ink);border-bottom-color:var(--ink)}"
       ".foot{margin-top:44px;padding-top:14px;border-top:1px solid var(--rule);color:var(--grey);font-size:.8rem}.foot a{color:var(--ink-soft)}"
       "@media(max-width:700px){.pg{padding:16px 16px 32px}h1{font-size:2rem}thead{display:none}"
       "tr{display:grid;grid-template-columns:1fr auto;gap:2px 14px;padding:12px 0;border-bottom:1px solid var(--rule-soft)}"
       "td{display:block;padding:0;border:0}td.a{width:auto}td.w{grid-column:1}td.n{grid-column:2;grid-row:1 / span 2}}")

fmt = lambda n, lang: f"{n:,}" if lang == "en" else f"{n:,}".replace(",", " ")
eur = lambda n, lang: "€" + fmt(n, lang)
house = lambda h, lang: MUS_EN.get(h, h) if lang == "en" else h
def day(dd, lang):
    if not dd: return ""
    y, m, *rest = str(dd).split("-")
    mo = T[lang]["month"][int(m) - 1]
    return (f"{int(rest[0])} {mo} {y}" if lang == "en" else f"{int(rest[0])}. {mo} {y}") if rest else f"{mo} {y}"
def days(a, b, lang):
    """13–15 November 2026 (13.–15. november 2026) within a month; both days in full otherwise"""
    if not b or b == a: return day(a, lang)
    if str(a)[:7] == str(b)[:7]: return (f"{int(str(a)[8:10])}–" if lang == "en" else f"{int(str(a)[8:10])}.–") + day(b, lang)
    return day(a, lang) + " – " + day(b, lang)
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
        secs = []
        for x in HAND:
            span = days(x["date"], x.get("end"), lang)
            nl = f' · {fmt(x["lots"], lang)} {t["lots"] if x["lots"] != 1 else t["lot1"]}' if x.get("lots") else ""
            cat = f' <a class="lot" href="{e(x["url"])}" rel="noopener">{t["cat"]} ↗</a>' if str(x.get("url") or "").startswith("http") else ""
            secs.append((x["date"], f'<section class="sale"><header class="sale-h"><span class="eb">{e(span)}</span>'
                         f'<h2>{e(x["sale"])}</h2><p class="sub">{e(house(x["house"], lang))}{nl}</p></header>'
                         f'<p class="sub">{e(t["hand"])}{cat}</p></section>'))
        for (dd, h, s), lots in groups.items():
            body = ""
            nl = f'{fmt(len(lots), lang)} {t["lots"] if len(lots) != 1 else t["lot1"]}'
            body += (f'<details class="sale"{" open" if len(groups) == 1 else ""}><summary class="sale-h"><span class="eb">{e(days(dd, END.get((h, dd)), lang))}</span>'
                     f'<h2>{e(s or house(h, lang))}</h2><p class="sub">{e(house(h, lang)) + " · " if s else ""}{nl}'
                     f'<span class="tog"><span class="sh">{t["show"]}</span><span class="hd">{t["hide"]}</span></span></p></summary>'
                     f'<table><thead><tr><th>{t["c_art"]}</th><th>{t["c_work"]}</th><th class="n">{t["c_price"]}</th></tr></thead><tbody>')
            for u in lots:
                sl = H.ARTIST_SLUG[u["a"]]
                prior = (f'<span class="m">{t["prior"]}: ' + " · ".join(f'{e(str(p[0])[:4])} {e(house(p[1], lang))} {eur(p[2], lang) if p[2] else t["unsold"]}' for p in u["pr"]) + "</span>") if u.get("pr") else ""
                lot = f'<a class="lot" href="{e(u["u"])}" rel="noopener">{t["lot"]} ↗</a>' if str(u.get("u") or "").startswith("http") else ""
                det = " · ".join(x for x in (u.get("tc"), u.get("dm")) if x)
                det = f'<span class="m">{e(det)}</span>' if det else ""
                body += (f'<tr><td class="a"><a href="{BASE}/{t["art"]}/{sl}">{e(A[u["a"]]["n"])}</a><span class="m">{e(record(u["a"], lang))}</span></td>'
                         f'<td class="w"><i>{e(u["t"])}</i>{", " + e(u["yl"]) if u.get("yl") else ""}{det}{prior}</td>'
                         f'<td class="n"><b>{eur(u["p"], lang) if u.get("p") else "–"}</b>{lot}</td></tr>')
            body += "</tbody></table></details>"
            secs.append((dd or "9", body))
        body = "".join(b for _, b in sorted(secs, key=lambda x: x[0]))
        me, other = f"{BASE}/{t['file']}", f"{BASE}/{t['other']}"
        n = len(UP)
        title = f'{t["h"]} – {fmt(n, lang)} {t["lots"]} · museaal.ee' if n else f'{t["h"]} · museaal.ee'
        page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{e(title)}</title><meta name="description" content="{e(t["lede"][:290])}">'
                f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
                '<link rel="stylesheet" href="/fonts/fonts.css">'
                f'<style>{CSS}</style>{H.GC}</head><body><div class="pg">'
                f'<div class="top"><a class="wm" href="{BASE}/{"" if lang == "en" else "#lang=et"}">{t["site"]}</a><a class="eb" href="{other}">{t["other_l"]}</a></div>'
                f'<header class="mast"><h1>{t["h"]}</h1><p class="lede">{e(t["lede"])}</p></header>'
                + (body or f'<p class="m">{e(t["none"])}</p>')
                + f'<footer class="foot">{e(t["note"])} {H.CONTACT[lang]}</footer></div></body></html>')
        open(f"site/{t['file']}.html", "w", encoding="utf-8").write(page)
        urls.append(me)
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  coming sales   {len(UP):,} lots in {len({(u.get('d'), u['h'], u['s']) for u in UP})} sale day(s), {len(HAND)} sale(s) by hand; upcoming.html, tulemas.html")

if __name__ == "__main__":
    main()
