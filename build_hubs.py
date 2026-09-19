# -*- coding: utf-8 -*-
"""Hub pages: by decade, by medium, by museum and by subject, in English and Estonian.

The artist pages are 10,500 leaves; until now nothing crawlable stood between them
and the landing page. These few hundred pages are the branches -- each a real page
with counts, the artists most represented, a wall of pictures and links onward to
the artists, the neighbouring hubs and the app's own view -- and they answer the
mid-tail queries: "eesti maalikunst 1920ndad", "Tartu Kunstimuuseumi kogu",
"maastikumaal". Generated, never edited by hand; run after build_pages.py (it
appends to the sitemap) and before csp.py.

  EN /decades/1920.html  /media/painting.html  /museums/<slug>.html  /subjects/landscape.html
  ET /kumnendid/1920.html /liigid/maal.html    /muuseumid/<slug>.html /ained/maastik.html
"""
import json, os, re, html, unicodedata, datetime, collections

BASE = "https://museaal.ee"
d = json.load(open("data/data.json", encoding="utf-8"))
A, W, V, META = d["artists"], d["works"], d.get("vocab", {}), d["meta"]
I18N = json.load(open("i18n.json", encoding="utf-8"))
MUSEUM_EN, MEDIUM_ET, BLURB_ET = I18N["MUSEUM_EN"], I18N["MEDIUM_ET"], I18N["BLURB_ET"]
PERIODS = [(1700, 1917, "Tsaariaeg"), (1918, 1939, "Vabariik"), (1940, 1990, "Okupatsioon"), (1991, 2099, "Taasiseseisvus")]
GC = '<script data-goatcounter="https://museaal.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'
STAMP = "<script>try{if(localStorage.getItem(\"ekr:theme\")===\"light\")document.documentElement.setAttribute(\"data-theme\",\"light\")}catch(e){}</script>"
e = lambda s: html.escape(str(s or ""), quote=True)
def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s.lower())) or "x"
def val(w, f):
    v = w.get(f)
    if isinstance(v, int) and f in V: return V[f][v] if 0 <= v < len(V[f]) else None
    return v
# the English blurbs live in the app; read them from the template, as build_landing.py reads the door
_app = open("tpl_app.html", encoding="utf-8").read()
BLURB_EN = {int(m.group(1)): m.group(2) for m in re.finditer(r'^\s+(\d{4}):"((?:[^"\\]|\\.)*)"', _app[_app.index("const BLURBS = {"):], re.M)}
# the pictures and the shapes, as the app shows them
def imsrc(im):
    if not im: return ""
    if im.startswith("m:"): return f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={im[2:]}"
    if im.startswith("e:"): return "https://digikogu.ekm.ee/static/preview/image/" + re.sub(r"/([^/]+)$", r"/t2_\1", im[2:])
    return im[2:]
key = lambda w: w.get("k") or re.sub(r"[^A-Z0-9:]", "", (w.get("nu") or "").upper())
ARTIST_SLUG = {i: slug(a["n"]) for i, a in enumerate(A)}
CHARTS = {k: v for k, v in (json.load(open("data/chart_sides.json", encoding="utf-8")) if os.path.exists("data/chart_sides.json") else {}).items() if v}
POS = {"l": "100% 50%", "r": "0% 50%", "t": "50% 100%", "b": "50% 0%"}
crop = lambda im: f' style="object-position:{POS[CHARTS[im][0]]}"' if im in CHARTS else ""
MRANK = {"Painting": 0, "Watercolour": 1, "Sculpture": 2, "Mixed media": 3, "Installation": 3, "Drawing": 4, "Sketch": 5, "Photograph": 6, "Print": 7}
CSS = ("body{margin:0;padding:28px;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0b0c0e;color:#f1f2f4;max-width:980px}"
       ":root[data-theme=light] body{background:#fff;color:#111}"
       "h1{font-size:1.8rem;margin:0 0 4px;font-weight:600}h2{font-size:1.1rem;font-weight:500;margin:28px 0 8px}"
       ".m{color:#8b9098;font-size:.85rem;margin:0 0 12px}:root[data-theme=light] .m{color:#666}a{color:#9ec5ff}:root[data-theme=light] a{color:#1a4fa3}"
       "p.lede{max-width:70ch;font-size:1.02rem}nav{font-size:.85rem;margin-bottom:18px}"
       ".wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin:14px 0 6px}"
       ".wt{display:block;background:#15171a;text-decoration:none;color:inherit;overflow:hidden}:root[data-theme=light] .wt{background:#f1f2f4}"
       ".wt img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover}.wt span{display:block;font-size:.72rem;line-height:1.3;padding:5px 6px 6px;color:#8b9098}.wt span i{font-style:italic;color:#f1f2f4}"
       ":root[data-theme=light] .wt span i{color:#111}"
       "ul.cols{columns:230px;list-style:none;padding:0;margin:0}ul.cols li{break-inside:avoid;padding:2px 0}ul.cols .n{color:#8b9098;font-size:.8rem;margin-left:6px}"
       "ul.row{list-style:none;padding:0;margin:0;display:flex;flex-wrap:wrap;gap:6px 14px}ul.row .n{color:#8b9098;font-size:.8rem;margin-left:4px}"
       ".nb{margin-top:26px;padding-top:12px;border-top:1px solid #2b2e34;font-size:.9rem}"
       "details.emb{margin:18px 0 6px;font-size:.85rem}details.emb summary{cursor:pointer;color:#8b9098}details.emb textarea{width:100%;box-sizing:border-box;font:12px/1.4 ui-monospace,Menlo,monospace;padding:8px;border:1px solid #2b2e34;background:#111316;color:#c7cace}"
       ":root[data-theme=light] details.emb textarea{border-color:#ccc;background:#f7f7f7;color:#333}")

L = {"en": dict(site="Estonian Art Catalogue", dec="decades", med="media", mus="museums", sub="subjects", art="a",
                dec_h="Estonian art by decade", med_h="Estonian art by medium", mus_h="The collections", sub_h="Estonian art by subject",
                works="works", artists="artists", of="of", browse="Browse in the catalogue →", top_art="Artists most represented", pics="Pictures",
                by_dec="By decade", by_med="By medium", by_mus="Where the works are", prev="←", next="→", other="Eesti keeles",
                foot="Museum records from MuIS and the EKM Digital Collection; gallery stock from the galleries' own catalogues. Pictures for public-domain works and live gallery listings only, from the holders' own servers.",
                before="before 1800", dec_t="Estonian art of the {d}s – {n} works by {a} artists · museaal.ee", dec_d="Art made in Estonia and by Estonian artists in the {d}s: {n} works by {a} artists in Estonian public collections and galleries — {media}. The artists most represented, a wall of pictures, the museums that hold them.",
                med_t="{m} in Estonian collections – {n} works by {a} artists · museaal.ee", med_d="{m} in Estonian public collections and galleries: {n} works by {a} artists, {span}. The artists most represented, a wall of pictures, the decades and the museums.",
                mus_t="{m} – {n} works by {a} artists in the catalogue · museaal.ee", mus_d="The art collection of {m}: {n} works by {a} artists as catalogued in MuIS and the EKM Digital Collection, {span} — {media}. Artists, pictures, decades.",
                sub_t="{s} in Estonian art – {n} works by {a} artists · museaal.ee", sub_d="{n} works with {sl} in the title, by {a} Estonian artists, {span} — {media}. Who painted it, when, and where the works are.",
                site_link="", hash="", embed_h="Embed on your page", embed_t="A strip of pictures, the count and a link back. Paste both lines: the second is the link that tells search engines where the pictures live."),
     "et": dict(site="Eesti Kunstikataloog", dec="kumnendid", med="liigid", mus="muuseumid", sub="ained", art="k",
                dec_h="Eesti kunst kümnendite kaupa", med_h="Eesti kunst liigi kaupa", mus_h="Kogud", sub_h="Eesti kunst aine kaupa",
                works="teost", artists="kunstnikku", of="—", browse="Sirvi kataloogis →", top_art="Enim esindatud kunstnikud", pics="Pildid",
                by_dec="Kümnendi kaupa", by_med="Liigi kaupa", by_mus="Kus teosed on", prev="←", next="→", other="In English",
                foot="Muuseumikirjed MuISist ja EKM digikogust; galeriide laoseis galeriide endi kataloogidest. Pilte näidatakse ainult autoriõiguse alt vabade teoste ja galeriides müügil olevate teoste kohta, hoidjate endi serveritest.",
                before="enne 1800", dec_t="Eesti kunst {d}ndatel – {n} teost {a} kunstnikult · museaal.ee", dec_d="Eesti kunst {d}ndatel: {n} teost {a} kunstnikult Eesti avalikes kogudes ja galeriides — {media}. Enim esindatud kunstnikud, pildisein, muuseumid.",
                med_t="{m} Eesti kogudes – {n} teost {a} kunstnikult · museaal.ee", med_d="{m} Eesti avalikes kogudes ja galeriides: {n} teost {a} kunstnikult, {span}. Enim esindatud kunstnikud, pildisein, kümnendid ja muuseumid.",
                mus_t="{m} – {n} teost {a} kunstnikult kataloogis · museaal.ee", mus_d="{m} kunstikogu: {n} teost {a} kunstnikult MuISi ja EKM digikogu järgi, {span} — {media}. Kunstnikud, pildid, kümnendid.",
                sub_t="{s} Eesti kunstis – {n} teost {a} kunstnikult · museaal.ee", sub_d="{n} teost, mille pealkirjas on {sl}, {a} Eesti kunstnikult, {span} — {media}. Kes, millal ja kus.",
                site_link="#lang=et", hash="lang=et&", embed_h="Manusta oma lehele", embed_t="Pildiriba, teoste arv ja link tagasi. Kleebi mõlemad read: teine on link, mis ütleb otsimootorile, kust pildid pärit on.")}
MED_PL = {"en": {"Painting": "paintings", "Watercolour": "watercolours", "Drawing": "drawings", "Print": "prints", "Sculpture": "sculpture",
                 "Illustration": "illustrations", "Photograph": "photographs", "Mixed media": "mixed media", "Installation": "installations", "Poster": "posters", "Bookplate": "bookplates", "Other": "other"},
          "et": {"Painting": "maalid", "Watercolour": "akvarellid", "Drawing": "joonistused", "Print": "graafika", "Sculpture": "skulptuur",
                 "Illustration": "illustratsioonid", "Photograph": "fotod", "Mixed media": "segatehnika", "Installation": "installatsioonid", "Poster": "plakatid", "Bookplate": "eksliibrised", "Other": "muu"}}
med_name = lambda m, lang: m if lang == "en" else MEDIUM_ET.get(m, m)
mus_name = lambda m, lang: MUSEUM_EN.get(m, m) if lang == "en" else m
def media_phrase(ws, lang):
    c = collections.Counter(val(w, "e") for w in ws if val(w, "e"))
    names = [MED_PL[lang].get(m, med_name(m, lang).lower()) for m, _ in c.most_common(3)]
    return ", ".join(names[:-1]) + (" and " if lang == "en" else " ja ") + names[-1] if len(names) > 1 else (names[0] if names else "")
fmt = lambda n, lang: f"{n:,}" if lang == "en" else f"{n:,}".replace(",", " ")

# ---- the subjects: a word in the title, Estonian stems with their inflections ----------------
SUBJECTS = [  # (slug en, slug et, EN label, ET label, regex on the folded title)
 ("landscape", "maastik", "Landscape", "Maastik", r"\bmaastik"), ("portrait", "portree", "Portrait", "Portree", r"\bportree"),
 ("self-portrait", "autoportree", "Self-portrait", "Autoportree", r"\bautoportree"), ("still-life", "natuurmort", "Still life", "Natüürmort", r"\bnat[uü]{1,2}rmort"),
 ("nude", "akt", "Nude", "Akt", r"\b(nais|mees)?akt(id|i|e)?\b"), ("the-sea", "meri", "The sea", "Meri", r"\bmer(i|e|d|el|elt|es)\b|\bmerevaade|\bmeremaastik"),
 ("the-shore", "rand", "The shore", "Rand", r"\brand\b|\branna"), ("harbour", "sadam", "Harbour", "Sadam", r"\bsadam"), ("ships", "laev", "Ships", "Laev", r"\blaev"),
 ("winter", "talv", "Winter", "Talv", r"\btalv"), ("spring", "kevad", "Spring", "Kevad", r"\bkevad"), ("summer", "suvi", "Summer", "Suvi", r"\bsuvi\b|\bsuve"),
 ("autumn", "sugis", "Autumn", "Sügis", r"\bs[uü]gis"), ("flowers", "lilled", "Flowers", "Lilled", r"\blill"), ("forest", "mets", "Forest", "Mets", r"\bmets\b|\bmetsa"),
 ("river", "jogi", "River", "Jõgi", r"\bj[oõ]gi\b|\bj[oõ]e\b"), ("lake", "jarv", "Lake", "Järv", r"\bj[aä]rv"), ("village", "kula", "Village", "Küla", r"\bk[uü]la\b"),
 ("farm", "talu", "Farm", "Talu", r"\btalu\b|\btaluõu|\btalumaja"), ("street", "tanav", "Street", "Tänav", r"\bt[aä]nav"), ("church", "kirik", "Church", "Kirik", r"\bkirik"),
 ("night", "oo", "Night", "Öö", r"\b[oö]{2}\b|\b[oö]ine|\b[oö]{2}ne"), ("mother", "ema", "Mother", "Ema", r"\bema\b|\bema "), ("child", "laps", "Child", "Laps", r"\blaps|\blapse"),
 ("horse", "hobune", "Horse", "Hobune", r"\bhobu"), ("kalevipoeg", "kalevipoeg", "Kalevipoeg", "Kalevipoeg", r"\bkalevipo"), ("interior", "interjoor", "Interior", "Interjöör", r"\binterj"),
 ("factory", "tehas", "Factory", "Tehas", r"\btehas\b|\btehase"), ("kolkhoz", "kolhoos", "Kolkhoz", "Kolhoos", r"\bkolhoos"),
 ("tallinn", "tallinn", "Tallinn", "Tallinn", r"\btallinn"), ("tartu", "tartu", "Tartu", "Tartu", r"\btartu\b"), ("toompea", "toompea", "Toompea", "Toompea", r"\btoompea"),
 ("pirita", "pirita", "Pirita", "Pirita", r"\bpirita"), ("saaremaa", "saaremaa", "Saaremaa", "Saaremaa", r"\bsaaremaa"), ("parnu", "parnu", "Pärnu", "Pärnu", r"\bp[aä]rnu"),
 ("narva", "narva", "Narva", "Narva", r"\bnarva"), ("haapsalu", "haapsalu", "Haapsalu", "Haapsalu", r"\bhaapsalu"), ("viljandi", "viljandi", "Viljandi", "Viljandi", r"\bviljandi"),
 ("paris", "pariis", "Paris", "Pariis", r"\bpariis"), ("italy", "itaalia", "Italy", "Itaalia", r"\bitaalia|\bcapri\b|\brooma\b|\bveneetsia"), ("norway", "norra", "Norway", "Norra", r"\bnorra"),
]
fold = lambda s: unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()

# ---- the sets -------------------------------------------------------------------------------
held = [w for w in W if (w.get("kind") or "held") in ("held", "shown", "gallery", "known")]     # not the auction lots
dec_of = lambda w: (w["y"] // 10 * 10) if w.get("y") else None
by_dec = collections.defaultdict(list)
for w in held:
    dd = dec_of(w)
    if dd is not None: by_dec["before" if dd < 1800 else dd].append(w)
by_med = collections.defaultdict(list)
for w in held:
    m = val(w, "e")
    if m: by_med[m].append(w)
by_mus = collections.defaultdict(list)
for w in W:
    if (w.get("kind") or "held") == "held": by_mus[val(w, "mu")].append(w)
by_sub = collections.defaultdict(list)
for w in held:
    t = fold(w.get("t"))
    if not t: continue
    for sl_en, sl_et, en, et, rx in SUBJECTS:
        if re.search(rx, t): by_sub[sl_en].append(w)
DECS = ["before"] + sorted(k for k in by_dec if k != "before" and len(by_dec[k]) >= 20)
MEDS = [m for m, ws in sorted(by_med.items(), key=lambda kv: -len(kv[1])) if len(ws) >= 100 and m in MED_PL["en"]]
MUSS = [m for m, ws in sorted(by_mus.items(), key=lambda kv: -len(kv[1])) if len(ws) >= 100 and m]
SUBS = [s for s in SUBJECTS if len(by_sub[s[0]]) >= 40]

# ---- pieces ---------------------------------------------------------------------------------
def wall(ws, lang, n=24):
    pics = [w for w in ws if w.get("im")]
    pics.sort(key=lambda w: (w.get("mp") or 10**6, w.get("hl", 10**6), MRANK.get(val(w, "e"), 8), w.get("y") is None, w.get("y") or 0))
    seen, tiles, per = set(), [], collections.Counter()
    for w in pics:
        k = (w["a"], (w.get("t") or "").lower().strip(" ."))
        if k in seen or per[w["a"]] >= 3: continue          # three per artist at most, so a hub is not one artist's wall
        seen.add(k); per[w["a"]] += 1; tiles.append(w)
        if len(tiles) == n: break
    if not tiles: return ""
    return ('<div class="wall">' + "".join(
        f'<a class="wt" href="{BASE}/#{L[lang]["hash"]}artist={ARTIST_SLUG[w["a"]]}&open={e(key(w))}" title="{e(w.get("t"))} · {e(A[w["a"]]["n"])}">'
        f'<img src="{e(imsrc(w["im"]))}" alt="{e(w.get("t"))}, {e(A[w["a"]]["n"])}" loading="lazy"{crop(w["im"])} referrerpolicy="no-referrer-when-downgrade">'
        f'<span><i>{e(w.get("t"))}</i><br>{e(A[w["a"]]["n"])}{" · " + str(w["y"]) if w.get("y") else ""}</span></a>' for w in tiles) + "</div>")
def artists_list(ws, lang, n=60):
    c = collections.Counter(w["a"] for w in ws)
    return '<ul class="cols">' + "".join(f'<li><a href="{BASE}/{L[lang]["art"]}/{ARTIST_SLUG[i]}.html">{e(A[i]["n"])}</a><span class="n">{fmt(k, lang)}</span></li>' for i, k in c.most_common(n)) + "</ul>"
def dec_label(dd, lang): return L[lang]["before"] if dd == "before" else (f"{dd}s" if lang == "en" else f"{dd}ndad")
def dec_href(dd, lang): return f"{BASE}/{L[lang]['dec']}/{dd}.html"
def med_href(m, lang): return f"{BASE}/{L[lang]['med']}/{slug(med_name(m, lang))}.html"
def mus_href(m, lang): return f"{BASE}/{L[lang]['mus']}/{slug(mus_name(m, lang))}.html"
def sub_href(s, lang): return f"{BASE}/{L[lang]['sub']}/{s[0] if lang == 'en' else s[1]}.html"
def facet_row(ws, lang, kind):
    if kind == "dec":
        c = collections.Counter(("before" if dec_of(w) < 1800 else dec_of(w)) for w in ws if dec_of(w) is not None)
        items = [(dec_label(k, lang), dec_href(k, lang), v) for k, v in sorted(c.items(), key=lambda kv: (kv[0] == "before" and -1 or kv[0])) if k in DECS]
    elif kind == "med":
        c = collections.Counter(val(w, "e") for w in ws if val(w, "e"))
        items = [(med_name(k, lang), med_href(k, lang), v) for k, v in c.most_common() if k in MEDS]
    else:
        c = collections.Counter(val(w, "mu") for w in ws if (w.get("kind") or "held") == "held")
        items = [(mus_name(k, lang), mus_href(k, lang), v) for k, v in c.most_common() if k in MUSS]
    if not items: return ""
    return '<ul class="row">' + "".join(f'<li><a href="{h}">{e(lab)}</a><span class="n">{fmt(v, lang)}</span></li>' for lab, h, v in items) + "</ul>"
def span_of(ws):
    ys = sorted(w["y"] for w in ws if w.get("y"))
    return f"{ys[0]}–{ys[-1]}" if ys else ""
def embed_box(lang, src, back, name):
    T = L[lang]
    code = (f'<iframe src="{src}" width="100%" height="230" loading="lazy" title="{name} – museaal.ee"></iframe>\n'
            f'<p><a href="{back}">{name}{" at museaal.ee" if lang == "en" else " museaal.ee-s"}</a></p>')
    return (f'<details class="emb"><summary>{T["embed_h"]}</summary><p class="m">{T["embed_t"]}</p>'
            f'<textarea readonly rows="3" spellcheck="false">{e(code)}</textarea></details>')

def page(lang, me, other, title, desc, h1, lede, ws, app_hash, facets, nb, xdefault, embed_src=None):
    T = L[lang]
    a_n = len({w["a"] for w in ws})
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><meta name="description" content="{e(desc[:300])}">'
            f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}"><link rel="alternate" hreflang="x-default" href="{xdefault}">'
            f'<meta property="og:type" content="website"><meta property="og:title" content="{e(h1)}"><meta property="og:description" content="{e(desc[:300])}"><meta property="og:url" content="{me}"><meta property="og:site_name" content="{T["site"]}">'
            f'<style>{CSS}</style>{GC}</head><body>'
            f'<nav><a href="{BASE}/{T["site_link"]}">{T["site"]}</a> › {nb["crumb"]} <span class="m">· <a href="{other}">{T["other"]}</a></span></nav>'
            f'<h1>{e(h1)}</h1><p class="m">{fmt(len(ws), lang)} {T["works"]} · {fmt(a_n, lang)} {T["artists"]}{" · " + span_of(ws) if span_of(ws) else ""}</p>'
            + (f'<p class="lede">{e(lede)}</p>' if lede else "")
            + f'<p><a href="{BASE}/#{T["hash"]}{app_hash}">{T["browse"]}</a></p>'
            + wall(ws, lang)
            + f'<h2>{T["top_art"]}</h2>' + artists_list(ws, lang)
            + "".join(f'<h2>{h}</h2>{r}' for h, r in facets if r)
            + f'<p class="nb">{nb["links"]}</p>'
            + (embed_box(lang, embed_src, me, h1) if embed_src else "")
            + f'<p class="m">{T["foot"]}</p></body></html>')

def main():
    # ---- write ----------------------------------------------------------------------------------
    os.makedirs("site", exist_ok=True)
    urls = []
    for lang in ("en", "et"):
        T = L[lang]; O = L["et" if lang == "en" else "en"]
        for k in ("dec", "med", "mus", "sub"): os.makedirs(f"site/{T[k]}", exist_ok=True)
        # decades
        for n_, dd in enumerate(DECS):
            ws = by_dec[dd]; lab = dec_label(dd, lang)
            me, other = dec_href(dd, lang), dec_href(dd, "et" if lang == "en" else "en")
            blurb = "" if dd == "before" else (BLURB_EN.get(dd, "") if lang == "en" else BLURB_ET.get(str(dd), ""))
            per = next((p for p in PERIODS if dd != "before" and p[0] <= dd + 9 and p[1] >= dd), None)
            per_lab = (I18N["PERIOD_EN"][per[2]] if lang == "en" else I18N["PERIOD_ET"][per[2]]) if per else ""
            title = T["dec_t"].format(d=dd if dd != "before" else lab, n=fmt(len(ws), lang), a=fmt(len({w["a"] for w in ws}), lang)) if dd != "before" else f"{T['site']} · {lab} · {fmt(len(ws), lang)} {T['works']}"
            desc = T["dec_d"].format(d=dd if dd != "before" else lab, n=fmt(len(ws), lang), a=fmt(len({w["a"] for w in ws}), lang), media=media_phrase(ws, lang))
            h1 = (f"Estonian art of the {dd}s" if lang == "en" else f"Eesti kunst {dd}ndatel") if dd != "before" else (f"Estonian art {lab}" if lang == "en" else f"Eesti kunst {lab}")
            lede = (per_lab + " — " if per_lab else "") + blurb
            links = " · ".join(x for x in [f'<a href="{dec_href(DECS[n_-1], lang)}">← {dec_label(DECS[n_-1], lang)}</a>' if n_ else "",
                                            f'<a href="{BASE}/{T["dec"]}/">{T["dec_h"]}</a>',
                                            f'<a href="{dec_href(DECS[n_+1], lang)}">{dec_label(DECS[n_+1], lang)} →</a>' if n_ + 1 < len(DECS) else ""] if x)
            nb = dict(crumb=f'<a href="{BASE}/{T["dec"]}/">{T["dec_h"]}</a> › {lab}', links=links)
            open(f"site/{T['dec']}/{dd}.html", "w", encoding="utf-8").write(page(lang, me, other, title, desc, h1, lede, ws,
                f"decade={dd}" if dd != "before" else "to=1799", [(T["by_med"], facet_row(ws, lang, "med")), (T["by_mus"], facet_row(ws, lang, "mus"))], nb, dec_href(dd, "en"),
            f"{BASE}/embed/{'' if lang == 'en' else 'et/'}{T['dec']}/{dd}.html"))
            urls.append((me, dec_href(dd, "en"), dec_href(dd, "et")))
        # media
        for m in MEDS:
            ws = by_med[m]; lab = med_name(m, lang)
            me, other = med_href(m, lang), med_href(m, "et" if lang == "en" else "en")
            an = fmt(len({w["a"] for w in ws}), lang)
            title = T["med_t"].format(m=lab, n=fmt(len(ws), lang), a=an); desc = T["med_d"].format(m=lab, n=fmt(len(ws), lang), a=an, span=span_of(ws))
            nb = dict(crumb=f'<a href="{BASE}/{T["med"]}/">{T["med_h"]}</a> › {e(lab)}', links=f'<a href="{BASE}/{T["med"]}/">{T["med_h"]}</a>')
            open(f"site/{T['med']}/{slug(lab)}.html", "w", encoding="utf-8").write(page(lang, me, other, title, desc, lab, "", ws, f"media={m}",
                [(T["by_dec"], facet_row(ws, lang, "dec")), (T["by_mus"], facet_row(ws, lang, "mus"))], nb, med_href(m, "en")))
            urls.append((me, med_href(m, "en"), med_href(m, "et")))
        # museums
        for m in MUSS:
            ws = by_mus[m]; lab = mus_name(m, lang)
            me, other = mus_href(m, lang), mus_href(m, "et" if lang == "en" else "en")
            an = fmt(len({w["a"] for w in ws}), lang)
            title = T["mus_t"].format(m=lab, n=fmt(len(ws), lang), a=an); desc = T["mus_d"].format(m=lab, n=fmt(len(ws), lang), a=an, span=span_of(ws), media=media_phrase(ws, lang))
            site = META.get("sites", {}).get(m)
            lede = ""
            nb = dict(crumb=f'<a href="{BASE}/{T["mus"]}/">{T["mus_h"]}</a> › {e(lab)}',
                      links=" · ".join(x for x in [f'<a href="{BASE}/{T["mus"]}/">{T["mus_h"]}</a>', f'<a href="{e(site)}" rel="noopener">{e(lab)} ↗</a>' if site else ""] if x))
            open(f"site/{T['mus']}/{slug(lab)}.html", "w", encoding="utf-8").write(page(lang, me, other, title, desc, lab, lede, ws, f"museum={m}",
                [(T["by_dec"], facet_row(ws, lang, "dec")), (T["by_med"], facet_row(ws, lang, "med"))], nb, mus_href(m, "en")))
            urls.append((me, mus_href(m, "en"), mus_href(m, "et")))
        # subjects
        for s in SUBS:
            ws = by_sub[s[0]]; lab = s[2] if lang == "en" else s[3]
            me, other = sub_href(s, lang), sub_href(s, "et" if lang == "en" else "en")
            an = fmt(len({w["a"] for w in ws}), lang)
            title = T["sub_t"].format(s=lab, n=fmt(len(ws), lang), a=an); desc = T["sub_d"].format(n=fmt(len(ws), lang), sl=("“" + s[3] + "”"), a=an, span=span_of(ws), media=media_phrase(ws, lang))
            nb = dict(crumb=f'<a href="{BASE}/{T["sub"]}/">{T["sub_h"]}</a> › {e(lab)}', links=f'<a href="{BASE}/{T["sub"]}/">{T["sub_h"]}</a>')
            open(f"site/{T['sub']}/{s[0] if lang == 'en' else s[1]}.html", "w", encoding="utf-8").write(page(lang, me, other, title, desc, lab, "", ws, f"q={s[3]}",
                [(T["by_dec"], facet_row(ws, lang, "dec")), (T["by_med"], facet_row(ws, lang, "med")), (T["by_mus"], facet_row(ws, lang, "mus"))], nb, sub_href(s, "en"),
            f"{BASE}/embed/{'' if lang == 'en' else 'et/'}{T['sub']}/{s[0] if lang == 'en' else s[1]}.html"))
            urls.append((me, sub_href(s, "en"), sub_href(s, "et")))
        # the four indexes
        for k, h, items in (("dec", T["dec_h"], [(dec_label(dd, lang), dec_href(dd, lang), len(by_dec[dd])) for dd in DECS]),
                            ("med", T["med_h"], [(med_name(m, lang), med_href(m, lang), len(by_med[m])) for m in MEDS]),
                            ("mus", T["mus_h"], [(mus_name(m, lang), mus_href(m, lang), len(by_mus[m])) for m in MUSS]),
                            ("sub", T["sub_h"], [((s[2] if lang == "en" else s[3]), sub_href(s, lang), len(by_sub[s[0]])) for s in SUBS])):
            me, other = f"{BASE}/{T[k]}/", f"{BASE}/{O[k]}/"
            lst = '<ul class="cols">' + "".join(f'<li><a href="{u}">{e(lab)}</a><span class="n">{fmt(n, lang)}</span></li>' for lab, u, n in items) + "</ul>"
            open(f"site/{T[k]}/index.html", "w", encoding="utf-8").write(
                f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{e(h)} · museaal.ee</title><meta name="description" content="{e(h)}: {len(items)} {"pages" if lang == "en" else "lehte"} · {T["site"]}">'
                f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
                f'<style>{CSS}</style>{GC}</head><body><nav><a href="{BASE}/{T["site_link"]}">{T["site"]}</a> › {e(h)} <span class="m">· <a href="{other}">{T["other"]}</a></span></nav>'
                f'<h1>{e(h)}</h1>{lst}<p class="nb">' + " · ".join(f'<a href="{BASE}/{T[x]}/">{T[x + "_h"]}</a>' for x in ("dec", "med", "mus", "sub") if x != k)
                + f' · <a href="{BASE}/{T["art"]}/">{"Artists A–Z" if lang == "en" else "Kunstnikud A–Ü"}</a></p></body></html>')
            urls.append((me, f"{BASE}/{L['en'][k]}/", f"{BASE}/{L['et'][k]}/"))

    # into the sitemap build_pages.py wrote
    today = datetime.date.today().isoformat()
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    add = "".join(f'<url><loc>{me}</loc><lastmod>{today}</lastmod><xhtml:link rel="alternate" hreflang="en" href="{en}"/><xhtml:link rel="alternate" hreflang="et" href="{et}"/></url>' for me, en, et in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  hub pages      {len(urls):,} ({len(DECS)} decades, {len(MEDS)} media, {len(MUSS)} museums, {len(SUBS)} subjects, 4 indexes; both languages)")


if __name__ == "__main__":
    main()
