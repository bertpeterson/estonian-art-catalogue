# -*- coding: utf-8 -*-
"""Idla Antiik (idla.ee) -> appends to gallery_records.json. WooCommerce; metadata only.

A Tallinn antique dealer (Old Town, Virmalise 2) whose art section "Eesti" held ~350 works in
November 2026: Soviet-era prints above all (Laarman, Okas, Vive Tolli, Lapin, Mall Vahtre), oil
paintings (Väino Paris, Kalju Nagel, Valdur Ohakas), watercolours and drawings. Read through
the WooCommerce Store API, the read-only endpoint its own pages use; robots.txt closes nothing.
Only that category (id 349): "Maalid, pildid muu maa" is foreign art.
The product name carries it all, loosely: artist, life dates, technique word, title, the
technique again and the year -- "Märt Laarman (1896-1979) graafika Laev,puulõige 1963a",
"Ermi Littover (1921-2015)Rõuge tüdruk,õli,papp 1964a", "Vello Vinn graafika Draakoni galerii,ofort
49/70 1988a". A name is taken only where life dates or a technique word end it; "Akvarell
Tallinn-Oleviste kirik ,Bruno Tomberg ?" and "Tallinna pilt 1964a, Mekinjan" are left out, and so
are lace, ceramics and the like that share the category. The short description gives the size,
mostly with the frame ("Mõõdud raamiga 48*50,5 cm"), kept so: "48 x 50,5 cm (raamiga)".
The asking price of current stock is read (asking_price.py); a sold work's never. Out of stock = sold.
"""
import json, re, ssl, time, html
from asking_price import asking
import store_api
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
API = "https://www.idla.ee/wp-json/wc/store/v1/products"
CATEGORY = 349                                                           # Kunst > Eesti
ctx = ssl.create_default_context()
from scrape_util import U
NUM = r"\d+(?:[.,]\d+)?"
# the word between name and title: "graafika", "õlimaal", "exlibris-graafika", "pliiatsijoonistus"
KIND = r"(?:exlibris-)?graafika|serigraafia|õlimaal|akvarell|guašš|tempera|pastell|segatehnika|(?:pliiatsi|tušši|söe)?joonistus"
# a comma part that is a technique, not a title: "puulõige", "õli", "papp", "ofort, akvatinta 17/20"
TECH = (r"(?:õli|papp|lõuend|masoniit|vineer|paber|akrüül|tempera|guašš|akvarell|pastell|tušš|söövitus|ofort|akvatinta|"
        r"kuivnõel|lito\w*|puulõige|linool\w*|siiditrükk|serigraafia|monotüüpia|pehmelakk|kõrgtrükk|sügavtrükk|segatehnika|"
        r"mezzotinto|metsotinto|puugravüür|kollaaž|pliiats|süsi)\b")
NOT_ART = {"eesti-keraamika", "portselan", "metallist-esemed", "tekstiilid-ja-riideesemed", "reklaamid-ja-sildid",
           "raamatud-ja-ajakirjad-eesti", "kollektsioneerimine", "maalid-pildid-muu-maa", "mereteemaline", "puidust-esemed"}

def api(page):
    return store_api.page(f"{API}?per_page=100&page={page}&category={CATEGORY}", UA, ctx, 60)   # a page not read stops the script

def artist_of(a):
    """'Roman (Espenberg) Haavamägi' -> 'Roman Haavamägi'; 'Õnne/Õnneleid-Astrid Eelma' -> 'Õnne Eelma'"""
    a = re.sub(r"\s*\([^)]*\)\s*", " ", a).strip()
    return re.sub(r"^([^\s/]+)/\S+", r"\1", a).strip(" ,")

NAME = r"(?:[A-ZÕÄÖÜŠŽ][\w-]+\.? ){1,3}?[A-ZÕÄÖÜŠŽ][\w]+"
FIX = {"Eduard Wiiralti": "Eduard Wiiralt"}                             # "Eduard Wiiralti illustratsioon ...": the genitive

def parse(name):
    """-> (artist, title, year, tech) or None: a name only where life dates, a technique word, a quoted title
    ("Maara Vint “Lootose mägi” 1990a") or a dash ("Valdur Ohakas-Sõbrannad,monotüüpia") ends it"""
    m = (re.match(r"^(.+?)\s*\((\d{4})\s*[-–]\s*(\d{4})?\)\s*(.*)$", name) or re.match(r"^(.+?)\s*\((\d{4})a?\)\s*(.*)$", name)
         or re.match(rf"^({NAME})\s+(?=(?:väike |antiikne )?(?:{KIND})\b)(.*)$", name)
         or re.match(rf"^({NAME})\s*(?=[“„\"])(.*)$", name) or re.match(rf"^({NAME})-(?=[A-ZÕÄÖÜ])(.*)$", name))
    if not m: return None
    artist, rest = artist_of(m.group(1)), m.group(m.lastindex)
    artist = FIX.get(artist, artist)
    if len(artist.split()) < 2 or re.search(r"\d|,|\bja\b|&|\?", artist) or artist.split()[0].lower() in ("akvarell", "eesti", "joonistus"): return None
    q = re.match(r"^[“„\"]\s*([^”″\"“]+?)\s*[”″\"“]\s*(.*)$", rest)        # a quoted title, the rest after it
    tech = []
    while not q:
        # what stands before the title: "graafika", "väike graafika", "antiikne akvarell", "monotüüpia", "lito"
        k = re.match(rf"^(?:väike|antiikne|värvitrükk|illustratsioon|kaart|{KIND}|{TECH})\b[\s,]*", rest, re.I)
        if not k: break
        if re.match(rf"{KIND}|{TECH}", k.group(0), re.I): tech.append(k.group(0).strip(" ,").lower())
        rest = rest[k.end():]
    y = re.search(r"\b(1[6-9]\d\d|20[0-2]\d)\s*a?\.?\b", rest)
    if q: title, rest = [q.group(1)], q.group(2)
    rest = re.sub(r"~?\b(1[6-9]\d\d|20[0-2]\d)\s*a?\.?(?=\W|$)|-\d\da\b|\d*/\d+\b|\bproov\b|\bbroneeritud\b|[”“″\"]", " ", rest, flags=re.I)
    parts = [p.strip(" .,–-") for p in rest.split(",") if p.strip(" .,–-")]
    if not q: title = []
    more = []
    for p in parts:
        # "Laev" then "puulõige"; "Kivine rand" then "söövitus"
        (more if title and re.match(rf"{KIND}|{TECH}", p, re.I) else title).append(p)
    if not title: return None
    t = title[0]
    tt = re.search(rf"\s+((?:{KIND}|{TECH}).*)$", t, re.I)                  # "Lilled 1984a õlimaal": the technique after the title
    if tt and tt.start() > 0: more.insert(0, tt.group(1)); t = t[:tt.start()]
    t = re.sub(r"\s+", " ", t).strip(" .,–-")
    if not t or re.match(rf"(?:{KIND}|{TECH})$", t, re.I): return None
    techs = [re.sub(r"\s+(?:[IVX]+|eesti)$", "", re.sub(r"\s+", " ", x), flags=re.I) for x in more if re.match(rf"{KIND}|{TECH}", x, re.I)]
    return artist, t, y.group(1) if y else None, ", ".join(techs) or ", ".join(tech)

def dims_of(text):
    m = re.search(rf"({NUM})\s*[*x×]\s*({NUM})(?:\s*[*x×]\s*({NUM}))?\s*(?:cm)?", text)
    if not m: return ""
    framed = re.search(r"raami", text[:m.start()], re.I) and not re.search(r"lehe|paspartuu", text[:m.start()], re.I)
    return " x ".join(g for g in m.groups() if g) + " cm" + (" (raamiga)" if framed else "")

recs, page, skipped = [], 1, []
while True:
    batch = api(page)
    if not batch: break
    for p in batch:
        name = U(p.get("name"))
        if {c.get("slug") for c in p.get("categories", [])} & NOT_ART: continue
        got = parse(name)
        if not got: skipped.append(name); continue
        artist, title, year, tech = got
        im = (p.get("images") or [{}])[0]
        # the 600-1024 wide copy from the srcset, not the 2000 original
        img = next((u for u, w in re.findall(r"(\S+) (\d+)w", im.get("srcset") or "") if 600 <= int(w) <= 1024), im.get("src"))
        reserved = re.search(r"broneeritud", name, re.I)                  # reserved: no asking price
        recs.append({**({} if reserved else asking(p)), "gid": f"idla-{p['id']}", "artist": artist, "title": title, "year": year,
                     "tech": tech[:80], "dims": dims_of(U(p.get("short_description"))),
                     "gallery": "Idla Antiik", "city": "Tallinn", "url": p.get("permalink") or "https://www.idla.ee",
                     **({"sold": True} if not p.get("is_in_stock", True) else {}),
                     **({"img": img} if img else {})})
    page += 1; time.sleep(1)
    if page > 10: break

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("idla-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"IDLA ANTIIK WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}  priced: {sum(1 for r in recs if r.get('price'))}  left out: {len(skipped)}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with tech {sum(1 for r in recs if r['tech'])}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
