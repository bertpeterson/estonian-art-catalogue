# -*- coding: utf-8 -*-
"""The finished sales: /past-sales and /moodunud-oksjonid, and a page for each sale under them.

Every auction lot in the catalogue (kind "auction") belongs to one sale: its house, its name
(an) and its date (ad). A house's lots of one name within a fortnight are one sale (Vaal's
run over two or three days); the same name a season later is another (EKO graafikaoksjon).
The index lists the sales, newest first, with how many lots, how many sold and the hammer
total; each sale's page lists its lots with the result as the house published it -- the
hammer price, sold without a price, sold after the sale, unsold -- and the starting price.
Osta Noort Kunsti publishes no results (anr): its lots say so and are never counted unsold.
Run after build_upcoming.py (it borrows that page's look and adds to the sitemap) and before csp.py.
"""
import json, os, datetime, collections
import build_hubs as H
import build_upcoming as U
import script_mark as SM  # the build's mark on its own inline scripts (csp.py)
import list_sync as LS

BASE, A, W, e = H.BASE, H.A, H.W, H.e
fmt, eur, surname, house = U.fmt, U.eur, U.surname, U.house
def days(a, b, lang):
    """the sale's first to last day, as the coming sales write it; a sale known only by its year (press records) by the year"""
    return a if len(a) == 4 else U.days(a, b if len(b) == len(a) else None, lang)

T = {"en": dict(file="past-sales", art="a", other="moodunud-oksjonid", h="Past sales", site="Estonian Art Catalogue",
                lede="Every finished sale of the Estonian auction houses in the catalogue, newest first: how many lots, how many sold and the hammer total, and for each sale its lots with the hammer prices as the house published them.",
                lots="lots", lot1="lot", sold="{s} sold", total="{t} hammer total", nores="results not published", up="Coming up at auction",
                c_art="Artist", c_work="Work", c_res="Result", start="starting price {p}", unsold="unsold", soldnp="sold, price not published",
                after="sold after the sale", nr="result not published", lot="Lot", sort="Sort", az="A–Z", price="Price",
                back="All past sales", other_l="Eesti keeles", note="A record, not a valuation. Hammer prices as the houses published them, without the buyer's premium. Refreshed weekly.",
                sale_d="{s}, {h}, {d}: {n} lots by Estonian artists with the hammer prices as the house published them."),
     "et": dict(file="moodunud-oksjonid", art="k", other="past-sales", h="Möödunud oksjonid", site="Eesti Kunstikataloog",
                lede="Kõik kataloogi Eesti oksjonimajade lõppenud oksjonid, uuemad eespool: mitu partiid, mitu müüdi ja haamrihindade summa, ning iga oksjoni partiid haamrihindadega nii, nagu maja need avaldas.",
                lots="partiid", lot1="partii", sold="{s} müüdud", total="haamrihinnad kokku {t}", nores="tulemused avaldamata", up="Tulemas oksjonil",
                c_art="Kunstnik", c_work="Teos", c_res="Tulemus", start="alghind {p}", unsold="müümata", soldnp="müüdud, hind avaldamata",
                after="müüdud järelmüügil", nr="tulemus avaldamata", lot="Partii", sort="Järjesta", az="A–Ü", price="Hind",
                back="Kõik möödunud oksjonid", other_l="In English", note="Ülestähendus, mitte hinnang. Haamrihinnad nii, nagu majad need avaldasid, ilma ostjatasuta. Uueneb iga nädal.",
                sale_d="{s}, {h}, {d}: {n} partiid Eesti kunstnikelt, haamrihinnad nii, nagu maja need avaldas.")}
for lang in T: T[lang]["month"] = U.T[lang]["month"]

CSS = U.CSS + (".yr{margin:56px 0 0;font-family:var(--serif);font-weight:500;font-size:2.2rem;line-height:1;letter-spacing:-.01em;color:var(--ink);border-bottom:2px solid var(--ink-soft);padding-bottom:10px}"
               "ul.sales{list-style:none;margin:0;padding:0}ul.sales li{display:grid;grid-template-columns:9.5em 1fr auto;gap:4px 18px;padding:12px 0;border-bottom:1px solid var(--rule-soft);align-items:baseline}"
               "ul.sales a{font-family:var(--serif);font-size:1.12rem;text-decoration:none}ul.sales a:hover{text-decoration:underline}"
               "ul.sales .n{font-family:var(--mono);font-size:.78rem;color:var(--ink-soft)}td.n .m{font-family:var(--mono);font-size:.68rem}"
               ".top .eb+.eb{margin-left:14px}"
               "@media(max-width:700px){ul.sales li{grid-template-columns:1fr}ul.sales .n{text-align:left}}")

# the sales: (house, name) runs of lots, split where the dates are more than a fortnight apart
def _d(s):
    s = str(s); return datetime.date(int(s[:4]), int(s[5:7] or 1) if len(s) >= 7 else 1, int(s[8:10]) if len(s) >= 10 else 1)
runs = collections.defaultdict(list)
for w in W:
    if w.get("kind") == "auction" and w.get("an"): runs[(H.val(w, "mu"), w["an"])].append(w)
SALES = []
for (h, an), ws in runs.items():
    ws.sort(key=lambda w: str(w["ad"]))
    cur = [ws[0]]
    for w in ws[1:]:
        if (_d(w["ad"]) - _d(cur[-1]["ad"])).days > 14: SALES.append((h, an, cur)); cur = []
        cur.append(w)
    SALES.append((h, an, cur))
SALES.sort(key=lambda x: (str(x[2][0]["ad"]), x[0], x[1]), reverse=True)

def name_of(h, an, ws):
    n = an.strip(" :")
    y = str(ws[0]["ad"])[:4]
    return n if y in n else f"{n} {y}"
SLUG, seen = {}, set()
for h, an, ws in SALES:
    nm = name_of(h, an, ws)
    s = H.slug(nm if h.split()[0].lower() in nm.lower() else f"{h} {nm}")
    k, i = s, 2
    while k in seen: k, i = f"{s}-{i}", i + 1
    seen.add(k); SLUG[id(ws)] = k

def result(w, t, lang):
    if w.get("anr"): return f'<span class="m">{t["nr"]}</span>'
    if w.get("ao") and w.get("ap"): return f'<b>{eur(w["ap"], lang)}</b>' + (f'<span class="m">{t["after"]}</span>' if w.get("aa") else "")
    if w.get("ao"): return f'<span class="m">{t["after"] if w.get("aa") else t["soldnp"]}</span>'
    return f'<span class="m">{t["unsold"]}</span>'

def summary(ws, t, lang):
    n = len(ws)
    out = f'{fmt(n, lang)} {t["lots"] if n != 1 else t["lot1"]}'
    if all(w.get("anr") for w in ws): return out + " · " + t["nores"]
    s = sum(1 for w in ws if w.get("ao"))
    tot = sum(w["ap"] for w in ws if w.get("ao") and w.get("ap"))
    return out + " · " + t["sold"].format(s=fmt(s, lang)) + (" · " + t["total"].format(t=eur(tot, lang)) if tot else "")

def head(lang, t, me, other, title, desc):
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><meta name="description" content="{e(desc[:290])}">'
            f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
            '<link rel="stylesheet" href="/fonts/fonts.css">'
            f'<style>{CSS}</style>{LS.TAG}{H.GC}</head><body><div class="pg">'
            f'<div class="top"><a class="wm" href="{BASE}/{"" if lang == "en" else "#lang=et"}">{t["site"]}</a>'
            f'<span><a class="eb" href="{BASE}/{U.T[lang]["file"]}">{t["up"]}</a><a class="eb" href="{other}">{t["other_l"]}</a></span></div>')

def foot(t, lang, js=""):
    return f'<footer class="foot">{e(t["note"])} {H.CONTACT[lang]}</footer></div>{js}</body></html>'

def main():
    urls = []
    for lang in ("en", "et"):
        t, o = T[lang], T["et" if lang == "en" else "en"]
        os.makedirs(f"site/{t['file']}", exist_ok=True)
        items, year = [], None
        for h, an, ws in SALES:
            sl, nm = SLUG[id(ws)], name_of(h, an, ws)
            span = days(str(ws[0]["ad"]), str(ws[-1]["ad"]), lang)
            me, other = f"{BASE}/{t['file']}/{sl}", f"{BASE}/{o['file']}/{sl}"
            lots = sorted(ws, key=lambda w: (surname(A[w["a"]]["n"]), w["t"]))
            rows = ""
            for i, w in enumerate(lots):
                det = " · ".join(x for x in ((H.val(w, "tc") if lang == "en" else H.val(w, "tce")) or H.val(w, "tc") or H.val(w, "tce"), w.get("dm")) if x)
                lot = f'<a class="lot" href="{e(w["url"])}" rel="noopener">{t["lot"]} ↗</a>' if str(w.get("url") or "").startswith("http") else ""
                st = f'<span class="m">{t["start"].format(p=eur(w["as"], lang))}</span>' if w.get("as") else ""
                p = w["ap"] if w.get("ao") and w.get("ap") else ""
                th = (f'<a class="th" href="{e(w["url"])}" rel="noopener"><img src="{e(H.imsrc(w["im"]))}" alt="" loading="lazy"></a>'
                      if w.get("im") and H.imsrc(w["im"]) and lot else "")
                rows += (f'<tr data-i="{i}" data-p="{p}"><td class="a"><a href="{BASE}/{t["art"]}/{H.ARTIST_SLUG[w["a"]]}">{e(A[w["a"]]["n"])}</a></td>'
                         f'<td class="w">{th}<i>{e(w["t"])}</i>{", " + e(w["yl"]) if w.get("yl") else ""}{f"<span class=m>{e(det)}</span>" if det else ""}</td>'
                         f'<td class="n">{result(w, t, lang)}{st}{lot}</td></tr>')
            sub = summary(ws, t, lang)
            page = (head(lang, t, me, other, f'{nm} – {t["c_res"].lower()} · museaal.ee',
                         t["sale_d"].format(s=nm, h=house(h, lang), d=span, n=fmt(len(ws), lang)))
                    + f'<header class="mast"><span class="eb">{e(span)} · <a class="eb" href="{BASE}/{t["file"]}">{t["back"]}</a></span>'
                    f'<h1>{e(nm)}</h1><p class="lede">{e(house(h, lang))} · {e(sub)}</p></header>'
                    f'<section class="sale"><div class="sort" style="margin-top:18px"><span class="eb">{t["sort"]}</span><button type="button" data-s="az" class="on">{t["az"]}</button>'
                    + (f'<button type="button" data-s="p" data-l="{t["price"]}">{t["price"]} ↓</button>' if any(w.get("ap") and w.get("ao") for w in ws) else "")
                    + f'</div><table><thead><tr><th>{t["c_art"]}</th><th>{t["c_work"]}</th><th class="n">{t["c_res"]}</th></tr></thead><tbody>{rows}</tbody></table></section>'
                    + foot(t, lang, f"{SM.OPEN}{U.JS}</script>"))
            open(f"site/{t['file']}/{sl}.html", "w", encoding="utf-8").write(page)
            urls.append(me)
            y = str(ws[0]["ad"])[:4]
            if y != year: items.append(f'{"</ul>" if year else ""}<h2 class="yr">{y}</h2><ul class="sales">'); year = y
            items.append(f'<li><span class="eb">{e(span)}</span><span><a href="{me}">{e(nm)}</a><span class="m">{e(house(h, lang))}</span></span><span class="n">{e(sub)}</span></li>')
        me, other = f"{BASE}/{t['file']}", f"{BASE}/{o['file']}"
        idx = (head(lang, t, me, other, f'{t["h"]} – {fmt(len(SALES), lang)} · museaal.ee', t["lede"])
               + f'<header class="mast"><h1>{t["h"]}</h1><p class="lede">{e(t["lede"])}</p></header>'
               + "".join(items) + ("</ul>" if items else "") + foot(t, lang))
        open(f"site/{t['file']}.html", "w", encoding="utf-8").write(idx)
        urls.append(me)
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  past sales     {len(SALES)} sales, {sum(len(x[2]) for x in SALES):,} lots; past-sales.html, moodunud-oksjonid.html and a page per sale")

if __name__ == "__main__":
    main()
