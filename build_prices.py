# -*- coding: utf-8 -*-
"""What an artist's works fetched at auction: /prices/<artist> and /hinnad/<artist>.

A page for every artist with four or more published results at the Estonian auction houses (the point from
which the site quotes the middle half of the hammer prices, build_ask.py). The search "<name> price" or
"<name> hind" met only the artist page, where the record at auction is one line; here it is the whole of it:
how many lots and how many sold, the middle half of the hammer prices and the highest, the same by medium and
by year, then every lot with its sale and result, newest first -- and what the galleries ask now, a link away.

A record, not a valuation: only what the houses published, nothing worked out about what a work should fetch.
Lots with no published result (anr, Osta Noort Kunsti) are left out. Pictures as on the past sales: only the
lots that carry one (data/picture_guard.py and the Images rule decide that, not this page).
Run after build_ask.py (it reads stock.json and the for-sale pages, and adds to the sitemap) and before csp.py.
"""
import json, os, datetime, collections, statistics
import build_hubs as H
import build_upcoming as U
import build_past_sales as P
import build_ask as BA
import script_mark as SM  # the build's mark on its own inline scripts (csp.py)

BASE, A, W, e = H.BASE, H.A, H.W, H.e
fmt, eur, house = U.fmt, U.eur, U.house
MIN = 4
MARK = "<!--prices-page-->"   # build_pages.py and build_ask.py leave it by an artist's record at auction; the link goes there
B = BA.BIT
CATS = [("photo", B["photo"]), ("sculpture", B["sculpture"]), ("print", B["print"]),
        ("paint", B["oil"] | B["acrylic"] | B["painting"] | B["mixed"]), ("paper", B["watercolour"] | B["drawing"])]

T = {"en": dict(dir="prices", art="a", sale="for-sale", site="Estonian Art Catalogue", other_l="Eesti keeles", past="Past sales",
                title="{name} prices – {n} auction results, {y}", h="{name}: prices at auction",
                lede="{n} lots by {name}{dates} at Estonian auction houses, {y}: {s} sold ({pct}%).",
                mid=" Half of the hammer prices were between {lo} and {hi}", rng=" Hammer prices {lo}–{hi}", one=" One hammer price, {lo}",
                top="; the highest, {p}, was for {t} at {h} in {y}.", pub=" Prices as the houses published them, without the buyer's premium.",
                by_m="By medium", by_y="By year", all="Every result", c_lots="Lots", c_sold="Sold", c_mid="Middle half", c_med="Median", c_top="Highest", c_y="Year",
                cats=dict(paint="Paintings", paper="Works on paper", print="Prints", sculpture="Sculpture", photo="Photographs", other="Other"),
                c_sale="Sale", c_work="Work", c_res="Result", newest="Newest", price="Price", lot="Lot",
                now="For sale now: {n} works at galleries{r} →", now1="For sale now: 1 work at a gallery{r} →", ask=", asking {r}",
                page="{name}: all works, museums, biography", link="All auction results and prices →",
                note="A record, not a valuation. Hammer prices as the houses published them, without the buyer's premium. Refreshed weekly."),
     "et": dict(dir="hinnad", art="k", sale="muugil", site="Eesti Kunstikataloog", other_l="In English", past="Möödunud oksjonid",
                title="{name}: hinnad – {n} oksjonitulemust, {y}", h="{name}: hinnad oksjonitel",
                lede="{name}{dates}: {n} teost Eesti oksjonitel, {y}; müüdud {s} ({pct}%).",
                mid=" Pooled haamrihindadest jäid vahemikku {lo}–{hi}", rng=" Haamrihinnad {lo}–{hi}", one=" Üks haamrihind, {lo}",
                top="; kõrgeim, {p}: {t} ({h}, {y}).", pub=" Hinnad nii, nagu majad need avaldasid, ilma ostjatasuta.",
                by_m="Tehnika järgi", by_y="Aasta järgi", all="Kõik tulemused", c_lots="Teoseid", c_sold="Müüdud", c_mid="Keskmine pool", c_med="Mediaan", c_top="Kõrgeim", c_y="Aasta",
                cats=dict(paint="Maalid", paper="Tööd paberil", print="Graafika", sculpture="Skulptuur", photo="Fotod", other="Muu"),
                c_sale="Oksjon", c_work="Teos", c_res="Tulemus", newest="Uuemad", price="Hind", lot="Partii",
                now="Müügil praegu: {n} teost galeriides{r} →", now1="Müügil praegu: 1 teos galeriis{r} →", ask=", {r}",
                page="{name}: kõik teosed, muuseumid, elulugu", link="Kõik oksjonitulemused ja hinnad →",
                note="Ülestähendus, mitte hinnang. Haamrihinnad nii, nagu majad need avaldasid, ilma ostjatasuta. Uueneb iga nädal.")}
for lang in T:
    for k in ("unsold", "soldnp", "after", "nr", "start"): T[lang][k] = P.T[lang][k]

CSS = P.CSS + ("h2.sec{font-family:var(--serif);font-weight:500;font-size:1.45rem;margin:44px 0 8px}"
               ".fg{display:grid;grid-template-columns:minmax(7em,1.3fr) repeat(4,minmax(0,1fr));gap:2px 18px;padding:9px 0;border-bottom:1px solid var(--rule-soft);"
               "font-size:.9rem;font-variant-numeric:tabular-nums;align-items:baseline}.fg.y{grid-template-columns:minmax(7em,1.3fr) repeat(3,minmax(0,1fr)) minmax(0,1fr)}"
               ".fg.hd{font-family:var(--mono);font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;color:var(--grey);border-bottom-color:var(--ink-soft)}"
               ".fg span+span{text-align:right}.fg b{font-weight:500}.figs{max-width:760px}"
               ".now{margin:26px 0 0;font-size:1rem}.now a{font-family:var(--serif);font-size:1.1rem}"
               "td.a .m a{color:inherit}"
               "@media(max-width:700px){.fg{grid-template-columns:1.2fr 1fr 1fr;font-size:.84rem}.fg.y{grid-template-columns:1.2fr 1fr 1fr 1fr}.fg:not(.y) span:nth-child(n+4){grid-row:2}"
               ".fg:not(.y) span:nth-child(4){grid-column:2}.fg:not(.y) span:nth-child(5){grid-column:3}}")

def cat(w):
    m = BA.media_of(BA.kind_of(w), " ".join(filter(None, (H.val(w, "tce"), H.val(w, "tc")))))
    return next((k for k, bits in CATS if m & bits), "other")

def mid(ps):
    """the middle half of the prices, from four up (as build_ask.py's record at auction); else None"""
    ps = sorted(ps)
    return (ps[len(ps) // 4], ps[(3 * len(ps)) // 4]) if len(ps) >= 4 else None

def main():
    lots = collections.defaultdict(list)
    for w in W:
        if w.get("kind") == "auction" and w.get("ad"): lots[w["a"]].append(w)
    sale_of = {id(w): (P.SLUG[id(ws)], P.name_of(h, an, ws)) for h, an, ws in P.SALES for w in ws}
    stock = {}
    if os.path.exists("site/data/stock.json"):
        d = json.load(open("site/data/stock.json", encoding="utf-8"))
        for w in d["works"]: stock.setdefault(d["artists"][w[1]][1], []).append(w[8])
    urls, n_pages = [], 0
    for ai, all_ in lots.items():
        sl = H.ARTIST_SLUG.get(ai)
        if not sl: continue
        L = sorted((w for w in all_ if not w.get("anr")), key=lambda w: str(w["ad"]), reverse=True)
        ok = len(L) >= MIN
        name = A[ai]["n"]
        if ok:
            life = A[ai].get("l") or ["", ""]
            dates = f" ({life[0]}–{life[1]})" if life[0] or life[1] else ""
            ys = sorted(str(w["ad"])[:4] for w in L)
            span = ys[0] if ys[0] == ys[-1] else f"{ys[0]}–{ys[-1]}"
            sold = [w for w in L if w.get("ao")]
            ps = sorted(w["ap"] for w in sold if w.get("ap"))
            best = max((w for w in sold if w.get("ap")), key=lambda w: w["ap"], default=None)
            by_c, by_y = collections.defaultdict(list), collections.defaultdict(list)
            for w in L: by_c[cat(w)].append(w); by_y[str(w["ad"])[:4]].append(w)
            mine = sorted(p for p in stock.get(sl, []))
        for lang in ("en", "et"):
            t, ol = T[lang], "et" if lang == "en" else "en"
            me, other = f"{BASE}/{t['dir']}/{sl}", f"{BASE}/{T[ol]['dir']}/{sl}"
            apage = f"{BASE}/{t['art']}/{sl}"
            # the way here from the artist's page and from their for-sale page; no page, no link
            for p in (f"site/{t['art']}/{sl}.html", f"site/{t['sale']}/{sl}.html"):
                if os.path.exists(p):
                    s = open(p, encoding="utf-8").read()
                    if MARK in s:
                        open(p, "w", encoding="utf-8").write(s.replace(MARK, f'<p><a class="cta" href="{me}">{e(t["link"])}</a></p>' if ok else ""))
            if not ok: continue
            m_ = mid(ps)
            lede = t["lede"].format(n=fmt(len(L), lang), name=name, dates=dates, y=span, s=fmt(len(sold), lang), pct=round(100 * len(sold) / len(L)))
            if ps:
                lede += (t["mid"].format(lo=eur(m_[0], lang), hi=eur(m_[1], lang)) if m_ and m_[0] != m_[1] else
                         t["rng"].format(lo=eur(ps[0], lang), hi=eur(ps[-1], lang)) if ps[0] != ps[-1] else t["one"].format(lo=eur(ps[0], lang)))
                lede += t["top"].format(p=eur(best["ap"], lang), t=best.get("t") or "—", h=house(H.val(best, "mu") or "", lang), y=str(best["ad"])[:4]) if len(ps) > 1 else "."
            lede += t["pub"]
            def fig(label, ws, year=False):
                pr = sorted(w["ap"] for w in ws if w.get("ao") and w.get("ap"))
                q = mid(pr)
                cells = [fmt(len(ws), lang), fmt(sum(1 for w in ws if w.get("ao")), lang)]
                cells += ([eur(round(statistics.median(pr)), lang) if pr else "–"] if year else [f"{eur(q[0], lang)}–{eur(q[1], lang)}" if q else "–"])
                cells += [eur(pr[-1], lang) if pr else "–"]
                return f'<div class="fg{" y" if year else ""}"><span><b>{e(label)}</b></span>' + "".join(f"<span>{e(c)}</span>" for c in cells) + "</div>"
            hd = lambda first, third, y="": (f'<div class="fg hd{y}"><span>{first}</span><span>{t["c_lots"]}</span><span>{t["c_sold"]}</span>'
                                             f'<span>{third}</span><span>{t["c_top"]}</span></div>')
            order = ["paint", "paper", "print", "sculpture", "photo", "other"]
            figs_m = (f'<h2 class="sec">{t["by_m"]}</h2><div class="figs">{hd("", t["c_mid"])}'
                      + "".join(fig(t["cats"][k], by_c[k]) for k in order if by_c.get(k)) + "</div>") if len(by_c) > 1 else ""
            figs_y = (f'<h2 class="sec">{t["by_y"]}</h2><div class="figs">{hd(t["c_y"], t["c_med"], " y")}'
                      + "".join(fig(y, by_y[y], True) for y in sorted(by_y, reverse=True)) + "</div>") if len(by_y) > 1 else ""
            rows = ""
            for i, w in enumerate(L):
                det = " · ".join(x for x in ((H.val(w, "tc") if lang == "en" else H.val(w, "tce")) or H.val(w, "tc") or H.val(w, "tce"), w.get("dm")) if x)
                lot = f'<a class="lot" href="{e(w["url"])}" rel="noopener">{t["lot"]} ↗</a>' if str(w.get("url") or "").startswith("http") else ""
                st = f'<span class="m">{t["start"].format(p=eur(w["as"], lang))}</span>' if w.get("as") else ""
                p = w["ap"] if w.get("ao") and w.get("ap") else ""
                th = (f'<a class="th" href="{e(w["url"])}" rel="noopener"><img src="{e(H.imsrc(w["im"]))}" alt="" loading="lazy"></a>'
                      if w.get("im") and H.imsrc(w["im"]) and lot else "")
                ssl, snm = sale_of.get(id(w), ("", w.get("an") or ""))
                sale = f'<a href="{BASE}/{P.T[lang]["file"]}/{ssl}">{e(snm)}</a>' if ssl else e(snm)
                rows += (f'<tr data-i="{i}" data-p="{p}"><td class="a">{sale}<span class="m">{e(house(H.val(w, "mu") or "", lang))} · {e(P.days(str(w["ad"]), "", lang))}</span></td>'
                         f'<td class="w">{th}<i>{e(w.get("t") or "—")}</i>{", " + e(str(w["yl"])) if w.get("yl") else ""}{f"<span class=m>{e(det)}</span>" if det else ""}</td>'
                         f'<td class="n">{P.result(w, t, lang)}{st}{lot}</td></tr>')
            now = ""
            if mine:
                pr = [p for p in mine if p]
                r = (eur(pr[0], lang) if pr and pr[0] == pr[-1] else f"{eur(pr[0], lang)}–{eur(pr[-1], lang)}" if pr else "")
                to = f"{BASE}/{t['sale']}/{sl}" if os.path.exists(f"site/{t['sale']}/{sl}.html") else apage
                txt = t["now1" if len(mine) == 1 else "now"].format(n=len(mine), r=t["ask"].format(r=r) if r else "")
                now = f'<p class="now"><a href="{to}">{e(txt)}</a></p>'
            title = t["title"].format(name=name, n=fmt(len(L), lang), y=span)
            ld = H.ldjson({"@context": "https://schema.org", "@type": "WebPage", "name": t["h"].format(name=name), "url": me, "inLanguage": lang,
                           "about": {"@type": "Person", "name": name, "url": apage}})
            page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                    f'<title>{e(title)} · museaal.ee</title><meta name="description" content="{e(lede[:290])}">'
                    f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{ol}" href="{other}">'
                    f'<script type="application/ld+json">{ld}</script>'
                    '<link rel="stylesheet" href="/fonts/fonts.css">'
                    f'<style>{CSS}</style>{H.GC}</head><body><div class="pg">'
                    f'<div class="top"><a class="wm" href="{BASE}/{"" if lang == "en" else "#lang=et"}">{t["site"]}</a>'
                    f'<span><a class="eb" href="{BASE}/{P.T[lang]["file"]}">{t["past"]}</a><a class="eb" href="{other}">{t["other_l"]}</a></span></div>'
                    f'<header class="mast"><span class="eb"><a class="eb" href="{apage}">{e(t["page"].format(name=name))}</a></span>'
                    f'<h1>{e(t["h"].format(name=name))}</h1><p class="lede">{e(lede)}</p>{now}</header>'
                    + figs_m + figs_y
                    + f'<h2 class="sec">{t["all"]}</h2><section class="sale"><div class="sort"><span class="eb">{P.T[lang]["sort"]}</span>'
                    f'<button type="button" data-s="az" class="on">{t["newest"]}</button>'
                    + (f'<button type="button" data-s="p" data-l="{t["price"]}">{t["price"]} ↓</button>' if ps else "")
                    + f'</div><table><thead><tr><th>{t["c_sale"]}</th><th>{t["c_work"]}</th><th class="n">{t["c_res"]}</th></tr></thead><tbody>{rows}</tbody></table></section>'
                    + f'<footer class="foot">{e(t["note"])} {H.CONTACT[lang]}</footer></div>{SM.OPEN}{U.JS}</script></body></html>')
            os.makedirs(f"site/{t['dir']}", exist_ok=True)
            open(f"site/{t['dir']}/{sl}.html", "w", encoding="utf-8").write(page)
            urls.append(me)
        n_pages += ok
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  prices         {n_pages:,} artists with a page of their results at auction ({MIN} or more), both languages")

if __name__ == "__main__":
    main()
