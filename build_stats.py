# -*- coding: utf-8 -*-
"""site/stats.html -- the catalogue in figures, built from data/data.json.

A plain page in the style of the artist pages: what the catalogue holds by kind and
by medium; the auction record by house and by year; the artists most sold at
auction by lots and by the sum of their hammer prices; the highest results; how
much of each house's offering finds a buyer. Every figure is computed here from
the same data the app loads, so the page and the app never disagree.
"""
import json, html, datetime, collections, re, unicodedata

SRC, OUT = "data/data.json", "site/stats.html"
d = json.load(open(SRC, encoding="utf-8"))
W, A, V = d["works"], d["artists"], d["vocab"]
e = html.escape
val = lambda w, f: (V[f][w[f]] if isinstance(w.get(f), int) and f in V else w.get(f))
kind = lambda w: w.get("kind") or "held"
fmt = lambda n: f"{n:,}"
eur = lambda n: f"{n:,} €"
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s))

# ---- holdings ----
by_kind = collections.Counter(kind(w) for w in W)
KIND = {"held": "In museum collections", "shown": "Exhibited", "gallery": "For sale in galleries", "sold": "Past gallery listings", "auction": "Auction lots"}
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
       ".big{font-size:2rem;font-weight:500;line-height:1.1}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:18px;margin:18px 0 6px}")

today = datetime.date.today().isoformat()
parts = [f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
         f"<title>The catalogue in figures — Estonian Art Catalogue</title>"
         f"<meta name=\"description\" content=\"What museaal.ee holds by kind and medium, and the Estonian auction record by house, year and artist.\">"
         f"<link rel=\"canonical\" href=\"https://museaal.ee/stats.html\"><style>{CSS}</style></head><body>"
         f"<nav><a href=\"./\">Estonian Art Catalogue</a> › The catalogue in figures</nav>"
         f"<h1>The catalogue in figures</h1><p class=\"m\">Computed from the data as built on {today}. Prices are hammer prices as the houses published them; a gallery's asking prices are never taken.</p>"]

parts.append('<div class="grid">' + "".join(f'<div><div class="big">{fmt(n)}</div><div class="m">{e(KIND.get(k, k))}</div></div>'
             for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1])) + "</div>")
parts.append(f"<h2>By medium</h2>" + table(["Medium", "Museums", "For sale", "Past listings", "Auction lots", "All"],
             [[e(m), fmt(c["held"] + c.get("shown", 0)), fmt(c["gallery"]), fmt(c["sold"]), fmt(c["auction"]), fmt(sum(c.values()))] for m, c in med_rows]))

parts.append(f"<h2>The auction record</h2><div class=\"grid\">"
             f"<div><div class=\"big\">{fmt(len(lots))}</div><div class=\"m\">lots</div></div>"
             f"<div><div class=\"big\">{fmt(len(sold))}</div><div class=\"m\">sold · {pct(len(sold), len(lots))}</div></div>"
             f"<div><div class=\"big\">{eur(total)}</div><div class=\"m\">hammer prices in all, {fmt(len(priced))} lots</div></div>"
             f"<div><div class=\"big\">{eur(round(total / len(priced)))}</div><div class=\"m\">average · median {eur(sorted(w['ap'] for w in priced)[len(priced) // 2])}</div></div></div>")
parts.append("<h2>By house</h2>" + table(["House", "Sales", "Lots", "Sold", "Sell-through", "Hammer total"],
             [[e(h), f"{v['first']}–{v['last']}", fmt(v["lots"]), fmt(v["sold"]), pct(v["sold"], v["lots"]), eur(v["sum"])]
              for h, v in sorted(house.items(), key=lambda kv: -kv[1]["sum"])]))
parts.append("<h2>By year</h2>" + table(["Year", "Lots", "Sold", "Sell-through", "Hammer total", "Average"],
             [[y, fmt(v["lots"]), fmt(v["sold"]), pct(v["sold"], v["lots"]), eur(v["sum"]), eur(round(v["sum"] / v["sold"])) if v["sold"] else "—"]
              for y, v in sorted(year.items(), reverse=True)]))
parts.append("<h2>By medium at auction</h2>" + table(["Medium", "Lots", "Sold", "Sell-through", "Hammer total", "Average"],
             [[e(m), fmt(v["lots"]), fmt(v["sold"]), pct(v["sold"], v["lots"]), eur(v["sum"]), eur(round(v["sum"] / v["sold"])) if v["sold"] else "—"]
              for m, v in sorted(auc_med.items(), key=lambda kv: -kv[1]["sum"])]))
parts.append("<h2>Artists most sold at auction</h2><p class=\"m\">By lots sold.</p>" + table(["", "Artist", "Sold", "Of lots", "Hammer total", "Highest"],
             [[str(k + 1), artist_link(i), fmt(v["sold"]), fmt(v["lots"]), eur(v["sum"]), eur(v["top"])] for k, (i, v) in enumerate(top_by_lots)]))
parts.append("<h2>Artists by the sum of their hammer prices</h2>" + table(["", "Artist", "Hammer total", "Sold", "Of lots", "Average", "Highest"],
             [[str(k + 1), artist_link(i), eur(v["sum"]), fmt(v["sold"]), fmt(v["lots"]), eur(round(v["sum"] / v["sold"])) if v["sold"] else "—", eur(v["top"])]
              for k, (i, v) in enumerate(top_by_sum)]))
parts.append("<h2>Highest results</h2>" + table(["", "Work", "Artist", "House", "Sale", "Hammer price"],
             [[str(k + 1), f"<em>{e(w['t'])}</em>" + (f" <span class=m>{e(str(w.get('yl') or w.get('y') or ''))}</span>" if (w.get('yl') or w.get('y')) else ""),
               artist_link(w["a"]), e(val(w, "mu")), e(str(w.get("ad", ""))[:4]), eur(w["ap"])] for k, w in enumerate(top_results)]))
parts.append(f"<p class=\"m\" style=\"margin-top:36px\">Auction results as Haus Galerii, Vernissage, Allee galerii, Vaal galerii, E-Kunstisalong and Eesti Kunsti Oksjonid published them, plus a few earlier record prices as the press reported them; kroon-era prices in euro at the fixed rate. A record, not a valuation. <a href=\"./\">Full catalogue</a> · <a href=\"a/\">Artists A–Z</a></p></body></html>")
open(OUT, "w", encoding="utf-8").write("".join(parts))
print(f"  stats page      {len(lots):,} lots, {len(house)} houses, {len(year)} years")
