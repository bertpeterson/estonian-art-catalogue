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
import json, os, re, html, unicodedata, datetime, collections
GC = '<script data-goatcounter="https://museaal.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'   # GoatCounter: a page-view count, no cookies

BASE = "https://museaal.ee"
OUT  = "site/a"
d = json.load(open("data/data.json", encoding="utf-8"))
A, W, V = d["artists"], d["works"], d.get("vocab", {})

# the six similar artists (data/similar.py) live beside the dataset, not in it
if os.path.exists("data/similar.json"):
    for _i, _s in json.load(open("data/similar.json", encoding="utf-8")).items(): A[int(_i)]["sim"] = _s
os.makedirs(OUT, exist_ok=True)

def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))

def val(w, f):
    v = w.get(f)
    if isinstance(v, int) and f in V: return V[f][v] if 0 <= v < len(V[f]) else None
    return v

e = lambda s: html.escape(str(s or ""), quote=True)
KIND = {"school": "trained at", "movement": "movement", "member": "member of"}
# Every artist has two pages: /a/<slug>.html in English and /k/<slug>.html in Estonian
# (k for kunstnik), each naming the other as its hreflang alternate. The audience that
# would search for these artists searches in Estonian; the pages were English only.
I18N = json.load(open("i18n.json", encoding="utf-8"))
MED_ET = I18N["MEDIUM_ET"]
L = {
 "en": dict(dir="a", site="Estonian Art Catalogue", kind=KIND, works="works", artists="Artists A–Z", art_nav="Artists",
            year="Year", title="Title", tech="Technique", dims="Dimensions", held="Held by", browse="Browse {n} works in the catalogue →",
            sold="sold", gone="no longer listed", soldp="Sold €{p}", soldnp="Sold", unsold="Unsold",
            first600="Showing the first 600 of {n} works — <a href=\"{u}\">see all in the catalogue</a>.",
            pics="{p} works with a picture; the first {k} here, all in the catalogue. Pictures for public-domain works and live gallery listings only, from the holders' own servers.",
            sim="Similar artists — same period, media and subjects: ", school="Also trained at {g}", movement="Also working in {g}", member="Also in {g}",
            contemp="Contemporaries in {h}: ", allaz="All artists A&ndash;Z",
            au="{n} auction lots · {s} sold · {y}{r} — as the auction houses published them; not a valuation",
            foot="Museum records from MuIS and the EKM Digital Collection; gallery stock from the galleries' own catalogues; auction results as Haus Galerii, Vernissage, Allee galerii, Vaal galerii, E-Kunstisalong and Eesti Kunsti Oksjonid published them. ",
            full="Full catalogue", mt=" <span class=\"m\">(machine translation of the holder&#39;s Estonian text, unedited)</span>", enonly="",
            embed_h="Embed on your page", embed_t="A strip of pictures, the count and a link back, for a blog, a course page or a museum's site. Paste both lines: the second is the link that tells search engines where the pictures live.",
            idx_title="Artists A–Z — Estonian Art Catalogue", idx_desc="Every artist in the Estonian Art Catalogue: {n} artists represented in Estonian public collections and galleries.",
            idx_h="Artists A–Z", idx_n="{n} artists", other_lang="Eesti keeles", hash="", in_mus="in Estonian museums and galleries", in_mus_nog="in Estonian museums",
            desc="{name}{dates}: {n} works in Estonian public collections{gal}, {span} — {media}, at {holders}. Every record links to its source.",
            desc_nospan="{name}{dates}: {n} works in Estonian public collections{gal} — {media}, at {holders}. Every record links to its source.", gal=" and galleries"),
 "et": dict(dir="k", site="Eesti Kunstikataloog", kind={"school": "õppinud:", "movement": "suund:", "member": "liige:"}, works="teost", artists="Kunstnikud A–Ü", art_nav="Kunstnikud",
            year="Aasta", title="Pealkiri", tech="Tehnika", dims="Mõõdud", held="Hoidja", browse="Sirvi {n} teost kataloogis →",
            sold="müüdud", gone="enam ei pakuta", soldp="Müüdud €{p}", soldnp="Müüdud", unsold="Müümata",
            first600="Esimesed 600 teost {n}-st — <a href=\"{u}\">vaata kõiki kataloogis</a>.",
            pics="{p} pildiga teost; siin esimesed {k}, kõik kataloogis. Pilte näidatakse ainult autoriõiguse alt vabade teoste ja galeriides müügil olevate teoste kohta, hoidjate endi serveritest.",
            sim="Sarnased kunstnikud — sama aeg, liigid ja ained: ", school="Samuti õppinud: {g}", movement="Samuti: {g}", member="Samuti {g} liige",
            contemp="Kaasaegsed kogus {h}: ", allaz="Kõik kunstnikud A&ndash;Ü",
            au="{n} oksjonipartiid · {s} müüdud · {y}{r} — nii, nagu oksjonimajad avaldasid; mitte hinnang",
            foot="Muuseumikirjed MuISist ja EKM digikogust; galeriide laoseis galeriide endi kataloogidest; oksjonitulemused nii, nagu Haus Galerii, Vernissage, Allee galerii, Vaal galerii, E-Kunstisalong ja Eesti Kunsti Oksjonid need avaldasid. ",
            full="Kogu kataloog", mt="", enonly=" <span class=\"m\">(inglise keeles)</span>",
            embed_h="Manusta oma lehele", embed_t="Pildiriba, teoste arv ja link tagasi — blogile, kursuse lehele või muuseumi kodulehele. Kleebi mõlemad read: teine on link, mis ütleb otsimootorile, kust pildid pärit on.",
            idx_title="Kunstnikud A–Ü — Eesti Kunstikataloog", idx_desc="Kõik Eesti Kunstikataloogi kunstnikud: {n} kunstnikku, kelle teoseid on Eesti avalikes kogudes ja galeriides.",
            idx_h="Kunstnikud A–Ü", idx_n="{n} kunstnikku", other_lang="In English", hash="lang=et&", in_mus="Eesti muuseumides ja galeriides", in_mus_nog="Eesti muuseumides",
            desc="{name}{dates}: {n} teost Eesti avalikes kogudes{gal}, {span} — {media}; {holders}. Iga kirje viitab allikale.",
            desc_nospan="{name}{dates}: {n} teost Eesti avalikes kogudes{gal} — {media}; {holders}. Iga kirje viitab allikale.", gal=" ja galeriides"),
}
MED_NAME = {"en": lambda m: m, "et": lambda m: MED_ET.get(m, m)}
# the media a description names: "paintings, drawings and prints" / "maalid, joonistused ja graafika"
MED_PL = {"en": {"Painting": "paintings", "Watercolour": "watercolours", "Drawing": "drawings", "Print": "prints", "Sculpture": "sculpture",
                 "Illustration": "illustrations", "Photograph": "photographs", "Mixed media": "mixed media", "Installation": "installations", "Poster": "posters", "Bookplate": "bookplates"},
          "et": {"Painting": "maalid", "Watercolour": "akvarellid", "Drawing": "joonistused", "Print": "graafika", "Sculpture": "skulptuur",
                 "Illustration": "illustratsioonid", "Photograph": "fotod", "Mixed media": "segatehnika", "Installation": "installatsioonid", "Poster": "plakatid", "Bookplate": "eksliibrised"}}
def media_phrase(ws, lang):
    c = {}
    for w in ws:
        m = val(w, "e")
        if m: c[m] = c.get(m, 0) + 1
    names = [MED_PL[lang].get(m, MED_NAME[lang](m).lower()) for m, _ in sorted(c.items(), key=lambda kv: -kv[1])[:3]]
    if not names: return ""
    if len(names) == 1: return names[0]
    return ", ".join(names[:-1]) + (" and " if lang == "en" else " ja ") + names[-1]
by_artist = {}
for w in W: by_artist.setdefault(w["a"], []).append(w)

CSS = ("body{margin:0;padding:28px;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
       "background:#fff;color:#111;max-width:940px}"
       ":root:not([data-theme=light]) body{background:#0b0c0e;color:#f1f2f4}:root:not([data-theme=light]) a{color:#9ec5ff}:root:not([data-theme=light]) "
       "th,:root:not([data-theme=light]) td{border-color:#2b2e34!important}:root:not([data-theme=light]) .m{color:#8b9098!important}"
       "h1{font-size:1.7rem;margin:0 0 4px;font-weight:600}"
       ".m{color:#666;font-size:.85rem;margin:0 0 14px}"
       "table{border-collapse:collapse;width:100%;font-size:.88rem;margin-top:14px}"
       "th,td{text-align:left;padding:5px 9px 5px 0;border-bottom:1px solid #e3e5e9;vertical-align:top}"
       "th{font-size:.7rem;text-transform:uppercase;letter-spacing:.09em;color:#666;font-weight:500}"
       "p.bio{max-width:66ch}a.cta{display:inline-block;margin:12px 0}nav{font-size:.85rem;margin-bottom:18px}"
       "details.emb{margin:22px 0 6px;font-size:.85rem}details.emb summary{cursor:pointer;color:#666}details.emb textarea{width:100%;box-sizing:border-box;font:12px/1.4 ui-monospace,Menlo,monospace;padding:8px;border:1px solid #2b2e34;background:#111316;color:#c7cace}"
       ":root[data-theme=light] details.emb textarea{border-color:#ccc;background:#f7f7f7;color:#333}"
       ".rel{font-size:.85rem;color:#666;margin:6px 0;max-width:80ch;line-height:1.7}"
       ".rel.nb{margin-top:22px;padding-top:12px;border-top:1px solid #e3e5e9}"
       ":root:not([data-theme=light]) .rel{color:#8b9098}:root:not([data-theme=light]) .rel.nb{border-color:#2b2e34}"
       ".wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin:14px 0 6px}"
       ".wt{display:block;background:#f1f2f4;text-decoration:none;color:inherit}.wt img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover}.wt{overflow:hidden}"
       ".wt span{display:block;font-size:.72rem;line-height:1.3;padding:5px 6px 6px;color:#666}.wt span i{font-style:italic;color:#111}"
       ":root:not([data-theme=light]) .wt{background:#15171a}:root:not([data-theme=light]) .wt span{color:#8b9098}:root:not([data-theme=light]) .wt span i{color:#f1f2f4}"
       # The app offers this as "printable page for this artist", so make that true:
       # drop the navigation and the call to action, force black on white regardless of
       # the reader's theme, and keep table rows from splitting across pages.
       "@media print{body{background:#fff;color:#000;padding:0;max-width:none;font-size:11pt}"
       "nav,a.cta,.rel{display:none}a{color:#000;text-decoration:none}"
       "th,td{border-color:#999!important}tr{break-inside:avoid}"
       "thead{display:table-header-group}h1{font-size:16pt}"
       "table{font-size:9pt}}")


def jsonld(a, ws, sl, dates, lang="en"):
    """schema.org description of the artist and a sample of their works.

    Plain HTML tells a crawler these are words; this tells it they are an artist and
    artworks, which is what lets an art-specific query match. Only the first 50 works
    are described — enough to characterise the page without a megabyte of JSON."""
    life = a.get("l") or ["", ""]
    D = L[lang]["dir"]
    person = {"@type": "Person", "name": a["n"], "url": f"{BASE}/{D}/{sl}.html"}
    if life[0]: person["birthDate"] = life[0]
    if life[1]: person["deathDate"] = life[1]
    if a.get("born"): person["birthPlace"] = {"@type": "Place", "name": a["born"]}
    if a.get("qid"): person["sameAs"] = f"https://www.wikidata.org/wiki/{a['qid']}"
    if a.get("wdesc"): person["description"] = a["wdesc"]
    if a.get("aff"): person["nationality"] = a["aff"]
    for g in a.get("grp", []):
        kind, label = g.split(":", 1)
        key = {"school": "alumniOf", "member": "memberOf", "movement": "movement"}[kind]
        org = {"@type": "Organization", "name": label} if kind != "movement" else label
        person.setdefault(key, []).append(org)
    works = []
    for w in ws[:50]:
        it = {"@type": "VisualArtwork", "name": w.get("t") or "—",
              "creator": {"@type": "Person", "name": a["n"]}}
        if w.get("y"): it["dateCreated"] = str(w["y"])
        if val(w, "tc") or val(w, "tce"): it["artMedium"] = val(w, "tc") or val(w, "tce")
        if val(w, "e"): it["artform"] = val(w, "e")
        if val(w, "mu"): it["holdingArchive"] = {"@type": "Organization", "name": val(w, "mu")}
        works.append(it)
    return json.dumps({"@context": "https://schema.org", "@graph": [person,
        {"@type": "CollectionPage", "name": (f"Works by {a['n']}" if lang == "en" else f"{a['n']} teosed"), "inLanguage": lang,
         "url": f"{BASE}/{D}/{sl}.html", "about": person,
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(ws),
                        "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": it}
                                            for i, it in enumerate(works)]}}]},
        ensure_ascii=False, separators=(",", ":"))

# ---- related artists -------------------------------------------------------
# Until now every artist page was an orphan: it linked up to the catalogue and
# across to the app, never sideways to another artist. That is a dead end for a
# reader who has just found a name they did not know, and for a crawler it means
# each page is reachable only from the A-Z index, with no reason to go deeper.
#
# Three relations, and every page gets at least one. Alphabetical neighbours are
# always available and chain all 3,664 pages into a single traversable sequence.
# A shared school or movement is the strongest link we hold, but only 745 artists
# carry one. Contemporaries -- nearest in working period within the same
# collection -- covers the rest.
LIVE   = [i for i in range(len(A)) if by_artist.get(i)]
SLUG   = {i: (slug(A[i]["n"]) or f"artist-{i}") for i in LIVE}
NWORKS = {i: len(by_artist[i]) for i in LIVE}

def period(i):
    """One year placing an artist in time, for ordering only.

    The median year of their dated works is the most honest single number: it is
    what the catalogue actually knows. Birth year plus 35 stands in when nothing
    is dated, which is roughly when a painter's catalogued work begins."""
    ys = sorted(w["y"] for w in by_artist[i] if w.get("y"))
    if ys: return ys[len(ys) // 2]
    m = re.search(r"\d{4}", str((A[i].get("l") or [""])[0] or ""))
    return int(m.group()) + 35 if m else None

by_grp = {}
for i in LIVE:
    for g in A[i].get("grp", []): by_grp.setdefault(g, []).append(i)

# Bucket by the artist's principal holder, ordered by period, so contemporaries
# are the neighbours in that ordering -- no 3,664-squared comparison needed.
PERIOD, principal, by_holder = {}, {}, {}
for i in LIVE:
    PERIOD[i] = period(i)
    c = {}
    for w in by_artist[i]:
        h = val(w, "mu")
        if h: c[h] = c.get(h, 0) + 1
    if c and PERIOD[i]:
        principal[i] = max(c, key=c.get)
        by_holder.setdefault(principal[i], []).append(i)
for h in by_holder:
    by_holder[h].sort(key=lambda i: PERIOD[i])
HPOS = {h: {i: n for n, i in enumerate(lst)} for h, lst in by_holder.items()}

ALPHA = sorted(LIVE, key=lambda i: A[i]["n"])
APOS  = {i: n for n, i in enumerate(ALPHA)}

def link(i, lang="en"):
    return f'<a href="{BASE}/{L[lang]["dir"]}/{SLUG[i]}.html">{e(A[i]["n"])}</a>'

def related(i, lang="en"):
    """Rendered related-artist lines for artist i, or an empty string."""
    T = L[lang]; link_ = lambda j: link(j, lang)
    seen, out = {i}, []
    # the computed neighbours first (similar.py: period, media, techniques, subjects,
    # movement or category) -- the line for a reader who liked the style
    sim = [j for j in A[i].get("sim", []) if j in SLUG]
    if sim:
        seen.update(sim)
        out.append('<p class="rel">' + T["sim"] + " · ".join(link_(j) for j in sim) + "</p>")
    # Rarest shared group first: "Atelier School of Ants Laikmaa" tells a reader
    # far more than "Estonian Academy of Arts", which 343 artists share.
    for g in sorted(A[i].get("grp", []), key=lambda g: len(by_grp[g]))[:2]:
        peers = [j for j in sorted(by_grp[g], key=lambda j: -NWORKS[j]) if j not in seen][:5]
        if not peers: continue
        seen.update(peers)
        kind, label = g.split(":", 1)
        lead = T[kind].format(g=label)
        out.append(f'<p class="rel">{e(lead)}: ' + " · ".join(link_(j) for j in peers) + "</p>")
    h = principal.get(i)
    if h:
        lst, pos = by_holder[h], HPOS[h][i]
        near = [lst[n] for n in range(max(0, pos - 6), min(len(lst), pos + 7)) if lst[n] not in seen]
        near.sort(key=lambda j: (abs(PERIOD[j] - PERIOD[i]), -NWORKS[j]))
        near = near[:5]
        if near:
            seen.update(near)
            out.append('<p class="rel">' + e(T["contemp"].format(h=h)) + " · ".join(link_(j) for j in near) + "</p>")
    return "".join(out)

def neighbours(i, lang="en"):
    """Previous and next alphabetically -- the chain that connects every page."""
    T = L[lang]; n, parts = APOS[i], []
    if n > 0:            parts.append("&larr; " + link(ALPHA[n - 1], lang))
    parts.append(f'<a href="{BASE}/{T["dir"]}/">{T["allaz"]}</a>')
    if n < len(ALPHA) - 1: parts.append(link(ALPHA[n + 1], lang) + " &rarr;")
    return '<p class="rel nb">' + " · ".join(parts) + "</p>"

pages, index_rows = 0, []
os.makedirs("site/k", exist_ok=True)
# the hubs this artist belongs to -- their decades, media and museums -- as a line of links:
# the reader's way sideways, and the crawler's; the sets and addresses are build_hubs.py's own
import build_hubs as H
def hub_line(ws, lang):
    T = H.L[lang]
    decs = collections.Counter(("before" if H.dec_of(w) < 1800 else H.dec_of(w)) for w in ws if H.dec_of(w) is not None)
    meds = collections.Counter(val(w, "e") for w in ws if val(w, "e"))
    muss = collections.Counter(val(w, "mu") for w in ws if (w.get("kind") or "held") == "held")
    parts = []
    d_ = [f'<a href="{H.dec_href(k, lang)}">{H.dec_label(k, lang)}</a>' for k, _ in sorted(decs.items(), key=lambda kv: (kv[0] == "before" and -1 or kv[0])) if k in H.DECS]
    m_ = [f'<a href="{H.med_href(k, lang)}">{e(H.med_name(k, lang))}</a>' for k, _ in meds.most_common() if k in H.MEDS]
    u_ = [f'<a href="{H.mus_href(k, lang)}">{e(H.mus_name(k, lang))}</a>' for k, _ in muss.most_common() if k in H.MUSS]
    if d_: parts.append((T["by_dec"] if lang == "en" else T["by_dec"]) + ": " + " · ".join(d_))
    if m_: parts.append(T["by_med"] + ": " + " · ".join(m_))
    if u_: parts.append(T["by_mus"] + ": " + " · ".join(u_))
    return f'<p class="rel">{"<br>".join(parts)}</p>' if parts else ""
CHARTS = {k: v for k, v in (json.load(open("data/chart_sides.json", encoding="utf-8")) if os.path.exists("data/chart_sides.json") else {}).items() if v}
POS = {"l": "100% 50%", "r": "0% 50%", "t": "50% 100%", "b": "50% 0%"}
crop = lambda im: f' style="object-position:{POS[CHARTS[im][0]]}"' if im in CHARTS else ""
MRANK = {"Painting": 0, "Watercolour": 1, "Sculpture": 2, "Mixed media": 3, "Installation": 3, "Drawing": 4, "Sketch": 5, "Photograph": 6, "Print": 7}
def imsrc(im):
    if not im: return ""
    if im.startswith("m:"): return f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={im[2:]}"
    if im.startswith("e:"): return "https://digikogu.ekm.ee/static/preview/image/" + re.sub(r"/([^/]+)$", r"/t2_\1", im[2:])
    return im[2:]
STAMP = "<script>try{if(localStorage.getItem(\"ekr:theme\")===\"light\")document.documentElement.setAttribute(\"data-theme\",\"light\")}catch(e){}</script>"

def embed_box(lang, src, back, name, T):
    """the two lines to paste: the iframe, and the plain link that carries the credit"""
    code = (f'<iframe src="{src}" width="100%" height="230" loading="lazy" title="{name} – museaal.ee"></iframe>\n'
            f'<p><a href="{back}">{name}{" at museaal.ee" if lang == "en" else " museaal.ee-s"}</a></p>')
    return (f'<details class="emb"><summary>{T["embed_h"]}</summary><p class="m">{T["embed_t"]}</p>'
            f'<textarea readonly rows="3" spellcheck="false">{e(code)}</textarea></details>')

def render(i, a, ws, lang):
    T = L[lang]; D = T["dir"]
    sl = SLUG[i]
    me, other = f"{BASE}/{D}/{sl}.html", f"{BASE}/{L['et' if lang == 'en' else 'en']['dir']}/{sl}.html"
    life = a.get("l") or ["", ""]
    dates = f"{life[0]}–{life[1]}" if life[0] or life[1] else ""
    years = sorted({w["y"] for w in ws if w.get("y")})
    span = f"{years[0]}–{years[-1]}" if years else ""
    holders = sorted({val(w, "mu") for w in ws if val(w, "mu")})
    # the snippet names museums, in the page's language; a private collection or a
    # gallery is not where a searcher would go to see the work
    hc = {}
    for w in ws:
        h = val(w, "mu")
        if h and (w.get("kind") or "held") == "held" and h not in ("Erakogu", "Asukoht teadmata"): hc[h] = hc.get(h, 0) + 1
    top_holders = [(I18N["MUSEUM_EN"].get(h, h) if lang == "en" else h) for h, _ in sorted(hc.items(), key=lambda kv: -kv[1])[:3]]
    gal = T["gal"] if any(w.get("kind") in ("gallery", "shown", "sold") for w in ws) else ""
    # the title and the snippet in the words a searcher uses: the name, how many works,
    # where they are, what kinds, when -- and the site's own name last
    n = len(ws)
    title = f"{a['n']} – {n} {T['works']} {T['in_mus'] if gal else T['in_mus_nog']} · museaal.ee"
    d_ = dict(name=a["n"], dates=f" ({dates})" if dates else "", n=n, gal=gal, span=span, media=media_phrase(ws, lang) or T["works"],
              holders=", ".join(top_holders) if top_holders else "—")
    desc = (T["desc"] if span else T["desc_nospan"]).format(**d_)[:300]

    def holder(w):
        if w.get("kind") == "sold": return f"{e(val(w, 'mu'))} · {T['sold'] if w.get('gs') else T['gone']}"
        if w.get("kind") != "auction": return e(val(w, "mu") or "")
        out = T["soldp"].format(p=f"{w['ap']:,}") if w.get("ao") and w.get("ap") else T["soldnp"] if w.get("ao") else T["unsold"]
        return f"{e(val(w, 'mu'))} · {e(w.get('an') or '')} · {out}"
    rows = "".join(
        f"<tr><td>{e(w.get('y') or w.get('yl') or '—')}</td><td>{e(w.get('t'))}</td>"
        f"<td>{e((val(w,'tc') or val(w,'tce') or '') if lang == 'en' else (val(w,'tce') or val(w,'tc') or ''))}</td><td>{e(w.get('dm') or '')}</td>"
        f"<td>{holder(w)}</td></tr>"
        for w in sorted(ws, key=lambda x: (x.get("y") is None, x.get("y") or 0, x.get("t") or ""))[:600])
    # the artwall: the same pictures as the app, from the holders' and galleries' own
    # servers, in the app's order -- key works, then paintings before drawings before
    # prints -- capped at forty-eight, each tile a link into the app's record
    pics = [w for w in ws if w.get("im")]
    pics.sort(key=lambda w: (w.get("hl", 10**9), MRANK.get(val(w, "e"), 8), w.get("y") is None, w.get("y") or 0))
    seen_t = set(); tiles = []
    for w in pics:
        k = (w.get("t") or "").lower().strip(" .")
        if k in seen_t: continue
        seen_t.add(k); tiles.append(w)
        if len(tiles) == 48: break
    key = lambda w: w.get('k') or re.sub(r'[^A-Z0-9:]', '', (w.get('nu') or '').upper())
    wall = ("<div class=\"wall\">" + "".join(
        f"<a class=\"wt\" href=\"{BASE}/#{T['hash']}artist={sl}&open={e(key(w))}\" title=\"{e(w.get('t') or '')}\">"
        f"<img src=\"{e(imsrc(w['im']))}\" alt=\"{e(w.get('t') or '')}, {e(a['n'])}\" loading=\"lazy\"{crop(w['im'])} referrerpolicy=\"no-referrer-when-downgrade\">"
        f"<span><i>{e(w.get('t') or '')}</i><br>{e(str(w.get('y') or ''))}{' · ' if w.get('y') else ''}{e(val(w, 'mu') or '')}</span></a>"
        for w in tiles) + "</div>"
        + f"<p class=\"m\">{e(T['pics'].format(p=f'{len(pics):,}', k=len(tiles)))}</p>") if pics else ""
    lots = [w for w in ws if w.get("kind") == "auction"]
    if lots:
        ps = sorted(w["ap"] for w in lots if w.get("ao") and w.get("ap"))
        ys = sorted(int(w["ad"][:4]) for w in lots)
        au_line = T["au"].format(n=len(lots), s=sum(1 for w in lots if w.get('ao')), y=(ys[0] if ys[0]==ys[-1] else f'{ys[0]}–{ys[-1]}'),
                                 r=(f" · €{ps[0]:,} – €{ps[-1]:,}" if len(ps) > 1 and ps[0] != ps[-1] else f" · €{ps[0]:,}" if ps else ""))
    else: au_line = ""
    bio = (a.get("b") or a.get("ben")) if lang == "et" else (a.get("ben") or a.get("b"))
    bio_note = (T["mt"] if (lang == "en" and a.get("bmt") and a.get("ben")) else T["enonly"] if (lang == "et" and not a.get("b") and a.get("ben")) else "")
    grp = " · ".join(T["kind"][g.split(":",1)[0]] + " " + g.split(":",1)[1] for g in a.get("grp", []))
    app = f"{BASE}/#{T['hash']}artist={sl}"
    return (f"<!doctype html><html lang=\"{lang}\"><head><meta charset=\"utf-8\">{STAMP}"
           f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           f"<title>{e(title)}</title>"
           f"<meta name=\"description\" content=\"{e(desc)}\">"
           f"<link rel=\"canonical\" href=\"{me}\">"
           f"<link rel=\"alternate\" hreflang=\"{lang}\" href=\"{me}\"><link rel=\"alternate\" hreflang=\"{'et' if lang == 'en' else 'en'}\" href=\"{other}\">"
           f"<link rel=\"alternate\" hreflang=\"x-default\" href=\"{BASE}/a/{sl}.html\">"
           f"<meta property=\"og:type\" content=\"profile\">"
           f"<meta property=\"og:title\" content=\"{e(a['n'])}{' (' + dates + ')' if dates else ''}\">"
           f"<meta property=\"og:description\" content=\"{e(desc)}\">"
           f"<meta property=\"og:url\" content=\"{me}\">"
           f"<meta property=\"og:site_name\" content=\"{T['site']}\">"
           f"<meta property=\"og:locale\" content=\"{'en_GB' if lang == 'en' else 'et_EE'}\">"
           # a shared link shows the artist's first work -- the holder's own picture, by reference
           + (f"<meta property=\"og:image\" content=\"{e(imsrc(tiles[0]['im']))}\">"
              f"<meta property=\"og:image:alt\" content=\"{e(tiles[0].get('t') or '')}, {e(a['n'])}\">"
              f"<meta name=\"twitter:card\" content=\"summary_large_image\">" if tiles else
              f"<meta name=\"twitter:card\" content=\"summary\">")
           + f"<script type=\"application/ld+json\">{jsonld(a, ws, sl, dates, lang)}</script>"
           f"<style>{CSS}</style>{GC}</head><body>"
           f"<nav><a href=\"{BASE}/{'' if lang == 'en' else '#lang=et'}\">{T['site']}</a> › <a href=\"{BASE}/{D}/\">{T['art_nav']}</a> › {e(a['n'])} <span class=\"m\">· <a href=\"{other}\" hreflang=\"{'et' if lang == 'en' else 'en'}\">{T['other_lang']}</a></span></nav>"
           f"<h1>{e(a['n'])}</h1>"
           f"<p class=\"m\">{e(dates)}{' · ' if dates and a.get('wdesc') else ''}{e(a.get('wdesc') or '')}"
           f"{'<br>' if holders else ''}{e('; '.join(holders[:6]))}</p>"
           + (f"<p class=\"m\">{e(grp)}</p>" if grp else "")
           + ((f"<p class=\"bio\">{e(bio)}" + bio_note + "</p>") if bio else "")
           + (f"<p class=\"m\">{e(au_line)}</p>" if au_line else "")
           + f"<p><a class=\"cta\" href=\"{app}\">{e(T['browse'].format(n=n))}</a></p>"
           + wall
           + related(i, lang)
           + hub_line(ws, lang)
           + (f"<p class=\"m\">{T['first600'].format(n=f'{n:,}', u=app)}</p>" if n > 600 else "")
           + f"<table><thead><tr><th>{T['year']}</th><th>{T['title']}</th><th>{T['tech']}</th><th>{T['dims']}</th>"
           f"<th>{T['held']}</th></tr></thead><tbody>{rows}</tbody></table>"
           + neighbours(i, lang)
           + embed_box(lang, f"{BASE}/embed/{'' if lang == 'en' else 'et/'}{sl}.html", me, a["n"], T)
           + f"<p class=\"m\">{T['foot']}<a href=\"{BASE}/{'' if lang == 'en' else '#lang=et'}\">{T['full']}</a></p></body></html>")

for i, a in enumerate(A):
    ws = by_artist.get(i, [])
    if not ws: continue
    sl = SLUG[i]
    for lang in ("en", "et"):
        open(f"site/{L[lang]['dir']}/{sl}.html", "w", encoding="utf-8").write(render(i, a, ws, lang))
    pages += 1
    index_rows.append((sl, a["n"], len(ws)))

today = datetime.date.today().isoformat()
# both languages of every artist page, each naming the other (the sitemap's hreflang form)
alt = lambda sl: (f'<xhtml:link rel="alternate" hreflang="en" href="{BASE}/a/{sl}.html"/>'
                  f'<xhtml:link rel="alternate" hreflang="et" href="{BASE}/k/{sl}.html"/>')
urls = "".join(f"<url><loc>{BASE}/{D}/{sl}.html</loc><lastmod>{today}</lastmod>{alt(sl)}</url>" for sl, _, _ in index_rows for D in ("a", "k"))
open("site/sitemap.xml", "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
    f'<url><loc>{BASE}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>'
    f'<url><loc>{BASE}/a/</loc><lastmod>{today}</lastmod></url><url><loc>{BASE}/k/</loc><lastmod>{today}</lastmod></url>'
    f'<url><loc>{BASE}/stats.html</loc><lastmod>{today}</lastmod></url><url><loc>{BASE}/stats-et.html</loc><lastmod>{today}</lastmod></url>{urls}</urlset>')
open("site/robots.txt", "w", encoding="utf-8").write(
    f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

# a plain index in each language, so crawlers reach every artist page from one place
for lang in ("en", "et"):
    T = L[lang]; D = T["dir"]; O = L["et" if lang == "en" else "en"]
    lst = "".join(f'<li><a href="{BASE}/{D}/{sl}.html">{html.escape(n)}</a> <span class="m">{c}</span></li>'
                  for sl, n, c in sorted(index_rows, key=lambda r: r[1]))
    open(f"site/{D}/index.html", "w", encoding="utf-8").write(
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{STAMP}'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{T["idx_title"]}</title>'
        f'<meta name="description" content="{e(T["idx_desc"].format(n=f"{len(index_rows):,}"))}">'
        f'<link rel="canonical" href="{BASE}/{D}/"><link rel="alternate" hreflang="{lang}" href="{BASE}/{D}/"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{BASE}/{O["dir"]}/">'
        f'<style>{CSS}ul{{columns:260px;list-style:none;padding:0}}'
        f'li{{break-inside:avoid;padding:2px 0}}</style>{GC}</head><body>'
        f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{T["site"]}</a> › {T["art_nav"]} <span class="m">· <a href="{BASE}/{O["dir"]}/">{T["other_lang"]}</a></span></nav>'
        f'<h1>{T["idx_h"]}</h1><p class="m">{T["idx_n"].format(n=f"{len(index_rows):,}")}</p><ul>{lst}</ul></body></html>')

# ---- retired names: redirect stubs --------------------------------------------
# A spelling merged away in merge.py had an artist page of its own, indexed and
# bookmarked. Each old URL now carries a stub that says where the artist went and
# sends the reader there; the canonical tag tells a crawler the same.
_retired = os.path.join("data", "retired_names.json")
stubs = 0
if os.path.exists(_retired):
    live = {a["n"]: SLUG[i] for i, a in enumerate(A) if i in SLUG}
    for old, new in json.load(open(_retired, encoding="utf-8")).items():
        if new not in live: continue
        osl, nsl = slug(old), live[new]
        if osl == nsl or os.path.exists(f"{OUT}/{osl}.html"): continue
        for D in ("a", "k"): open(f"site/{D}/{osl}.html", "w", encoding="utf-8").write(
            f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><script>try{{if(localStorage.getItem(\"ekr:theme\")===\"light\")document.documentElement.setAttribute(\"data-theme\",\"light\")}}catch(e){{}}</script>"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{e(old)} — see {e(new)} — Estonian Art Catalogue</title>"
            f"<link rel=\"canonical\" href=\"{BASE}/{D}/{nsl}.html\">"
            f"<meta http-equiv=\"refresh\" content=\"0; url={BASE}/{D}/{nsl}.html\">"
            f"<meta name=\"robots\" content=\"noindex\"><style>{CSS}</style></head><body>"
            f"<nav><a href=\"{BASE}/\">Estonian Art Catalogue</a> › {e(old)}</nav>"
            f"<h1>{e(old)}</h1><p class=\"m\">This spelling has been merged. The artist is catalogued as "
            f"<a href=\"{BASE}/{D}/{nsl}.html\">{e(new)}</a> — taking you there.</p></body></html>")
        stubs += 1

# ---- 404 --------------------------------------------------------------------
# GitHub Pages serves 404.html for any missing path. A stale link usually names
# an artist, so the page offers a search prefilled from the path, and the A-Z.
open("site/404.html", "w", encoding="utf-8").write(
    f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><script>try{{if(localStorage.getItem(\"ekr:theme\")===\"light\")document.documentElement.setAttribute(\"data-theme\",\"light\")}}catch(e){{}}</script>"
    f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
    f"<title>Not found — Estonian Art Catalogue</title><meta name=\"robots\" content=\"noindex\">"
    f"<style>{CSS}form{{display:flex;gap:8px;max-width:520px;margin:18px 0}}"
    f"input{{flex:1;font:inherit;padding:8px 10px;border:1px solid #bbb}}button{{font:inherit;padding:8px 14px}}</style>{GC}</head><body>"
    f"<nav><a href=\"{BASE}/\">Estonian Art Catalogue</a> › Not found</nav>"
    f"<h1>There is no page here</h1>"
    f"<p class=\"m\" id=\"why\">The address may be misspelt, or the page has moved.</p>"
    f"<form id=\"f\"><input id=\"q\" placeholder=\"Search the catalogue\" aria-label=\"Search\"><button>Search</button></form>"
    f"<p><a href=\"{BASE}/a/\">Artists A–Z</a> · <a href=\"{BASE}/k/\">Kunstnikud A–Ü</a> · <a href=\"{BASE}/\">Full catalogue</a></p>"
    f"<script>"
    f"var m=location.pathname.match(/\\/[ak]\\/([^\\/]+?)(?:\\.html)?$/);"
    f"if(m){{var w=decodeURIComponent(m[1]).replace(/-/g,' ');document.getElementById('q').value=w;"
    f"document.getElementById('why').textContent='No artist page at this address. The name may have been merged with another spelling — try the search.';}}"
    f"document.getElementById('f').onsubmit=function(ev){{ev.preventDefault();var q=document.getElementById('q').value.trim();"
    f"location.href='{BASE}/#'+(q?'q='+encodeURIComponent(q):'');}};"
    f"</script></body></html>")

print(f"  redirect stubs {stubs:,}")
print(f"  artist pages   {pages:,} in each language (/a/ English, /k/ Estonian)")
print(f"  sitemap        {2*len(index_rows)+5:,} urls (both languages)")
print(f"  total size     {sum(os.path.getsize(os.path.join(OUT,f)) for f in os.listdir(OUT))/1048576:.1f} MB")
