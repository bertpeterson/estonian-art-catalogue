# -*- coding: utf-8 -*-
import json, re, collections, unicodedata, datetime, os, html
exec(open('build.py',encoding='utf-8').read().split('def esc_ess')[0])   # ESS/TECH/MAT/ED_LIFE/ED_BIO

def invkey(s):
    if not s: return None
    s = re.sub(r'[^A-Za-z0-9:]', '', s.upper())
    return s or None

# ---------- artist name hygiene ----------
# The two catalogues damage names in different, mechanical ways. MuIS marks a
# mononym or pseudonym with a leading apostrophe ("' Adamson-Eric", "pseud., ' Gori")
# and sometimes leaves a trailing semicolon; digikogu ships double spaces
# ("Otto  Krusten") and drops the closing bracket ("Gori ( Vello Agori").
# Left alone each variant becomes its own artist, splitting one body of work in two.
def clean_name(n):
    n = (n or "").strip()
    n = re.sub(r"^\s*pseud\.?,?\s*", "", n, flags=re.I)   # MuIS pseudonym prefix
    n = re.sub(r"^'\s*", "", n)                            # MuIS mononym marker
    n = re.sub(r"\s+", " ", n)                             # digikogu double spaces
    n = re.sub(r"\(\s+", "(", n)                            # "Gori ( Vello" -> "Gori (Vello"
    if n.count("(") == n.count(")") + 1: n += ")"          # restore the dropped bracket
    return n.strip(" ;,").strip()

def fold(n):
    """Match key for spelling variants of one name: accents folded, German oe/ae/ue
    collapsed, word order ignored. Deliberately requires the SAME set of words, so
    'Otto Friedrich von Moeller' and 'Otto Friedrich Theodor von Moeller' stay apart —
    a missing forename is a question about who someone is, not how it is spelled."""
    s = clean_name(n).lower()
    for a, b in (("õ","o"),("ö","o"),("ä","a"),("ü","u"),("š","s"),("ž","z")):
        s = s.replace(a, b)
    s = s.replace("oe","o").replace("ae","a").replace("ue","u")
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode()
    key = tuple(sorted(re.findall(r"[a-z0-9]+", s)))
    # "Dücker (?)" is the museum recording an UNCERTAIN attribution. Folding it into
    # the plain name would assert an authorship they declined to assert, so keep it apart.
    return key + ("?",) if "?" in n else key

# ---------- medium inference for digikogu-only records ----------
KOGU_MED = {"maalikogu":"Painting","graafikakogu":"Print","skulptuurikogu":"Sculpture",
  "joonistuste kogu":"Drawing","joonistustekogu":"Drawing","fotokogu":"Photograph",
  "nüüdiskunstikogu":"Installation","akvarellikogu":"Watercolour","plakatikogu":"Print",
  "tarbekunstikogu":"Applied art","meediakunstikogu":"Video",
  "graafika abikogu":"Print","skulptuuri abikogu":"Sculpture","maali abikogu":"Painting","joonistuste abikogu":"Drawing"}
TECH_MED = [
 # English terms too — the EKKM records are catalogued in English
 (r'video\s*installation|installation.*video', "Installation"),
 (r'\bvideo\b|film|moving image', "Video"),
 (r'installation|sculpture|object|neon|wall stencil|assemblage', "Installation"),
 (r'photo\s*sculpture|photograph|photo paper|c-print|inkjet|slide', "Photograph"),
 (r'performance|lecture-performance|action', "Performance"),
 (r'oil on|acrylic on|painting|canvas', "Painting"),
 (r'drawing|pencil on|ink on', "Drawing"),
 (r'print|silkscreen|lithograph|etching|screenprint', "Print"),
 (r'õli|akrüül|tempera|guašš|gvašš|vahatehnika|emulsioon', "Painting"),
 (r'akvarell', "Watercolour"),
 (r'ofort|litograafia|linoollõige|puulõige|serigraafia|siiditrükk|gravüür|kuivnõel|akvatint|mezzotint|ksülograafia|ofsettrükk|monotüüpia|trükk', "Print"),
 (r'pliiats|tušš|süsi|kriit|sangviin|sulejoonistus|sepia|pastell|viltpliiats|joonistus', "Drawing"),
 (r'valamine|raiumine|modelleerimine|voolimine|pronks|marmor|kips|graniit|šamott|dolomiit', "Sculpture"),
 (r'foto|fotograafia|digitaal', "Photograph"),
 (r'video|film', "Video"),
 (r'kollaaž', "Collage"),
]
def infer_med(kogu, tech, mat):
    k = (kogu or "").strip().lower()
    if k in KOGU_MED: return KOGU_MED[k]
    blob = ((tech or "") + " " + (mat or "")).lower()
    for pat, med in TECH_MED:
        if re.search(pat, blob): return med
    return "Other"

APPROX = re.compile(r'(?<![A-Za-zÕÄÖÜõäöü])(?:umbes|arvatavasti|on\s+oletatav|ca\.?|c\.|u\.?)(?=\s|$)', re.I)
def year_of(d):
    if not d: return None, None
    s = d.strip()
    # Not \b after the digits: Estonian writes a decade as "1940ndad" / "1950ndate
    # keskpaik", and a word boundary fails against the following letter, so the
    # museum's own decade was being filed as undated. Guard against digits only.
    ys = [int(x) for x in re.findall(r'(?<!\d)(1[3-9]\d\d|20[0-4]\d)(?!\d)', s)]
    if not ys: return None, s
    lab = APPROX.sub("ca", s)                 # one marker for "approximately"
    lab = re.sub(r'\s*-\s*', "–", lab)         # en dash for ranges
    lab = re.sub(r'\bca\s+(\d{4})–ca\s+(\d{4})\b', r'ca \1–\2', lab)   # ca 1913–ca 1914 -> ca 1913–1914
    lab = re.sub(r'\s{2,}', " ", lab).strip()
    # MuIS sometimes repeats the same dating phrase; keep each distinct part once
    parts, seen = [], set()
    for p in (x.strip() for x in lab.split(";")):
        if p and p.lower() not in seen: seen.add(p.lower()); parts.append(p)
    return ys[0], "; ".join(parts)

# ---------- load ----------
MU = json.load(open("records.json", encoding="utf-8"))
DK = json.load(open("dk_records.json", encoding="utf-8")) if os.path.exists("dk_records.json") else []

# Clean every artist name before anything is keyed on it, then settle on one
# spelling per person: the variant carrying the most records wins, and among
# equals the accented form wins, since that is the form the museums intend.
for r in MU + DK:
    if r.get("artist"): r["artist"] = clean_name(r["artist"])

_tally = collections.Counter(r["artist"] for r in MU + DK if r.get("artist"))

# A bracket after a name means four different things, and only one of them is a
# duplicate. "(Vello Agori)" is the real name behind a pseudonym — same person.
# "(jun.)" and "(sen.)" separate a father from a son, "(1537 - 1612) töökoda" means
# the workshop of someone rather than the artist, and "(?)" is the museum declining
# to assert the attribution at all. Only the first may be folded away.
QUALIFIER = re.compile(r"^\s*(?:jun|sen|jr|sr|juun|noorem|vanem|\?|[\d\s?/.–—-]+)\s*\.?\s*$", re.I)
def _strip_brackets(n):
    return re.sub(r"\s+", " ", re.sub(r"\s*\([^)]*\)\s*", " ", n)).strip()
def bare_of(n):
    """The name without its alias brackets, or None when a bracket is not an alias."""
    inners = re.findall(r"\(([^)]*)\)", n)
    if not inners or any(QUALIFIER.match(i) for i in inners): return None
    return _strip_brackets(n) or None

_keys = {n: fold(n) for n in _tally}
_present = set(_keys.values())
# a bare form is ambiguous if some sibling distinguishes itself from it with jun./sen.
_ambiguous = {fold(_strip_brackets(n)) for n in _tally
              if any(QUALIFIER.match(i) for i in re.findall(r"\(([^)]*)\)", n))}
for n in list(_keys):
    b = bare_of(n)
    if b:
        bk = fold(b)
        if bk in _present and bk not in _ambiguous: _keys[n] = bk

_variants = collections.defaultdict(list)
for n, k in _keys.items(): _variants[k].append(n)
CANON = {}
for group in _variants.values():
    best = max(group, key=lambda n: (_tally[n], sum(ord(c) > 127 for c in n), n))
    for n in group: CANON[n] = best
MERGED_NAMES = sum(len(g) - 1 for g in _variants.values() if len(g) > 1)
for r in MU + DK:
    if r.get("artist"): r["artist"] = CANON.get(r["artist"], r["artist"])

unified = {}       # invkey or synthetic -> record
def blank():
    return {"src": set(), "artist": None, "t": None, "date": None, "tech": None, "mat": None,
            "dims": None, "museum": None, "coll": None, "num": None, "desc": None,
            "ess": None, "cat": None, "muis": None, "oid": None}

for r in MU:
    k = invkey(r.get("num")) or ("M" + r["id"])
    u = unified.setdefault(k, blank())
    u["src"].add("muis"); u["artist"] = r["artist"]
    u["t"] = r["title"]; u["date"] = r.get("date"); u["tech"] = r.get("tech")
    u["mat"] = r.get("mat"); u["dims"] = r.get("dims"); u["museum"] = r.get("museum")
    u["coll"] = r.get("collection"); u["num"] = r.get("num"); u["desc"] = r.get("desc")
    u["ess"] = r.get("essence"); u["muis"] = r["id"]

for r in DK:
    num = " ".join(x for x in [r.get("Tulmenumber"), r.get("Kogunumber")] if x).strip()
    k = invkey(num) or ("D" + r["oid"])
    u = unified.setdefault(k, blank())
    u["src"].add("ekm")
    u["oid"] = r["oid"]
    u["cat"] = r.get("Kategooriad") or u["cat"]
    if not u["artist"]: u["artist"] = r["artist"]
    if not u["t"]:      u["t"] = (r.get("Pealkiri") or "").strip() or None
    if not u["date"]:   u["date"] = r.get("Dateering")
    if not u["tech"]:   u["tech"] = r.get("Tehnika")
    if not u["mat"]:    u["mat"] = r.get("Materjal")
    if not u["dims"]:   u["dims"] = r.get("Mõõdud")
    if not u["num"]:    u["num"] = num or None
    if not u["museum"]: u["museum"] = r.get("Varaline kuuluvus") or "Eesti Kunstimuuseum SA"
    if not u["coll"]:   u["coll"] = r.get("EKM kogu")
    if not u["ess"]:    u["ess"] = None
    u["_kogu"] = r.get("EKM kogu")

for k, u in unified.items():
    u["k"] = k
    if u["museum"]: u["museum"] = re.sub(r'\s+SA$', '', u["museum"].strip())
    if u["museum"] and "muuseum" not in u["museum"].lower() and "ekm" in u["src"] and "muis" not in u["src"]:
        u["coll"] = (u["coll"] or "") + " · deposit, owner: " + u["museum"]
        u["museum"] = "Eesti Kunstimuuseum"
# A trailing "(?)" is the museum recording that it does not actually know who made
# this — "Otto Dix (?)" sits in their catalogue beside works firmly given to Dix.
# The catalogue takes attributed work only, and an attribution the holder will not
# assert is not one, so these come out on the same rule that excludes anonymous work.
# The bracketed form is not the only one — the same doubt is written as a bare
# trailing "?" ("Magnus Zeller?"). Requiring a capitalised word or a closing bracket
# before it keeps the one name that genuinely ends in a question mark: the collective
# Chto delat / What is to be done?, where the "?" follows a lowercase word.
UNCERTAIN = re.compile(r'(?:\(\s*\?\s*\)|(?:[A-ZÕÄÖÜŠŽ][^\s]*|\))\s*\?)\s*$')
_before = [u for u in unified.values() if u["artist"] and u["t"]]
recs = [u for u in _before if not UNCERTAIN.search(u["artist"])]
DROPPED_UNCERTAIN = len(_before) - len(recs)
print("  dropped as uncertain attribution:", DROPPED_UNCERTAIN,
      "objects /", len({u["artist"] for u in _before if UNCERTAIN.search(u["artist"])}), "names")

# ---------- artists ----------
by_artist = collections.defaultdict(list)
for r in recs: by_artist[r["artist"]].append(r)

# a catalogue note quoting an outside source is not a biography
BAD_BIO = re.compile(r'^(väljavõte|katkend|allikas|tsitaat|refereeritud|vt\.?\s)|https?://|www\.|facebook', re.I)
MU_LIFE, MU_BIO = {}, {}
for r in MU:
    if r.get("life") and r["artist"] not in MU_LIFE: MU_LIFE[r["artist"]] = r["life"]
    if r.get("bio") and not BAD_BIO.search(r["bio"]):
        b = MU_BIO.get(r["artist"])
        if not b or len(r["bio"]) > len(b): MU_BIO[r["artist"]] = r["bio"]
AU = json.load(open("dk_authors.json", encoding="utf-8")) if os.path.exists("dk_authors.json") else {}
def au_life(a):
    b = re.search(r'(\d{4})', a.get("Sündinud", "") or ""); d = re.search(r'(\d{4})', a.get("Surnud", "") or "")
    return [b.group(1), d.group(1) if d else ""] if b else None
def au_bio(a):
    parts = []
    if a.get("Sündinud"): parts.append("Sündinud " + a["Sündinud"] + (", " + a["Sünnikoht"] if a.get("Sünnikoht") else ""))
    if a.get("Surnud"):   parts.append("surnud " + a["Surnud"] + (", " + a["Surmakoht"] if a.get("Surmakoht") else ""))
    head = "; ".join(parts)
    edu = a.get("Haridus", "")
    if edu: head += (". " if head else "") + "Haridus: " + "; ".join(x.strip() for x in edu.split("\n") if x.strip())[:320]
    return head.strip() or None
DK_LIFE = {}
for r in DK:
    a = r.get("Autor") or ""
    m = re.search(r'\((\d{3,4})\s*[-–]\s*(\d{3,4})?\)', a)
    if m and r["artist"] not in DK_LIFE: DK_LIFE[r["artist"]] = [m.group(1), m.group(2) or ""]

artists, aidx = [], {}
for name in sorted(by_artist, key=lambda n: (n.split()[-1], n)):
    au = AU.get(name, {})
    life, ls = MU_LIFE.get(name), "muis"
    if not life: life, ls = au_life(au), "ekm"
    if not life: life, ls = DK_LIFE.get(name), "ekm"
    if not life: life, ls = ED_LIFE.get(name), "ed"
    bio, bs = MU_BIO.get(name), "muis"
    if not bio: bio, bs = au_bio(au), "ekm"
    if not bio: bio, bs = ED_BIO.get(name), "ed"
    aidx[name] = len(artists)
    artists.append({"n": name, "l": life or ["", ""], "ls": ls if life else "ed",
                    "b": (bio or "")[:1200], "bs": bs if bio else "ed", "ai": au.get("aid")})

def term(v, table):
    if not v: return None
    parts = [p.strip() for p in re.split(r'[;,\n]', v) if p.strip()]
    return "; ".join(table.get(p.lower(), p) for p in parts[:3])

def ess_en(e, kogu, tech, mat):
    if e:
        first = re.split(r'[;/]', e)[0].strip().lower()
        if first in ESS: return ESS[first]
        if first: return first.capitalize()
    return infer_med(kogu, tech, mat)

def tkey(t):
    t = unicodedata.normalize('NFKD', t.lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', t)
groups = collections.OrderedDict()
for r in recs:
    y, _ = year_of(r.get("date"))
    g = (r["artist"], tkey(r["t"]), y)
    groups.setdefault(g, []).append(r)
OBJECTS = len(recs)
recs = []
for g, members in groups.items():
    members.sort(key=lambda r: (0 if "muis" in r["src"] else 1, r.get("num") or ""))
    rep = dict(members[0]); rep["n"] = len(members)
    if len(members) > 1:
        rep["mem"] = [[m.get("num") or "", (m.get("tech") or "").split(";")[0].strip(),
                       (m.get("date") or ""), m.get("muis") or "", m.get("oid") or ""]
                      for m in members]
    rep["src"] = set().union(*(m["src"] for m in members))
    if not rep.get("muis"): rep["muis"] = next((m.get("muis") for m in members if m.get("muis")), None)
    if not rep.get("oid"):  rep["oid"]  = next((m.get("oid")  for m in members if m.get("oid")),  None)
    if not rep.get("cat"):  rep["cat"]  = next((m.get("cat")  for m in members if m.get("cat")),  None)
    recs.append(rep)

# Some cataloguers put the date of making at the end of the title and left the
# dating field empty. Recover only a year appended at the very end, and only when
# it is possible for that artist's lifespan. Descriptions are NOT mined: their
# years are conservation dates and sitters' birthdates, not dates of making.
TITLE_YEAR = re.compile(r'[.,;]\s*(1[5-9]\d\d|20[0-4]\d)\s*(?:a\.?|aasta)?\s*[.)]?\s*$')

works = []
for r in recs:
    y, lab = year_of(r.get("date"))
    dsrc = "museum" if y else None
    if y is None:
        m = TITLE_YEAR.search(r["t"])
        if m:
            ty = int(m.group(1))
            al = artists[aidx[r["artist"]]]["l"]
            b = int(al[0]) if al[0] else None
            dd = int(al[1]) if al[1] else 2026
            if b is None or (b + 12 <= ty <= dd + 2):
                y, lab, dsrc = ty, str(ty), "title"
    works.append({
      "a": aidx[r["artist"]], "t": r["t"].strip(),
      "y": y, "yl": lab, "dsrc": dsrc,
      "e": ess_en(r.get("ess"), r.get("_kogu") or r.get("coll"), r.get("tech"), r.get("mat")),
      "ee": (re.split(r'[;/]', r["ess"])[0].strip() if r.get("ess") else None),
      "tc": term(r.get("tech"), TECH), "tce": r.get("tech"),
      "m": term(r.get("mat"), MAT), "me": r.get("mat"),
      "dm": r.get("dims"), "mu": r.get("museum"), "co": r.get("coll"),
      "nu": r.get("num"), "d": r.get("desc"), "c": r.get("cat"),
      "s": "".join(sorted(r["src"])), "mi": r.get("muis"), "oi": r.get("oid"), "k": r["k"], "n": r["n"],
      "mem": r.get("mem")})

for i, a in enumerate(artists):
    a["c"] = sum(1 for w in works if w["a"] == i)


# ---------- CCA artist biographies, Venice pavilion, EKKM collection ----------
CE = json.load(open("cca_ekkm.json", encoding="utf-8")) if os.path.exists("cca_ekkm.json") else {"artists":[],"venice":[],"ekkm":[]}
def toks(n):
    n = unicodedata.normalize('NFKD', (n or "").lower())
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return tuple(sorted(t for t in re.split(r'[^a-z0-9]+', n) if len(t) > 1))
by_tok = {toks(a["n"]): i for i, a in enumerate(artists)}

def artist_index(name, bio_en=None):
    """Find an artist, or add one. Returns index or None for unusable names."""
    t = toks(name)
    if not t: return None
    if t in by_tok: return by_tok[t]
    artists.append({"n": name.strip(), "l": ["", ""], "ls": "ed", "b": "", "bs": "ed",
                    "ai": None, "c": 0, "ben": bio_en, "bens": "cca" if bio_en else None})
    by_tok[t] = len(artists) - 1
    return by_tok[t]

# English biographies, written by the field rather than by me
CCA_BIO = {toks(a["name"]): a["bio"] for a in CE["artists"] if a.get("bio")}
for a in artists:
    b = CCA_BIO.get(toks(a["n"]))
    if b: a["ben"], a["bens"] = b, "cca"
    else: a.setdefault("ben", None); a.setdefault("bens", None)

SPLIT = re.compile(r'\s*(?:,| and | ja |\(|\))\s*')
def people(who):
    who = re.sub(r'^John Smith\s*', '', who or "")
    return [p.strip() for p in SPLIT.split(who) if len(p.strip()) > 3]

for v in CE["venice"]:
    for person in people(v["who"]):
        ai = artist_index(person, CCA_BIO.get(toks(person)))
        if ai is None: continue
        works.append({"a": ai, "t": v["title"] or f"Estonian Pavilion, Venice Biennale {v['year']}",
            "y": v["year"], "yl": str(v["year"]), "dsrc": "museum",
            "e": "Installation", "ee": None, "tc": None, "tce": None, "m": None, "me": None,
            "dm": None, "mu": "Veneetsia biennaal, Eesti paviljon", "co": f"{v['year']}",
            "nu": None, "d": v["blurb"], "c": None, "s": "cca", "mi": None, "oi": None,
            "k": "V" + str(v["year"]) + "-" + str(ai), "n": 1, "mem": None,
            "kind": "shown", "url": ("https://cca.ee/en/venice-biennale/" + v["slug"]) if v.get("slug") else "https://cca.ee/en/venice-biennale"})

for e in CE["ekkm"]:
    ai = artist_index(e["artist"])
    if ai is None: continue
    works.append({"a": ai, "t": e["title"] or "—", "y": e.get("year"),
        "yl": str(e["year"]) if e.get("year") else None, "dsrc": "museum" if e.get("year") else None,
        "e": infer_med(None, e.get("medium"), e.get("medium")), "ee": None,
        "tc": e.get("medium"), "tce": e.get("medium"), "m": None, "me": None,
        "dm": None, "mu": "Eesti Kaasaegse Kunsti Muuseum", "co": "EKKM kollektsioon",
        "nu": None, "d": e.get("desc"), "c": None, "s": "ekkm", "mi": None, "oi": None,
        "k": "E" + re.sub(r'[^a-z0-9]', '', e["url"].rstrip("/").split("/")[-1]), "n": 1,
        "mem": None, "kind": "shown" if False else "held", "url": e["url"]})

# Wikidata citizenship, where it exists. Deliberately kept as a list: these artists
# lived under changing states, so "Estonia + Russian Empire + Soviet Union" is the
# honest answer, not a single nationality we pick for them.
WD = json.load(open("wd_artists.json", encoding="utf-8")) if os.path.exists("wd_artists.json") else {}
WDD = json.load(open("wd_desc.json", encoding="utf-8")) if os.path.exists("wd_desc.json") else {}
AFF = [(r'baltic[- ]german','Baltic German'),(r'estonian[- ]swedish','Estonian-Swedish'),
       (r'estonian','Estonian'),(r'\bswedish','Swedish'),(r'\brussian','Russian'),(r'\bgerman','German'),
       (r'\bswiss','Swiss'),(r'\bfinnish','Finnish'),(r'\bpolish','Polish'),(r'\blatvian','Latvian'),
       (r'\bdutch','Dutch'),(r'\bfrench','French'),(r'\bitalian','Italian'),(r'\bamerican','American'),
       (r'\bbritish|\benglish','British'),(r'\bsoviet','Soviet'),(r'\bukrainian','Ukrainian')]
def affil(t):
    t = (t or "").lower()
    for pat, lab in AFF:
        if re.search(pat, t): return lab
    return None
# Look the artist up under the canonical name, then under the name with its alias
# brackets removed — "Gori (Vello Agori)" is filed in Wikidata as plain "Gori".
def wd_get(table, name):
    return table.get(name) or (table.get(_strip_brackets(name)) if "(" in name else None)

def yr4(s):
    m = re.match(r'^(\d{4})', str(s or ""))
    return int(m.group(1)) if m else None

# Wikidata is matched on the name label alone, and names collide: a 17th-century
# Tallinn woodcarver and a German biologist born in 1964 are both "Christian
# Ackermann". The museum's own dates are the anchor — a candidate whose birth year
# contradicts them is a different person, not a better record.
def wd_plausible(a, rec):
    if not rec: return False
    b = yr4(rec.get("byear"))
    if b is None:
        # No structured birth year, but the description usually carries one.
        # Allow a wide margin: sources genuinely disagree by a few years about when
        # Clara Peeters was born. A decade-plus apart is a different person.
        m = re.search(r'\((?:born\s+)?(\d{4})', rec.get("desc") or "")
        born = (a.get("l") or ["", ""])[0]
        if m and yr4(born): return abs(int(m.group(1)) - yr4(born)) <= 15
        return True                                 # nothing to check
    born, died = (a.get("l") or ["", ""])[:2]
    mb, md = yr4(born), yr4(died)
    if mb is not None: return abs(b - mb) <= 3
    if md is not None: return md - 110 < b < md     # born within a lifetime of dying
    return True                                     # museum has no dates either

WD_REJECTED = WD_CONFLICT = 0
for a in artists:
    w, v = wd_get(WD, a["n"]), wd_get(WDD, a["n"])
    if w and not wd_plausible(a, w): w = None; WD_REJECTED += 1
    if v and not wd_plausible(a, v): v = None; WD_REJECTED += 1
    # The two passes query independently and can land on different people. If they
    # disagree and the museum's dates cannot say which is right, we do not know who
    # this is — better to show nothing than to attach the wrong person's life.
    if w and v and w.get("qid") and v.get("qid"):
        wb, vb = yr4(w.get("byear")), yr4(v.get("byear"))
        # Different people under one name, or one record reporting two birth years
        # for the same person — either way the identity is not established.
        if w["qid"] != v["qid"] or (wb and vb and abs(wb - vb) > 3):
            WD_CONFLICT += 1
            w = v = None
    if w:
        if w.get("cit"): a["cit"] = w["cit"]
        if w.get("qid"): a["qid"] = w["qid"]
        if w.get("born"): a["born"] = w["born"]
    if v:
        a["wdesc"] = v["desc"]
        if not a.get("qid"): a["qid"] = v.get("qid")
        f = affil(v["desc"])
        if f: a["aff"] = f
print("  wikidata rejected on date contradiction:", WD_REJECTED)
print("  wikidata dropped as unresolvable conflict:", WD_CONFLICT)

# ---------- commercial galleries ----------
# These are NOT museum holdings: the work is in private hands or for sale, and the
# gallery is its current venue rather than an owner with an accession number. They
# carry kind="gallery" so a visitor can always tell the two apart, and every record
# links back to the gallery's own page. Prices are deliberately not collected.
GAL = json.load(open("gallery_records.json", encoding="utf-8")) if os.path.exists("gallery_records.json") else []
gal_added = 0
# Each gallery parser decoded its own shortlist of HTML entities, which let
# "&#8220;" and "&#8221;" through into titles. Decode the lot here instead, once.
for g in GAL:
    for f in ("artist", "title", "tech", "dims"):
        if g.get(f): g[f] = re.sub(r'\s+', ' ', html.unescape(g[f])).strip()
    ai = artist_index(g["artist"])
    if ai is None or not g.get("title"): continue
    y = int(g["year"]) if g.get("year") and g["year"].isdigit() else None
    tech = g.get("tech") or None
    works.append({"a": ai, "t": g["title"], "y": y,
        "yl": g.get("year") or None, "dsrc": "gallery" if y else None,
        "e": infer_med(None, tech, tech), "ee": None,
        "tc": tech, "tce": tech, "m": None, "me": None,
        "dm": g.get("dims") or None, "mu": g["gallery"], "co": None,
        "nu": None, "d": None, "c": None, "s": "gallery", "mi": None, "oi": None,
        "k": "G" + re.sub(r'[^A-Za-z0-9]', '', g["gid"]), "n": 1,
        "mem": None, "kind": "gallery", "url": g.get("url")})
    gal_added += 1
print("  gallery works added:", gal_added,
      "from", len({g["gallery"] for g in GAL}), "galleries")

for w in works: w.setdefault("kind", "held")
for i, a in enumerate(artists): a["c"] = sum(1 for w in works if w["a"] == i)

data = {"meta": {"built": datetime.date.today().isoformat(),
                 "works": len(works), "objects": OBJECTS, "artists": len(artists),
                 "held": sum(1 for w in works if w["kind"]=="held"),
                 "shown": sum(1 for w in works if w["kind"]=="shown"),
                 "gallery": sum(1 for w in works if w["kind"]=="gallery"),
                 "galleries": len({w["mu"] for w in works if w["kind"]=="gallery"}),
                 "cca_bios": sum(1 for a in artists if a.get("bens")=="cca"),
                 "with_origin": sum(1 for a in artists if a.get("cit")),
                 "with_aff": sum(1 for a in artists if a.get("aff")),
                 "dated": sum(1 for w in works if w["y"]),
                 "dated_from_title": sum(1 for w in works if w.get("dsrc") == "title"),
                 "undated": sum(1 for w in works if w["y"] is None),
                 "muis": sum(1 for w in works if "muis" in w["s"]),
                 "ekm": sum(1 for w in works if "ekm" in w["s"]),
                 "both": sum(1 for w in works if w["s"] == "ekmmuis")},
        "artists": artists, "works": works}
# 26k works x a dozen empty fields is megabytes of "null" — drop them; JS sees undefined either way
def prune(o):
    return {k: v for k, v in o.items() if v not in (None, "", [], {})}
data["works"] = [prune(w) for w in data["works"]]
data["artists"] = [prune(a) for a in data["artists"]]

# A few dozen strings (museum, collection, medium, technique, material, source, category)
# were being written out once per work. Store each once and reference it by index.
DICT_FIELDS = ["mu", "co", "e", "ee", "tc", "tce", "m", "me", "s", "c"]
vocab = {f: [] for f in DICT_FIELDS}
index = {f: {} for f in DICT_FIELDS}
for w in data["works"]:
    for f in DICT_FIELDS:
        v = w.get(f)
        if v is None: continue
        if v not in index[f]:
            index[f][v] = len(vocab[f]); vocab[f].append(v)
        w[f] = index[f][v]
# the two defaults do not need storing at all
for w in data["works"]:
    if w.get("kind") == "held": w.pop("kind", None)
    if w.get("dsrc") == "museum": w.pop("dsrc", None)
# the row key is just the inventory number with punctuation stripped — derive it in the
# page instead of shipping both. Only synthetic keys (records with no number) are kept.
def derive(nu):
    return re.sub(r'[^A-Za-z0-9:]', '', (nu or "").upper()) or None
for w in data["works"]:
    if w.get("nu") and derive(w["nu"]) == w.get("k"): w.pop("k", None)
data["vocab"] = vocab
data["meta"]["encoded"] = DICT_FIELDS
json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("data.json", os.path.getsize("data.json")//1024, "KB")
for k, v in data["meta"].items(): print(" ", k, v)
dec = collections.Counter((w["y"]//10*10) for w in works if w["y"])
print("decades:", " ".join(f"{k}s:{v}" for k, v in sorted(dec.items())))
print("media:", collections.Counter(w["e"] for w in works).most_common(14))
print("museums:", collections.Counter(w["mu"] for w in works).most_common(8))
print("categories:", collections.Counter(w["c"] for w in works if w["c"]).most_common(14))
