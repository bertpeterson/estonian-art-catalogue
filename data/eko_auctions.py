# -*- coding: utf-8 -*-
"""Eesti Kunsti Oksjonid (EKO) results -> auction_records.json (house: Eesti Kunsti Oksjonid)

EKO runs online sales that close in the room, twenty or so since 2023, and keeps each
sale's page up with the outcome on every lot: "Lõpppakkumine 5000 € (14)" is the
final bid and the number of bids; "Lõpppakkumine - (0)" a lot nobody bid on;
"Müüdud 3300 € (0)" one sold after the sale at its starting price. The lot line
carries artist, title, year and size ("Arnold Alas “Öine Tallinna vaade” 1963,
96×80"); the card adds the medium and the size without and with frame.

The house prints no sale date on the page. Each lot's own page carries the date the
lot was listed, a fortnight or so before the sale, and the sale's name often carries
the day ("Sügisoksjon 25.10."); the two together place the sale. Lot pages are cached;
a sale still running has no results and is left until it has.
"""
import re, json, os, gzip, time, html, datetime, urllib.request, ssl, collections

BASE = "https://eestikunstioksjonid.ee"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "gcache"
os.makedirs(CACHE, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=45, context=ctx) as f:
                return f.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404: return ""
            if attempt == 2: print("ERR", url, e.code, flush=True); return ""
            time.sleep(3 * (attempt + 1))
        except Exception as e:
            if attempt == 2: print("ERR", url, repr(e)[:70], flush=True); return ""
            time.sleep(3 * (attempt + 1))

def get(url, key):
    p = os.path.join(CACHE, key + ".html.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    h = fetch(url)
    if h:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    time.sleep(0.8)
    return h

clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

# The houses set sale names in capitals; that is the poster, not the name. Sentence
# case, keeping roman numerals and the houses' own initials.
def sentence(s):
    letters = re.findall(r"[A-Za-zÄÖÜÕäöüõŠŽšž]", s or "")
    if len(letters) < 4 or sum(c.isupper() for c in letters) < 0.5 * len(letters): return s
    keep = {"I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XX","XXX","XL","L","EKO","EML","EKA","EKL","MM","M&M"}
    proper = {"eesti","haus","galerii","kuressaare","kuursaalis","pärnu","tallinn","tartu","eduard","wiiralt","riho","sibula",
              "debora","vaarandi","mall","nukke","wiiralti","kunstiakadeemia","art&tonic","viimsi","artiumis","kontserdimajas","suvepealinna"}
    out = []
    for i, w in enumerate(re.split(r"(\s+)", s)):
        if not w.strip(): out.append(w); continue
        core = w.strip(",.:;()\"„“”")
        if core in keep or re.fullmatch(r"[IVXL]+", core): out.append(w)
        elif i == 0 or core.lower() in proper or (out and out[-2].endswith((":", ".", "-", "–"))): out.append(w[:1] + w[1:].lower())
        else: out.append(w.lower())
    return "".join(out)
# Arnold Alas “Öine Tallinna vaade” 1963, 96×80  /  Jüri Arrak (1936-2022) “Kolmik”, 2020a  /
# Arkadio Laigo, Mapp ”Tartu näitusplats” 1936a  /  Jüri Arrak, Lend 1983a.
LOT = re.compile(r"^(?P<a>[^“”\"„]+?)\s*,?\s*[“”\"„]\s*(?P<t>.+?)\s*[”\"“]\s*,?\s*(?P<rest>.*)$", re.S)
LOT2 = re.compile(r"^(?P<a>[^,]+),\s*(?P<t>.+?)\s+(?P<rest>(?:\d{4}|\d{2}ndad).*)$", re.S)
def split_lot(line):
    m = LOT.match(line) or LOT2.match(line)
    if not m: return None
    a = re.sub(r"\([^)]*\)", " ", m.group("a"))                   # "(1936-2022)" is a life, not a name
    a = re.sub(r"(\s+[a-zäöüõšž][^\s]*)+$", "", re.sub(r"\s+", " ", a).strip(" ,"))   # "Lepo Mikko triptühhon"
    if len(a) > 3 and a == a.upper():                                      # one sale typed its artists in capitals
        a = " ".join(w if w.lower() in ("von", "van", "de") else w[:1] + w[1:].lower() for w in a.split(" "))
    return a, m.group("t").strip(), m.group("rest")
SALE_NOISE = re.compile(r"täname.*$|\s+\d{1,2}\.\d{1,2}\.\d{4}.*$|LÕPPENUD!?|on lõppenud\.?|edukalt lõppenud\.?|^\s*\d{1,2}\.\d{1,2}\.(?:\s*\d{2,4}\.?)?\s*|^\s*\d{1,2}\.\s*[a-zõäöü]+il,?\s*|\s*[–-]\s*$", re.I)
OUTCOME = re.compile(r'(Lõpppakkumine|Müüdud)</div>\s*<div>\s*<span class="uk-text-bolder">\s*([\d\s]*?)\s*(?:&euro;|€)?\s*(?:-\s*)?</span>\s*(?:<span[^>]*>\s*\((\d+)\)\s*</span>)?', re.S)

home = fetch(f"{BASE}/")
slugs = []
for s in re.findall(r'href="(?:' + BASE + r')?/k/oksjonid/([^/"]+)/"', home):
    if s not in slugs: slugs.append(s)
print(f"EKO: {len(slugs)} sales linked", flush=True)

today = datetime.date.today()
recs, n_open, n_unparsed = [], 0, 0
for slug in slugs:
    lots, page, sale, day = [], 1, None, None
    while True:
        u = f"{BASE}/k/oksjonid/{slug}/" + (f"page/{page}/" if page > 1 else "")
        h = fetch(u); time.sleep(0.8)
        if not h: time.sleep(5); h = fetch(u)
        if not h: break
        if sale is None:
            m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
            sale = clean(m.group(1)) if m else slug
            dm = re.search(r"(\d{1,2})\.(\d{1,2})\.?(?:\s*(\d{2,4})\b)?", sale) or re.search(r"(\d{1,2})-(\d{1,2})(?:-(\d{4}|\d{2}))?(?:/|$)", slug)
            for _ in range(3): sale = SALE_NOISE.sub("", sale).strip(" ,.–-!")
            sale = sentence(sale)
            day = dm.groups() if dm else None
        cards = re.split(r'(?=<div class="single_product_ product_)', h)[1:]
        if not cards: break
        lots += [c.split('<hr class="uk-divider-small')[0] for c in cards]
        if f"/k/oksjonid/{slug}/page/{page + 1}/" not in h: break
        page += 1
    if not lots: continue
    if not any(OUTCOME.search(c) for c in lots): n_open += 1; continue   # still running: no results yet
    got, months = [], collections.Counter()
    for c in lots:
        url = re.search(r'href="(' + BASE + r'/o/[^"]+)"', c)
        title = re.search(r'<h5 class="uk-link" title="([^"]*)"', c)
        pid = re.search(r"\bpost-(\d+)\b", c)
        st = re.search(r'data-startprice="([\d.]+)"', c)
        oc = OUTCOME.search(c)
        if not (url and title and pid and oc): n_unparsed += 1; continue
        lm = split_lot(clean(title.group(1)))
        if not lm or not re.match(r"^[^\d]{3,60}$", lm[0]): n_unparsed += 1; continue
        artist, ltitle, rest = lm
        yl = re.split(r",|\s(?=\d+\s*[×x]\s*\d+)", rest, 1)[0].strip(" ,.")
        if not re.search(r"\d{4}|ndad|saj", yl): yl = ""
        y4 = re.search(r"(\d{4})", yl)
        med = re.search(r'fa-palette"></i></span>\s*<span>([^<]*)</span>', c)
        dm = re.search(r'fa-ruler"></i></span>\s*<span>([^<]*)</span>', c)
        dims = clean(dm.group(1)).split("/")[0] if dm else ""          # the work, not the frame
        dims = re.search(r"\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?", dims)
        dims = (re.sub(r"\s*[x×]\s*", " x ", dims.group(0)).replace(",", ".") + " cm") if dims else ""
        label, price, bids = oc.group(1), re.sub(r"\D", "", oc.group(2) or ""), oc.group(3)
        hammer = int(price) if price else None
        sold = hammer is not None
        after = sold and (label == "Müüdud" or bids == "0")                 # sold after the sale, no bid in it
        lp = get(url.group(1), f"ekoauc_{pid.group(1)}")
        pub = re.search(r'"datePublished":"(\d{4}-\d{2})-(\d{2})', lp or "")
        if pub: months[pub.group(1)] += 1
        got.append({"aid": "eko-" + pid.group(1), "artist": artist, "title": ltitle,
                    "year": y4.group(1) if y4 else None, "yl": yl or None, "tech": clean(med.group(1)) if med else "", "dims": dims,
                    "house": "Eesti Kunsti Oksjonid", "sale": sale,
                    "start": int(float(st.group(1))) if st else None, "hammer": hammer, "sold": sold, "after": after, "url": url.group(1)})
    # the sale's month: when its lots were listed, moved to the day the name gives
    ym = months.most_common(1)[0][0] if months else None
    if ym and day:
        y, mo = int(ym[:4]), int(day[1])
        if day[2]: y = int(day[2]) + (2000 if int(day[2]) < 100 else 0)
        elif mo < int(ym[5:7]): y += 1
        when = f"{y}-{mo:02d}-{int(day[0]):02d}"
    else: when = ym or ""
    if when and when[:7] > today.isoformat()[:7]: n_open += 1; continue
    for r in got: r["when"] = when[:7]; r["date"] = when
    recs += got
    print(f"  {when:10} {sale[:44]:44} lots {len(got)}", flush=True)

recs.sort(key=lambda r: (r["date"], r["artist"], r["title"]))
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump([r for r in prev if r["house"] != "Eesti Kunsti Oksjonid"] + recs, open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
sold = [r for r in recs if r["sold"]]
print(f"\nEKO AUCTION RESULTS: {len(recs)}   sold {len(sold)}   unsold {len(recs) - len(sold)}   sales {len({r['sale'] for r in recs})}")
print(f"  sales still open {n_open}, lots unparsed {n_unparsed}, with medium {sum(1 for r in recs if r['tech'])}, with dims {sum(1 for r in recs if r['dims'])}, undated sale {sum(1 for r in recs if not r['date'])}")
for r in recs[:3] + recs[-3:]:
    print(f"   {r['date']:10} {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':5} {r['tech'][:16]:16} start {r['start']!s:>6} hammer {r['hammer']!s:>6}")
