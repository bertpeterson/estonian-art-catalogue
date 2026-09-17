# -*- coding: utf-8 -*-
"""site/stats.html -- the catalogue in figures, built from data/data.json.

A plain page in the style of the artist pages: what the catalogue holds by kind and
by medium; the auction record by house and by year; the artists most sold at
auction by lots and by the sum of their hammer prices; the highest results; how
much of each house's offering finds a buyer. Every figure is computed here from
the same data the app loads, so the page and the app never disagree.
"""
import json, os, html, datetime, collections, re, unicodedata
GC = '<script data-goatcounter="https://museaal.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'   # GoatCounter: a page-view count, no cookies

SRC, OUT = "data/data.json", "site/stats.html"
d = json.load(open(SRC, encoding="utf-8"))
W, A, V = d["works"], d["artists"], d["vocab"]
e = html.escape
val = lambda w, f: (V[f][w[f]] if isinstance(w.get(f), int) and f in V else w.get(f))
kind = lambda w: w.get("kind") or "held"
fmt = lambda n: f"{n:,}"
eur = lambda n: f"€{n:,}"
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s))

# ---- holdings ----
by_kind = collections.Counter(kind(w) for w in W)
KIND = {"held": "In museum collections", "shown": "Exhibited", "gallery": "For sale in galleries", "sold": "Past gallery listings", "auction": "Auction lots", "known": "Known works"}
med = collections.defaultdict(collections.Counter)
for w in W: med[val(w, "e") or "Other"][kind(w)] += 1
# the long tail of museum object types (Nõu, Kauss, Laegas...) folds into Other
med_rows = sorted(med.items(), key=lambda kv: -sum(kv[1].values()))
main, other = [], collections.Counter()
for m, c in med_rows:
    if sum(c.values()) >= 100 and m != "Other": main.append((m, c))
    else: other.update(c)
med_rows = main + ([("Other", other)] if other else [])

# ---- auctions ----
lots = [w for w in W if kind(w) == "auction"]
sold = [w for w in lots if w.get("ao")]
priced = [w for w in sold if w.get("ap")]
total = sum(w["ap"] for w in priced)
house = collections.defaultdict(lambda: {"lots": 0, "sold": 0, "sum": 0, "first": "9999", "last": "0000"})
for w in lots:
    h = house[val(w, "mu")]; h["lots"] += 1
    if w.get("ao"): h["sold"] += 1; h["sum"] += w.get("ap") or 0
    y = str(w.get("ad", ""))[:4]
    if y: h["first"] = min(h["first"], y); h["last"] = max(h["last"], y)
year = collections.defaultdict(lambda: {"lots": 0, "sold": 0, "sum": 0})
for w in lots:
    y = str(w.get("ad", ""))[:4]
    if not y: continue
    year[y]["lots"] += 1
    if w.get("ao"): year[y]["sold"] += 1; year[y]["sum"] += w.get("ap") or 0
by_art = collections.defaultdict(lambda: {"lots": 0, "sold": 0, "sum": 0, "top": 0})
for w in lots:
    a = by_art[w["a"]]; a["lots"] += 1
    if w.get("ao"): a["sold"] += 1; a["sum"] += w.get("ap") or 0; a["top"] = max(a["top"], w.get("ap") or 0)
top_by_lots = sorted(by_art.items(), key=lambda kv: (-kv[1]["sold"], -kv[1]["sum"]))[:25]
top_by_sum = sorted(by_art.items(), key=lambda kv: -kv[1]["sum"])[:25]
top_results = sorted(priced, key=lambda w: -w["ap"])[:25]
auc_med = collections.defaultdict(lambda: {"lots": 0, "sold": 0, "sum": 0})
for w in lots:
    m = auc_med[val(w, "e") or "Other"]; m["lots"] += 1
    if w.get("ao"): m["sold"] += 1; m["sum"] += w.get("ap") or 0

def hbars(rows, fmtv=fmt, width=420, bar=14, gap=6, label_w=150):
    """Horizontal bars, one series: label at left, value at the bar's end. Ink-coloured
    marks on the page surface, so they read in both colour schemes."""
    if not rows: return ""
    mx = max(v for _, v in rows) or 1
    h = len(rows) * (bar + gap)
    out = [f'<svg class="hb" viewBox="0 0 {width} {h}" width="{width}" height="{h}" role="img">']
    for k, (lab, v) in enumerate(rows):
        y = k * (bar + gap); w = max(1, round((width - label_w - 70) * v / mx))
        out.append(f'<text x="{label_w - 8}" y="{y + bar - 3}" text-anchor="end" class="hl">{e(str(lab))[:22]}</text>'
                   f'<rect x="{label_w}" y="{y}" width="{w}" height="{bar}" rx="1" class="hr"><title>{e(str(lab))}: {e(fmtv(v))}</title></rect>'
                   f'<text x="{label_w + w + 6}" y="{y + bar - 3}" class="hv">{e(fmtv(v))}</text>')
    out.append("</svg>")
    return "".join(out)
def cellbar(v, mx):
    return f'<span class="cb"><i style="width:{max(1, round(100 * v / mx)) if mx else 0}%"></i></span>'
def artist_link(i):
    return f'<a href="a/{slug(A[i]["n"]) or "artist-" + str(i)}.html">{e(A[i]["n"])}</a>'
def pct(a, b): return f"{a / b * 100:.0f}%" if b else "—"
def table(head, rows):
    th = "".join(f"<th{' class=n' if i else ''}>{e(h)}</th>" for i, h in enumerate(head))
    return f"<table><thead><tr>{th}</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td{' class=n' if i else ''}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows) + "</tbody></table>"

CSS = ("body{margin:0;padding:28px;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fff;color:#111;max-width:940px}"
       "@media(prefers-color-scheme:dark){body{background:#0b0c0e;color:#f1f2f4}a{color:#9ec5ff}th,td{border-color:#2b2e34!important}.m{color:#8b9098!important}}"
       "h1{font-weight:500;font-size:2rem;margin:0 0 4px}h2{font-weight:500;font-size:1.25rem;margin:36px 0 8px}"
       ".m{color:#666;font-size:.9rem}nav{font-size:.9rem;margin-bottom:22px}a{color:inherit}"
       "table{border-collapse:collapse;width:100%;font-size:.9rem;margin-top:8px}th,td{text-align:left;padding:5px 8px;border-bottom:1px solid #e3e3e3;vertical-align:top}"
       "th{font-weight:500;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:#666}.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}"
       ".big{font-size:2rem;font-weight:500;line-height:1.1}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:18px;margin:18px 0 6px}"
       ".sec{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 32px;align-items:start}.sec table{margin-top:0}"
       "@media(max-width:820px){.sec{grid-template-columns:1fr}.hb{width:100%;height:auto}}"
       ".hb{display:block;margin-top:8px;overflow:visible}.hb .hr{fill:#111}.hb .hl,.hb .hv{font-size:11px;fill:#666}.hb .hv{font-variant-numeric:tabular-nums}"
       "@media(prefers-color-scheme:dark){.hb .hr{fill:#f1f2f4}.hb .hl,.hb .hv{fill:#8b9098}}"
       ".cb{display:inline-block;width:110px;height:8px;background:#e8e8e8;vertical-align:middle}.cb i{display:block;height:100%;background:#111}"
       "@media(prefers-color-scheme:dark){.cb{background:#2b2e34}.cb i{background:#f1f2f4}}"
       ".dc{display:inline-flex;align-items:flex-end;gap:1px;height:22px}.dc i{display:block;width:4px;background:#111}@media(prefers-color-scheme:dark){.dc i{background:#f1f2f4}}")

today = datetime.date.today().isoformat()
ET = {'The catalogue in figures': 'Kataloog arvudes', 'Estonian Art Catalogue': 'Eesti Kunstikataloog', 'What museaal.ee holds by kind and medium, and the Estonian auction record by house, year and artist.': 'Mida museaal.ee sisaldab liigi ja tehnika kaupa, ning Eesti oksjonitulemused maja, aasta ja kunstniku kaupa.', 'Computed from the data as built on': 'Arvutatud andmetest seisuga', "Prices are hammer prices as the houses published them; a gallery's asking prices are never taken.": 'Hinnad on haamrihinnad nii, nagu majad need avaldasid; galeriide küsitud hindu ei koguta.', 'By medium': 'Liigi kaupa', 'Medium': 'Liik', 'Museums': 'Muuseumid', 'For sale': 'Müügil', 'Past listings': 'Varasemad pakkumised', 'Auction lots': 'Oksjonipartiid', 'All': 'Kokku', 'The collections': 'Kogud', 'Every holder with a hundred works or more; pictures are shown for public-domain works only.': 'Iga hoidja, kellel on vähemalt sada teost; pilte näidatakse ainult autoriõiguse alt vabade teoste puhul.', 'Holder': 'Hoidja', 'Works': 'Teoseid', 'Dated': 'Dateeritud', 'With a picture': 'Pildiga', 'Main media': 'Peamised liigid', 'Per decade': 'Kümnendi kaupa', 'By decade': 'Kümnendi kaupa', 'Decade': 'Kümnend', 'Museum works': 'Muuseumiteoseid', 'Dated works in the catalogue': 'Dateeritud teoseid kataloogis', 'The auction record': 'Oksjonitulemused', 'lots': 'partiid', 'sold': 'müüdud', 'hammer prices in all,': 'haamrihindu kokku,', 'average · median': 'keskmine · mediaan', 'By house': 'Maja kaupa', 'House': 'Maja', 'Sales': 'Oksjoneid', 'Lots': 'Partiisid', 'Sold': 'Müüdud', 'Sell-through': 'Müügiosakaal', 'Hammer total': 'Haamrihinnad kokku', 'By year': 'Aasta kaupa', 'Year': 'Aasta', 'Average': 'Keskmine', 'Hammer total by year': 'Haamrihinnad kokku aasta kaupa', 'Lots by year': 'Partiisid aasta kaupa', 'By medium at auction': 'Liigi kaupa oksjonil', 'Artists most sold at auction': 'Enim müüdud kunstnikud oksjonil', 'By lots sold.': 'Müüdud partiide järgi.', 'Artist': 'Kunstnik', 'Of lots': 'Partiidest', 'Highest': 'Kõrgeim', 'Artists by the sum of their hammer prices': 'Kunstnikud haamrihindade summa järgi', 'Highest results': 'Kõrgeimad tulemused', 'Work': 'Teos', 'Sale': 'Oksjon', 'Hammer price': 'Haamrihind', 'Auction results as Haus Galerii, Vernissage, Allee galerii, Vaal galerii, E-Kunstisalong and Eesti Kunsti Oksjonid published them, plus a few earlier record prices as the press reported them; kroon-era prices in euro at the fixed rate. A record, not a valuation.': 'Oksjonitulemused nii, nagu Haus Galerii, Vernissage, Allee galerii, Vaal galerii, E-Kunstisalong ja Eesti Kunsti Oksjonid need avaldasid, lisaks mõni varasem rekordhind ajakirjanduse järgi; kroonihinnad eurodes fikseeritud kursiga. Ülestähendus, mitte hinnang.', 'Full catalogue': 'Kogu kataloog', 'Artists A–Z': 'Kunstnikud A–Ü', 'In museum collections': 'Muuseumikogudes', 'Exhibited': 'Eksponeeritud', 'For sale in galleries': 'Galeriides müügil', 'Past gallery listings': 'Varasemad galeriipakkumised', 'Known works': 'Teadaolevad teosed'}
I18N = json.load(open("i18n.json", encoding="utf-8")) if os.path.exists("i18n.json") else {}
MED_ET, MUS_EN = I18N.get("MEDIUM_ET", {}), I18N.get("MUSEUM_EN", {})
PRICES_NOTE = "Prices are hammer prices as the houses published them; a gallery's asking prices are never taken."
def render(lang):
    _ = (lambda s: ET.get(s, s)) if lang == "et" else (lambda s: s)
    medl = (lambda m: MED_ET.get(m, m)) if lang == "et" else (lambda m: m)
    musl = (lambda h: h) if lang == "et" else (lambda h: MUS_EN.get(h, h))
    decl = (lambda d: f"{d}ndad") if lang == "et" else (lambda d: f"{d}s")
    OUTNAME = "stats.html" if lang == "en" else "stats-et.html"
    HOME = "./" if lang == "en" else "./#lang=et"
    OTHER, OTHERLAB = ("stats-et.html", "Eesti keeles") if lang == "en" else ("stats.html", "In English")
    parts = []
    parts = [f"<!doctype html><html lang=\"{lang}\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
             f"<title>The catalogue in figures — Estonian Art Catalogue</title>"
             f"<meta name=\"description\" content=\"What museaal.ee holds by kind and medium, and the Estonian auction record by house, year and artist.\">"
             f"<link rel=\"canonical\" href=\"https://museaal.ee/{OUTNAME}\"><style>{CSS}</style>{GC}</head><body>"
             f"<nav><a href=\"./\">{_('Estonian Art Catalogue')}</a> › {_('The catalogue in figures')}</nav>"
             f"<h1>{_('The catalogue in figures')}</h1><p class=\"m\">{_('Computed from the data as built on')} {today}. {_(PRICES_NOTE)}</p>"]

    parts.append('<div class="grid">' + "".join(f'<div><div class="big">{fmt(n)}</div><div class="m">{e(_(KIND.get(k, k)))}</div></div>'
                 for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1])) + "</div>")
    parts.append(f"<h2>{_('By medium')}</h2><div class=\"sec\">" + table([_("Medium"), _("Museums"), _("For sale"), _("Past listings"), _("Auction lots"), _("All")],
                 [[e(medl(m)), fmt(c["held"] + c.get("shown", 0)), fmt(c["gallery"]), fmt(c["sold"]), fmt(c["auction"]), fmt(sum(c.values()))] for m, c in med_rows])
                 + hbars([(medl(m), sum(c.values())) for m, c in med_rows], width=360, label_w=110) + "</div>")

    # ---- the collections: works per holder, per decade, per medium ----
    held = [w for w in W if kind(w) in ("held", "shown") and val(w, "s") != "gallery"]
    by_holder = collections.Counter(val(w, "mu") for w in held)
    holders = [h for h, n in by_holder.most_common() if n >= 100]
    hold_dec = collections.defaultdict(collections.Counter); hold_med = collections.defaultdict(collections.Counter); hold_pic = collections.Counter(); hold_dated = collections.Counter()
    for w in held:
        h = val(w, "mu"); hold_med[h][val(w, "e") or "Other"] += 1
        if w.get("y"): hold_dec[h][w["y"] // 10 * 10] += 1; hold_dated[h] += 1
        if w.get("im"): hold_pic[h] += 1
    DECS = list(range(1800, 2030, 10))
    def decrow(h):
        c = hold_dec[h]; mx = max(c.values()) if c else 1
        return "".join(f'<i title="{d}s: {c.get(d, 0)}" style="height:{max(1, round(22 * c.get(d, 0) / mx)) if c.get(d, 0) else 0}px"></i>' for d in DECS)
    parts.append(f"<h2>{_('The collections')}</h2><p class=\"m\">{_('Every holder with a hundred works or more; pictures are shown for public-domain works only.')}</p>"
                 + table([_("Holder"), _("Works"), _("Dated"), _("With a picture"), _("Main media")],
                 [[e(musl(h)), fmt(by_holder[h]), pct(hold_dated[h], by_holder[h]), fmt(hold_pic[h]),
                   e(" · ".join(f"{medl(m)} {fmt(n)}" for m, n in hold_med[h].most_common(3)))] for h in holders]))
    parts.append(f"<h2>{_('By decade')}</h2><div class=\"sec\">" + table([_("Decade"), _("Museum works"), _("Dated works in the catalogue"), _("With a picture")],
                 [[decl(d), fmt(sum(hold_dec[h].get(d, 0) for h in hold_dec)), fmt(sum(1 for w in W if w.get("y") and w["y"] // 10 * 10 == d)), fmt(sum(1 for w in held if w.get("im") and w.get("y") and w["y"] // 10 * 10 == d))] for d in DECS])
                 + hbars([(decl(d), sum(hold_dec[h].get(d, 0) for h in hold_dec)) for d in DECS], width=360, label_w=70) + "</div>")

    parts.append(f"<h2>{_('The auction record')}</h2><div class=\"grid\">"
                 f"<div><div class=\"big\">{fmt(len(lots))}</div><div class=\"m\">{_('lots')}</div></div>"
                 f"<div><div class=\"big\">{fmt(len(sold))}</div><div class=\"m\">{_('sold')} · {pct(len(sold), len(lots))}</div></div>"
                 f"<div><div class=\"big\">{eur(total)}</div><div class=\"m\">{_('hammer prices in all,')} {fmt(len(priced))} {_('lots')}</div></div>"
                 f"<div><div class=\"big\">{eur(round(total / len(priced)))}</div><div class=\"m\">{_('average · median')} {eur(sorted(w['ap'] for w in priced)[len(priced) // 2])}</div></div></div>")
    hs = sorted(house.items(), key=lambda kv: -kv[1]["sum"])
    parts.append(f"<h2>{_('By house')}</h2><div class=\"sec\">" + table([_("House"), _("Sales"), _("Lots"), _("Sold"), _("Sell-through"), _("Hammer total")],
                 [[e(h), f"{v['first']}–{v['last']}", fmt(v["lots"]), fmt(v["sold"]), pct(v["sold"], v["lots"]), eur(v["sum"])] for h, v in hs])
                 + "<div>" + hbars([(h, v["sum"]) for h, v in hs], fmtv=lambda n: f"€{n / 1e6:.1f} M", width=360, label_w=140)
                 + hbars([(h, v["lots"]) for h, v in hs], width=360, label_w=140) + "</div></div>")
    ys = sorted(year.items())
    parts.append(f"<h2>{_('By year')}</h2><div class=\"sec\">" + table([_("Year"), _("Lots"), _("Sold"), _("Sell-through"), _("Hammer total"), _("Average")],
                 [[y, fmt(v["lots"]), fmt(v["sold"]), pct(v["sold"], v["lots"]), eur(v["sum"]), eur(round(v["sum"] / v["sold"])) if v["sold"] else "—"]
                  for y, v in reversed(ys)])
                 + f"<div><p class=\"m\" style=\"margin:8px 0 0\">{_('Hammer total by year')}</p>" + hbars([(y, v["sum"]) for y, v in reversed(ys)], fmtv=lambda n: f"€{n / 1e6:.1f} M", width=360, bar=10, gap=3, label_w=50)
                 + f"<p class=\"m\" style=\"margin:14px 0 0\">{_('Lots by year')}</p>" + hbars([(y, v["lots"]) for y, v in reversed(ys)], width=360, bar=10, gap=3, label_w=50) + "</div></div>")
    ams = sorted(auc_med.items(), key=lambda kv: -kv[1]["sum"])
    parts.append(f"<h2>{_('By medium at auction')}</h2><div class=\"sec\">" + table([_("Medium"), _("Lots"), _("Sold"), _("Sell-through"), _("Hammer total"), _("Average")],
                 [[e(m), fmt(v["lots"]), fmt(v["sold"]), pct(v["sold"], v["lots"]), eur(v["sum"]), eur(round(v["sum"] / v["sold"])) if v["sold"] else "—"] for m, v in ams])
                 + hbars([(medl(m), v["sum"]) for m, v in ams], fmtv=lambda n: f"€{n / 1e6:.1f} M", width=360, label_w=100) + "</div>")
    mx = top_by_lots[0][1]["sold"] if top_by_lots else 1
    parts.append(f"<h2>{_('Artists most sold at auction')}</h2><p class=\"m\">{_('By lots sold.')}</p>" + table(["", _("Artist"), "", _("Sold"), _("Of lots"), _("Hammer total"), _("Highest")],
                 [[str(k + 1), artist_link(i), cellbar(v["sold"], mx), fmt(v["sold"]), fmt(v["lots"]), eur(v["sum"]), eur(v["top"])] for k, (i, v) in enumerate(top_by_lots)]))
    mx = top_by_sum[0][1]["sum"] if top_by_sum else 1
    parts.append(f"<h2>{_('Artists by the sum of their hammer prices')}</h2>" + table(["", _("Artist"), "", _("Hammer total"), _("Sold"), _("Of lots"), _("Average"), _("Highest")],
                 [[str(k + 1), artist_link(i), cellbar(v["sum"], mx), eur(v["sum"]), fmt(v["sold"]), fmt(v["lots"]), eur(round(v["sum"] / v["sold"])) if v["sold"] else "—", eur(v["top"])]
                  for k, (i, v) in enumerate(top_by_sum)]))
    mx = top_results[0]["ap"] if top_results else 1
    parts.append(f"<h2>{_('Highest results')}</h2>" + table(["", _("Work"), _("Artist"), _("House"), _("Sale"), "", _("Hammer price")],
                 [[str(k + 1), f"<em>{e(w['t'])}</em>" + (f" <span class=m>{e(str(w.get('yl') or w.get('y') or ''))}</span>" if (w.get('yl') or w.get('y')) else ""),
                   artist_link(w["a"]), e(musl(val(w, "mu"))), e(str(w.get("ad", ""))[:4]), cellbar(w["ap"], mx), eur(w["ap"])] for k, w in enumerate(top_results)]))
    parts.append(f"<p class=\"m\" style=\"margin-top:36px\">Auction results as Haus Galerii, Vernissage, Allee galerii, Vaal galerii, E-Kunstisalong and Eesti Kunsti Oksjonid published them, plus a few earlier record prices as the press reported them; kroon-era prices in euro at the fixed rate. A record, not a valuation. <a href=\"{HOME}\">{_('Full catalogue')}</a> · <a href=\"a/\">{_('Artists A–Z')}</a> · <a href=\"{OTHER}\">{OTHERLAB}</a></p></body></html>")

    out = "".join(parts)
    if lang == "et":   # Estonian groups thousands with a space
        for _k in range(3): out = re.sub(r"(\d),(\d{3})(?!\d)", "\\1\u202f\\2", out)
    open("site/" + OUTNAME, "w", encoding="utf-8").write(out)
    return len(parts)
render("en"); render("et")
print(f"  stats page      {len(lots):,} lots, {len(house)} houses, {len(year)} years")
