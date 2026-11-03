# -*- coding: utf-8 -*-
"""A work's sales history: the times one picture was sold or offered, matched by picture
-> sales_history.json  {"chains": [{"m": 0|1, "w": [work keys], "x": [Auctionet lots]}], "city": {house: city}}

Every past and coming auction lot here (the Estonian houses), every gallery listing, current
or past, the museum records and the Konrad Mägi catalogue, and Auctionet's ended lots of our
artists (Stockholm, Göteborg, Helsinki ...): two of them are one work when they are by the
same artist and CLIP finds the pictures alike at cosine CUT or more. Chains are joined
transitively, so Endel Kõks's "Damer och knektar", sold on Auctionet in 2015, and the same
canvas at Allee in 2021 are one chain, and a lot that later entered a museum ends in it.

A print, a cast or a poster is not one object: another impression of the same print is
another sheet. Such chains are marked m=1 and the site shows them as "other impressions",
never as one object's history.

The cut: different works photographed the same way -- sketches with MuIS's grey-scale strip,
an auction house's studio backdrop -- reach 0.95. Pairs from 0.90 to CUT were checked by eye
(2026-11-03): see CUT below. Pictures one house uses for many works (a "no picture" card)
are dropped: a picture that is near-identical to pictures of three or more artists.

Auctionet lots come from its public API (ended lots, searched by the artist's surname as
the sleeper scan did), cached in cache/auctionet.json; pictures are read, embedded with
CLIP ViT-B/32 on this machine and discarded, the vectors cached in embcache/sales.npy by
picture address. Nothing from a foreign lot is shown on the site but its facts and link.
Run with the venv after new auction or gallery records:  .venv-clip/bin/python sales_history.py
(from data/; --fetch to search Auctionet for artists not searched before)
"""
import json, os, re, sys, io, time, collections, datetime, unicodedata, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np

# Checked by eye on 2026-11-03, 20 pairs a band: from 0.94 to 0.96 nearly all one work, the misses
# sheets of a series ("92" and "93"); from 0.92 to 0.94 prints are nearly all one print, other
# work mostly a series' siblings (Runge's "Arhitektoon 3" and "7", Koplimets's "Aftermath I", "II")
CUT = 0.95            # one object: same artist, cosine at least this
CUT_MULTI = 0.92      # one print or cast, either side by its medium or its Auctionet title
CUT_ABROAD = 0.92     # an Auctionet lot against an Estonian one: two photographers, two lights --
                      # Kõks's "Damer och knektar" and Allee's "Emandad ja teenijad" are 0.921,
                      # while the same-house siblings that fail at 0.92-0.95 share one photographer
CUT_MUSEUM = 0.96     # a museum record's photograph against a sale: MuIS's strips and backdrops
PLACEHOLDER = 0.99    # a picture this close to three artists' pictures is a house's stock card
UA = "Mozilla/5.0 (compatible; museaal.ee sales history; one request a second)"
AN_CACHE, VEC, VEC_IDS = "cache/auctionet.json", "embcache/sales.npy", "embcache/sales_ids.json"
MULTI = {"Print", "Bookplate", "Poster", "Sculpture", "Relief", "Medal", "Figurine", "Illustration", "Linoollõige", "Litograafia"}
# Auctionet titles name the technique in Swedish, Finnish, German or English
AN_MULTI = re.compile(r"etch|etsn|etsau|radier|lith|litogr|woodcut|wood engrav|träsnitt|trägravyr|puupiir|puugrav|holzschn|linol|"
                      r"screen|serigr|grafi|graphic|druck|aquat|akvat|drypoint|torrnål|kuivneul|mezzo|ofort|gravyr|engrav|"
                      r"brons|bronze|skulptur|sculpt|gips|plaster|poster|affisch", re.I)
CITY = ["Stockholm", "Göteborg", "Malmö", "Helsinki", "Helsingfors", "Lund", "Linköping", "Sundsvall", "Norrköping", "Helsingborg",
        "Halmstad", "Växjö", "Örebro", "Borås", "Vänersborg", "Västervik", "Kalmar", "Nyköping", "Karlstad", "Uppsala", "Västerås",
        "Gävle", "Jönköping", "Umeå", "Visby", "Copenhagen", "København", "Turku", "Tampere", "Berlin", "Hamburg", "Wien"]
CITY_OF = {"Stockholms": "Stockholm", "Göteborgs": "Göteborg", "Helsingborgs": "Helsingborg", "Halmstads": "Halmstad",
           "Örebro": "Örebro", "Kolonn": "Stockholm", "Metropol": "Stockholm", "Garpenhus": "Lund", "Ekenbergs": "Stockholm",
           "Roslagens": "Norrtälje", "Hälsinglands": "Hudiksvall", "Bukowskis": "Stockholm", "Formstad": "Lund"}

def city(house):
    for c in CITY:
        if c in house: return "Helsinki" if c == "Helsingfors" else c
    return next((v for k, v in CITY_OF.items() if house.startswith(k)), "")

def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as f: return f.read()
        except Exception:
            if k == tries - 1: raise
            time.sleep(3 * (k + 1))

d = json.load(open("data.json", encoding="utf-8"))
W, A, V = d["works"], d["artists"], d["vocab"]
alnum = lambda s: re.sub(r"[^A-Za-z0-9]", "", s)
# the Estonian houses' and galleries' cities, as the galleries' own records give them; an
# auction house with no gallery record and no known address (an online sale) has none
CITY_EE = {"Vaal galerii": "Tallinn"} | {g["gallery"]: g["city"] for f in ("gallery_records.json", "gallery_past.json")
                                         for g in json.load(open(f, encoding="utf-8")) if g.get("city")}
AU_IMG = {"A" + alnum(r["aid"]): r.get("img") for r in json.load(open("auction_records.json", encoding="utf-8"))}
GA_IMG = {"G" + alnum(g["gid"]): g.get("img") for f in ("gallery_records.json", "gallery_past.json")
          for g in json.load(open(f, encoding="utf-8"))}

# ---- Auctionet: ended lots of our artists, searched by surname --------------------------------
def spellings(name):
    n = re.sub(r"\(.*?\)", "", name).split(); sur = n[-1]
    plain = "".join(c for c in unicodedata.normalize("NFKD", sur) if not unicodedata.combining(c))
    de = sur.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("õ", "oe")
    out = {sur, plain, de, re.sub(r"([aeiou])\1", r"\1", plain)}
    if plain[0] in "VvWw": out |= {"W" + plain[1:], "V" + plain[1:]}
    return sorted(out)

fold = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
LOOSE = re.compile(r"circle of|krets|school|skola|manner|after|efter|nach |kopia|copy|attrib|tillskriv|umkreis|werkstatt|follower", re.I)

def an_artist(title, cands):
    """the artist a lot's title names: first name (or its initial) and surname before the first full stop"""
    if LOOSE.search(title): return None
    head = fold(re.split(r"[.(]", title)[0] if "." in title[:60] else title[:60])
    hits = []
    for a in cands:
        n = re.sub(r"\(.*?\)", "", a).split()
        if len(n) < 2 or not any(fold(s) in head for s in spellings(a)): continue
        if fold(n[0]) in head or re.search(r"\b" + re.escape(fold(n[0])[0]) + r"\b", head): hits.append(a)
    return hits[0] if len(hits) == 1 else None

an = json.load(open(AN_CACHE, encoding="utf-8")) if os.path.exists(AN_CACHE) else {"done": [], "lots": {}}
if "--fetch" in sys.argv:
    sales = collections.Counter(A[w["a"]]["n"] for w in W if w.get("kind") == "auction")
    by_sur = collections.defaultdict(list)
    for a in sales: by_sur[fold(re.sub(r"\(.*?\)", "", a).split()[-1])].append(a)
    done = set(an["done"])
    for a, n in sales.most_common():
        if n < 3: break
        for q in spellings(a):
            if q.lower() in done: continue
            page, pages = 1, 1
            while page <= min(pages, 10):
                try: r = json.loads(get("https://auctionet.com/api/v2/items.json?" + urllib.parse.urlencode(
                        {"is": "ended", "q": q, "per_page": 100, "page": page})))
                except Exception as e: print(f"  {q}: {e!r}"); break
                pages = r["pagination"]["total_pages"]
                for x in r["items"]:
                    who = an_artist(x.get("title") or "", by_sur[fold(re.sub(r"\(.*?\)", "", a).split()[-1])])
                    if not who: continue
                    b = x.get("bids") or []
                    an["lots"][str(x["id"])] = dict(id=x["id"], artist=who, title=x.get("title") or "", house=x.get("house"),
                        cur=x.get("currency"), top=b[0]["amount"] if b else None, state=x.get("state"), ends=x.get("ends_at"),
                        url=x.get("url"), img=(x.get("images") or [{}])[0].get("w640"))
                page += 1; time.sleep(1)
            done.add(q.lower())
        an["done"] = sorted(done); json.dump(an, open(AN_CACHE, "w"), ensure_ascii=False)
print(f"Auctionet: {len(an['lots']):,} ended lots of our artists", flush=True)

# ---- the items: everything with a picture -----------------------------------------------------
museum_ids = json.load(open("embcache/ids.json")); museum_pos = {k: i for i, k in enumerate(museum_ids)}
museum_E = np.load("embcache/emb.npy")
pic = lambda im: im and (im[2:] if im.startswith("g:") else None)
items = []      # (artist, kind, key, picture address or museum picture id)
for w in W:
    a, kd = A[w["a"]]["n"], w.get("kind")
    if kd == "auction": u = AU_IMG.get(w.get("k")) or pic(w.get("im")); src = "au"
    elif kd in ("gallery", "sold"): u = pic(w.get("im")) or GA_IMG.get(w.get("k")); src = "ga"
    elif kd in (None, "known") and w.get("im") in museum_pos: u = w["im"]; src = "mu"
    else: continue
    if u and w.get("k" if src != "mu" else "im"): items.append(dict(a=a, src=src, w=w, u=u))
names = {x["n"] for x in A}
for x in an["lots"].values():
    if x.get("img") and x["artist"] in names: items.append(dict(a=x["artist"], src="an", x=x, u=x["img"]))
print(f"items: {collections.Counter(i['src'] for i in items)}", flush=True)

# ---- vectors: the museum pictures from embcache/, the rest read here and cached by address ----
E0 = np.load(VEC) if os.path.exists(VEC) else np.zeros((0, 512), np.float16)
ids0 = json.load(open(VEC_IDS)) if os.path.exists(VEC_IDS) else []
have = {u: n for n, u in enumerate(ids0)}
todo = sorted({i["u"] for i in items if i["src"] != "mu" and i["u"] not in have})
print(f"pictures: {len(have):,} embedded before, {len(todo):,} to read", flush=True)
if todo:
    import torch, open_clip
    from PIL import Image
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    model = model.to(dev).eval()
    def fetch(u):
        try:
            img = Image.open(io.BytesIO(get(urllib.parse.quote(u, safe=":/?=&%+~@"), tries=2)))
            img.draft("RGB", (448, 448)); return u, pre(img.convert("RGB"))
        except Exception: return u, None
    new_u, new_v, bu, bt, t0 = [], [], [], [], time.time()
    def flush():
        if not bt: return
        with torch.no_grad():
            f = model.encode_image(torch.stack(bt).to(dev)).float(); f = f / f.norm(dim=-1, keepdim=True)
        new_v.append(f.cpu().numpy().astype(np.float16)); new_u.extend(bu); bu.clear(); bt.clear()
    with ThreadPoolExecutor(8) as ex:
        for n, (u, t) in enumerate(ex.map(fetch, todo), 1):
            if t is not None: bu.append(u); bt.append(t)
            if len(bt) == 64: flush()
            if n % 1000 == 0:
                print(f"  {n:,}/{len(todo):,} ({n / (time.time() - t0):.0f}/s)", flush=True)
    flush()
    if new_v: E0 = np.concatenate([E0] + new_v); ids0 = ids0 + new_u
    np.save(VEC, E0); json.dump(ids0, open(VEC_IDS, "w"))
    have = {u: n for n, u in enumerate(ids0)}
items = [i for i in items if (i["u"] in museum_pos if i["src"] == "mu" else i["u"] in have)]
X = np.stack([museum_E[museum_pos[i["u"]]] if i["src"] == "mu" else E0[have[i["u"]]] for i in items]).astype(np.float32)
X /= np.linalg.norm(X, axis=1, keepdims=True)

# ---- stock cards: one picture behind three or more artists' sales ----------------------------
sale = np.array([i["src"] != "mu" for i in items])
si = np.where(sale)[0]; art = np.array([i["a"] for i in items])
card = set()
for s in range(0, len(si), 2000):
    blk = si[s:s + 2000]; S = X[blk] @ X[si].T
    for r, j in enumerate(blk):
        near = si[S[r] >= PLACEHOLDER]
        if len(set(art[near])) >= 3: card.add(j)
print(f"stock cards dropped: {len(card)}", flush=True)

# ---- pairs: same artist, at least one of them a sale or an offer -----------------------------
EMED = V["e"]
def multi_of(i):
    if "x" in i: return bool(AN_MULTI.search(i["x"]["title"]))
    return isinstance(i["w"].get("e"), int) and EMED[i["w"]["e"]] in MULTI
MUL = np.array([multi_of(i) for i in items])
# two titles that differ only in a number are two sheets of a series: "Arhitektoon 3", "Arhitektoon 7"
numless = lambda t: re.sub(r"\b([ivxl]+|\d+[a-z]?)\b", "#", re.sub(r"[^\w\s]", " ", str(t or "").lower())).split()
def series(i, j):
    if "w" not in i or "w" not in j: return False
    a, b = str(i["w"].get("t") or "").lower().strip(), str(j["w"].get("t") or "").lower().strip()
    return a != b and numless(a) == numless(b) and "#" in numless(a)
by = collections.defaultdict(list)
for n, i in enumerate(items):
    if n not in card: by[i["a"]].append(n)
par = {}
def find(x):
    while par.setdefault(x, x) != x: par[x] = par[par[x]]; x = par[x]
    return x
pairs, band = collections.Counter(), []
for a, ns in by.items():
    ns = np.array(ns); s_ = ns[sale[ns]]
    if not len(s_): continue
    S = X[s_] @ X[ns].T
    for r, c in zip(*np.where(S >= 0.90)):
        i, j = s_[r], ns[c]
        if i == j or (sale[j] and j < i): continue
        src = {items[i]["src"], items[j]["src"]}
        cut = CUT_MUSEUM if "mu" in src else CUT_MULTI if MUL[i] or MUL[j] else CUT_ABROAD if len(src) == 2 and "an" in src else CUT
        if S[r, c] < 0.96: band.append((float(S[r, c]), int(i), int(j)))
        if S[r, c] < cut or series(items[i], items[j]): continue
        pairs[tuple(sorted((items[i]["src"], items[j]["src"])))] += 1
        ri, rj = find(i), find(j)
        if ri != rj: par[max(ri, rj)] = min(ri, rj)
print(f"pairs: {dict(pairs)}", flush=True)
if "--band" in sys.argv:      # the pairs below the safe level, for a look by eye
    json.dump([dict(cos=c, a=items[i]["a"], i=items[i]["u"], j=items[j]["u"], si=items[i]["src"], sj=items[j]["src"],
                    ti=(items[i].get("w") or items[i].get("x"))["t" if "w" in items[i] else "title"],
                    tj=(items[j].get("w") or items[j].get("x"))["t" if "w" in items[j] else "title"]) for c, i, j in band],
              open(sys.argv[sys.argv.index("--band") + 1], "w"), ensure_ascii=False, indent=0)

groups = collections.defaultdict(list)
for n in par: groups[find(n)].append(n)
# the work's key as build_site.py reads it
mkey = lambda i: i["w"].get("k") or re.sub(r"[^A-Z0-9:]", "", (i["w"].get("nu") or "").upper())
chains = []
for g in groups.values():
    g = [items[n] for n in sorted(g)]
    if not any(i["src"] != "an" for i in g) or len(g) < 2: continue
    multi = any(multi_of(i) for i in g)
    ws = sorted({mkey(i) for i in g if "w" in i} - {""})
    xs = sorted(({"d": datetime.datetime.fromtimestamp(x["ends"]).strftime("%Y-%m-%d") if x.get("ends") else "",
                  "h": x["house"], "c": city(x["house"] or ""), "cur": x["cur"], "p": x["top"],
                  "o": int(x["state"] == "sold" and bool(x["top"])), "u": x["url"], "t": x["title"][:160]}
                 for x in (i["x"] for i in g if "x" in i)), key=lambda e: e["d"])
    if len(ws) + len(xs) < 2: continue
    chains.append(dict(a=g[0]["a"], m=int(multi), w=ws, x=xs))
chains.sort(key=lambda c: (c["a"], c["w"]))
json.dump({"chains": chains, "city": dict(sorted(CITY_EE.items()))}, open("sales_history.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
size = collections.Counter(min(len(c["w"]) + len(c["x"]), 6) for c in chains)
print(f"sales_history.json: {len(chains)} chains ({sum(c['m'] for c in chains)} of prints or casts), "
      f"{sum(1 for c in chains if c['x'])} with an Auctionet lot; sizes {dict(sorted(size.items()))}")
