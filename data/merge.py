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
 (r'\boil\b|acrylic|painting|canvas|gouache', "Painting"),
 (r'collage', "Collage"),
 (r'drypoint|linocut|woodcut|aquatint|mezzotint|engraving|monotype|offset', "Print"),
 (r'\bpen\b|sulepea|charcoal|pastel|graphite|felt-tip|marker', "Drawing"),
 (r'fabric|embroider|tikitud|tekstiil|textile|wool|linen|appliqu', "Textile"),
 (r'drawing|pencil on|ink on', "Drawing"),
 (r'print|silkscreen|lithograph|etching|screenprint', "Print"),
 # NOBA and the galleries use the bare category word, not a technique
 (r'^\s*(maal|painting|maalikunst)\b', "Painting"),
 (r'^\s*(graafika|graphics|printmaking|trükigraafika)\b', "Print"),
 (r'^\s*(skulptuur|sculpture|keraamika|ceramics?)\b', "Sculpture"),
 (r'^\s*(joonistus|drawing)\b', "Drawing"),
 (r'^\s*(foto|photography|photo)\b', "Photograph"),
 (r'^\s*(installatsioon|installation)\b', "Installation"),
 (r'^\s*(segatehnika|mixed media)\b', "Mixed media"),
 (r'^\s*(tekstiil|textile|vaip|tapestry)\b', "Textile"),
 (r'^\s*(tänavakunst|street art)\b', "Street art"),
 (r'^\s*(digitaalkunst|digital art|digitaal)\b', "Digital"),
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
    # A range wider than a generation is a period, not a year. "ca 1800–1899" is the
    # cataloguer writing "19th century" in digits, and filing it at its first year put
    # Helene von Wrangell's ox-cart, painted after 1835, in the 1800s beside the
    # Baroque. Keep the museum's words as the label; give it no single year. The app
    # reads the century off a same-century range, as it does off "18. saj".
    # Tested on the normalised label, not the raw string: "umbes 1800 - umbes 1899" has
    # a marker before each year, and only after folding is it a plain range.
    m = re.search(r'(?<!\d)(1[3-9]\d\d|20[0-4]\d)\s*[-–]\s*(?:ca\s+)?(1[3-9]\d\d|20[0-4]\d)(?!\d)', lab)
    if m and int(m.group(2)) - int(m.group(1)) > 30: return None, "; ".join(parts)
    return ys[0], "; ".join(parts)

# ---------- load ----------
MU = json.load(open("records.json", encoding="utf-8"))
# ...and the collections read later through MuIS's OAI-PMH service (muis_oai.py), in
# the same shape; an id the page harvest already holds is not read twice there
if os.path.exists("oai_records.json"):
    _oai = json.load(open("oai_records.json", encoding="utf-8")); _have = {r["id"] for r in MU}
    _oai = [r for r in _oai if r["id"] not in _have and r.get("artist")]   # attributed works only, as everywhere
    MU += _oai
    print("  MuIS records through OAI-PMH:", len(_oai))
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

# The same painting can sit in both catalogues under accession numbers written
# differently -- MuIS "EKM j 153:105 M 86", digikogu "EKM j 153/1231 M 86" -- and so
# escape the join above, to appear twice, once with each photograph. What the two
# share is the collection number EKM gives the object, "M 86", unique within a
# collection letter; the same artist and that number is the same object. A digikogu
# record left on its own is joined to the one MuIS record of that artist with that
# number, when there is exactly one.
_tail = lambda num: (lambda m: (m.group(1).upper(), m.group(2)) if m else None)(re.search(r"\b([A-Za-z]{1,2})\s?(\d+)\s*$", num or ""))
_bycoll = collections.defaultdict(list)
for k, u in unified.items():
    if u["src"] == {"muis"} and u["num"] and u["artist"] and "kunstimuuseum" in (u["museum"] or "").lower() and "eesti" in (u["museum"] or "").lower():
        t = _tail(u["num"])
        if t: _bycoll[(" ".join(fold(u["artist"])), t)].append(k)
_joined = 0
for k in [k for k, u in unified.items() if u["src"] == {"ekm"} and u["artist"]]:
    u = unified[k]
    t = _tail(u["num"]) or (lambda kg: _tail(kg) if kg else None)(None)
    cands = _bycoll.get((" ".join(fold(u["artist"])), t)) if t else None
    if not cands or len(cands) != 1 or "ekm" in unified[cands[0]]["src"]: continue
    m = unified[cands[0]]
    m["src"].add("ekm"); m["oid"] = u["oid"]; m["cat"] = u["cat"] or m["cat"]; m["_kogu"] = u.get("_kogu")
    for f in ("t", "date", "tech", "mat", "dims", "coll"):
        if not m[f]: m[f] = u[f]
    del unified[k]; _joined += 1
print("  digikogu records joined to their MuIS twin by collection number:", _joined)

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

# "Tundmatu kunstnik" — literally "unknown artist" — is not a name, it is the absence
# of one, written into the name field instead of left empty. It arrived as a single
# artist holding 485 works, which the attributed-only rule never caught because the
# field was not blank. It comes out on that same rule.
#
# The notnames stay. "Püha Lucia legendi meister", "Nürnbergi meister IBK", "Meister B
# täringuga" look anonymous and are not: a notname is the conventional identifier for
# a master whose hand is recognised across several works but whose name is lost. That
# is an attribution, and art history treats it as one.
# The OAI export writes the absence of a name in more ways than the pages did --
# "teadmata", "Tundmatu meister", "Tundmatu 19. sajandi kunstnik", ". tundmatu" -- and
# every one of them is the same absence.
ANON = {"tundmatu kunstnik"}
# A firm is not an artist either: a printing house, a publisher, a factory, a company
# (Verlag von Franz Kluge, F. Schwabe trükikoda, Visible Solutions OÜ). The workshop of
# a named master -- Cranach, Notke, Goltzius -- is an attribution and stays.
_FIRM = re.compile(r"\b(trükikoda|trükk|kirjastus|verlag|druckerei|tehas|tööstus|vabrik|kombinaat|aktsiaselts|osaühing|OÜ|O\.?/ü\.?|A/S|Ltd|GmbH|Solutions)\b|&", re.I)
_anon = lambda n: n.strip().lower() in ANON or re.match(r"^\W*(tundmatu|teadmata|anonüüm)\b", n.strip(), re.I) is not None or not re.match(r"^\w", n.strip()) or (_FIRM.search(n) is not None and not re.search(r"töökoda|ateljee", n, re.I))
_before = [u for u in unified.values() if u["artist"] and u["t"]]
recs = [u for u in _before
        if not UNCERTAIN.search(u["artist"]) and not _anon(u["artist"])]
DROPPED_ANON = sum(1 for u in _before if _anon(u["artist"]))
print("  dropped as unattributed:", DROPPED_ANON, "objects /", len(ANON), "names")
DROPPED_UNCERTAIN = sum(1 for u in _before if UNCERTAIN.search(u["artist"]))
print("  dropped as uncertain attribution:", DROPPED_UNCERTAIN,
      "objects /", len({u["artist"] for u in _before if UNCERTAIN.search(u["artist"])}), "names")

# ---------- artists ----------
by_artist = collections.defaultdict(list)
for r in recs: by_artist[r["artist"]].append(r)

# a catalogue note quoting an outside source is not a biography
BAD_BIO = re.compile(r'^(väljavõte|katkend|allikas|tsitaat|refereeritud|vt\.?\s)|https?://|www\.|facebook', re.I)
MU_LIFE, MU_BIO = {}, {}
# The biography an artist's records agree on. The longest was taken before, and for
# Johann Köler that was a life of Jesus: one record of a Christ painting carried the
# sitter's biography in the artist's field, 121 carried Köler's. Majority first, and
# length only to settle a tie.
# MuIS puts the sitter's biography in the same field as the maker's: a sculpture of
# Lurich carries Lurich's life, a Christ carries a life of Jesus. So a text that turns
# up under several artists belongs to the one whose records carry it most, and to
# nobody else; Amandus Adamson's five bio-bearing records (Köler's life twice,
# Jesus twice, Lurich once) leave him rightly without one.
_bios = collections.defaultdict(collections.Counter)
for r in MU:
    if r.get("life") and r["artist"] not in MU_LIFE: MU_LIFE[r["artist"]] = r["life"]
    if r.get("bio") and not BAD_BIO.search(r["bio"]): _bios[r["artist"]][r["bio"].strip()] += 1
_owner = {}                                           # bio text -> the artist it belongs to
for a, c in _bios.items():
    for b, n in c.items():
        if b not in _owner or n > _bios[_owner[b]][b]: _owner[b] = a
# ...and a text that opens "Georg Lurich (22 April 1876" is a life of Georg Lurich,
# whoever's record it sits on: a two-or-three-word name followed by a bracketed date
# names its subject, and if none of those words is in the artist's name it is not theirs.
_SUBJ = re.compile(r"^((?:[A-ZÄÖÜÕŠŽ][^\s(]*\s+){1,2}[A-ZÄÖÜÕŠŽ][^\s(]*)\s*\(\s*(?:\d|s\.|sünd)")
def _other_person(bio, artist):
    m = _SUBJ.match(bio)
    if not m: return False
    words = lambda t: {"".join(fold(x)) for x in re.findall(r"[^\W\d_]+", t) if len(x) > 2}
    return not (words(m.group(1)) & words(artist))
for a, c in _bios.items():
    mine = [b for b in c if _owner[b] == a and not _other_person(b, a)]
    if mine: MU_BIO[a] = max(mine, key=lambda b: (c[b], len(b)))
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

# Source records that are wrong on their face -- a death before a birth -- corrected
# here and tagged editorial, so the tag on the page says who is asserting the date.
# EKM's author string reads "Karl Pavlovitš Brüllov (1799 - 1582)": Bryullov died in
# 1852, digits transposed. Ivan Velts "(1866 - 1826)" died in 1926.
LIFE_FIX = {"Karl Pavlovitš Brüllov": ["1799", "1852"], "Ivan Augustinovitš Welz": ["1866", "1926"],
            "Lucas Conrad Pfandzelt": ["1716", "1786"]}   # MuIS has "178" for the death year

# ---------- one person, two spellings ----------
# The spelling pass above folds accents and alias brackets. It cannot see that
# "Johan Köler" and "Johann Köler" are one man, or that "Erich Kügelgen" and "Erich
# von Kügelgen" are, each with his own page and half his works. The evidence that
# they are is the birth year: the same year, the same surname, and first names a
# letter apart or one a subset of the other. Names with a workshop, copy or
# attribution qualifier never merge -- a workshop is not its master.
PARTICLE = {"von", "van", "de", "der", "den", "du", "la", "le", "da", "di", "af", "zu", "und", "ja"}
NEVER = re.compile(r"töökoda|workshop|ateljee|koolkond|järgi|koopia|manner|ring|\?|\bja\b|&", re.I)   # a duo is two people
def _life_of(name, src=False):
    for life, ls in ((LIFE_FIX.get(name), "ed"), (MU_LIFE.get(name), "muis"), (au_life(AU.get(name, {})), "ekm"),
                     (DK_LIFE.get(name), "ekm"), (ED_LIFE.get(name), "ed")):
        if life: return (life, ls) if src else life
    return (None, None) if src else None
LIFE_FROM_VARIANT = {}   # the surviving spelling had no dates; the absorbed one did
def _byear(name):
    l = _life_of(name); m = re.match(r"^\s*(\d{4})", str(l[0]) if l else "")
    return int(m.group(1)) if m else None
def _ftok(t):
    """fold() returns a sorted tuple of words for whole names; one word folds to one string.
    C and K, W and V, X and KS are one letter in Estonian spelling of a foreign name --
    Carl/Karl, Alexander/Aleksander, Woldemar/Voldemar -- and fold together here."""
    k = fold(t); k = k[0] if k else ""
    return re.sub(r"^c", "k", k.replace("x", "ks").replace("w", "v"))
def _toks(n):
    n = re.sub(r"\b(sen|jun|jr|sr|vanem|noorem)\.?\b", " ", _strip_brackets(n), flags=re.I)
    # a hyphenated given name (Peeter-Adolf) or surname (Bergmann-Vardi) splits into its parts
    return [_ftok(t) for t in re.findall(r"[^\s.,\-]+", n) if _ftok(t) and _ftok(t) not in PARTICLE]
def _close(a, b):
    """Equal, or one edit apart: Johann/Johan, Vive/Viive, Mathias/Matthias; an initial
    matches the name it starts (K. -- Karin)."""
    if a == b: return True
    if len(a) == 1 or len(b) == 1: return a[0] == b[0]
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 3: return False
    if len(a) == len(b): return sum(x != y for x, y in zip(a, b)) == 1
    lo, hi = (a, b) if len(a) < len(b) else (b, a)
    return any(hi[:i] + hi[i+1:] == lo for i in range(len(hi)))
def _qual(n):
    """Which generation a name claims: sr, jr, or none. Father and son share a name."""
    if re.search(r"\b(jun|jr|juun|noorem)\b", n, re.I): return "jr"
    if re.search(r"\b(sen|sr|vanem)\b", n, re.I): return "sr"
    return None
def _same_person(x, y):
    tx, ty = _toks(x), _toks(y)
    if len(tx) < 2 or len(ty) < 2 or tx[-1] != ty[-1] or not _close(tx[0], ty[0]): return False
    if NEVER.search(x) or NEVER.search(y) or _qual(x) != _qual(y): return False
    lo, hi = (tx, ty) if len(tx) <= len(ty) else (ty, tx)
    # every token of the shorter name has a close match in the longer, in order
    j = 0
    for t in lo:
        while j < len(hi) and not _close(t, hi[j]): j += 1
        if j == len(hi): return False
        j += 1
    bx, by = _byear(x), _byear(y)
    if bx and by: return bx == by
    # no year to check: the same length and letter-close, or the shorter name lying
    # wholly inside the longer -- Vladimir Bogatkin in Vladimir Valerianovitš Bogatkin
    return len(tx) == len(ty) or (len(lo) >= 2 and len(lo[0]) > 1)
_bysur = collections.defaultdict(list)
for n in by_artist: 
    t = _toks(n)
    if len(t) >= 2: _bysur[t[-1]].append(n)
SPELLINGS = []
for names in _bysur.values():
    names = sorted(names, key=lambda n: -len(by_artist[n]))
    for i, big in enumerate(names):
        if big not in by_artist: continue
        for small in names[i+1:]:
            if small in by_artist and _same_person(big, small) and not (
                    len(_toks(small)[0]) == 1 and sum(1 for n in names if n in by_artist and n != small and _same_person(n, small)) > 1):
                for r in by_artist.pop(small): r["artist"] = big; by_artist[big].append(r)
                if not _life_of(big) and _life_of(small): LIFE_FROM_VARIANT[big] = _life_of(small, src=True)
                SPELLINGS.append((small, big))
print("  merged as one person under two spellings:", len(SPELLINGS))
# The retired spellings had artist pages of their own, indexed and bookmarked.
# build_pages.py turns each into a redirect to the surviving page.
json.dump({small: big for small, big in SPELLINGS}, open("retired_names.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
for small, big in SPELLINGS: print("     %-38s -> %s" % (small, big))

artists, aidx = [], {}
for name in sorted(by_artist, key=lambda n: (n.split()[-1], n)):
    au = AU.get(name, {})
    life, ls = MU_LIFE.get(name), "muis"
    if not life: life, ls = au_life(au), "ekm"
    if not life: life, ls = DK_LIFE.get(name), "ekm"
    if not life: life, ls = ED_LIFE.get(name), "ed"
    if not life and name in LIFE_FROM_VARIANT: life, ls = LIFE_FROM_VARIANT[name]
    if name in LIFE_FIX: life, ls = LIFE_FIX[name], "ed"
    bio, bs = MU_BIO.get(name), "muis"
    if not bio: bio, bs = au_bio(au), "ekm"
    if not bio: bio, bs = ED_BIO.get(name), "ed"
    aidx[name] = len(artists)
    artists.append({"n": name, "l": life or ["", ""], "ls": ls if life else "ed",
                    "b": (bio or "")[:2400], "bs": bs if bio else "ed", "ai": au.get("aid")})

def term(v, table):
    if not v: return None
    parts = [p.strip() for p in re.split(r'[;,\n]', v) if p.strip()]
    return "; ".join(table.get(p.lower(), p) for p in parts[:3])
# a gallery's or house's technique line mixes technique and support -- "Õli, lõuend",
# "Söövitus paberil", "Akrüül lõuendil" -- so both tables serve it, and the Estonian
# locative ("paberil", "lõuendil": on paper, on canvas) is read as its noun
TECHMAT = {**MAT, **TECH, "lõuendil": "on canvas", "paberil": "on paper", "papil": "on board", "kartongil": "on card",
           "vineeril": "on plywood", "masoniidil": "on masonite", "puidul": "on wood", "klaasil": "on glass", "metallil": "on metal",
           "siidil": "on silk", "plaadil": "on panel", "graafika": "print", "maal": "painting", "skulptuur": "sculpture", "joonistus": "drawing",
           "foto": "photograph", "printmaking": "print", "painting": "painting", "oil on canvas": "oil on canvas"}
# the museums' material phrases carry qualifiers the tables do not know: "paber
# (dubleeritud lõuendile)", "kips (patineeritud; pronksi imitatsioon)". Word by word
# after the phrase tables, so the English side reads "paper (laid down on canvas)"
MATWORD = {"dubleeritud": "laid down", "kleebitud": "mounted", "papile": "on board", "pappalusele": "on a card support", "lõuendile": "on canvas",
           "paberile": "on paper", "alusele": "on a support", "puidule": "on wood", "vineerile": "on plywood", "plastikule": "on plastic", "klaasile": "on glass",
           "patineeritud": "patinated", "raamitud": "framed", "klaasitud": "glazed", "lamineeritud": "laminated", "imitatsioon": "imitation", "pronksi": "bronze",
           "kullatud": "gilded", "hõbetatud": "silvered", "värvitud": "painted", "toonitud": "tinted", "krunditud": "primed", "poleeritud": "polished",
           "portselan": "porcelain", "fotopaber": "photographic paper", "tsink": "zinc", "akvarellpaber": "watercolour paper", "tselluloid": "celluloid",
           "kalka": "tracing paper", "taimparknahk": "vegetable-tanned leather", "puu": "wood", "terrakota": "terracotta", "fajanss": "faience", "luu": "bone",
           "tehismaterjal": "synthetic material", "akrüül": "acrylic", "riie": "cloth", "kartong": "card", "papp": "board", "paber": "paper", "lõuend": "canvas",
           "kips": "plaster", "vineer": "plywood", "masoniit": "masonite", "klaas": "glass", "metall": "metal", "puit": "wood", "pronks": "bronze", "savi": "clay",
           "siid": "silk", "vill": "wool", "lina": "linen", "nahk": "leather", "teras": "steel", "vask": "copper", "hõbe": "silver", "kuld": "gold", "kivi": "stone",
           "graniit": "granite", "marmor": "marble", "dolomiit": "dolomite", "paekivi": "limestone", "betoon": "concrete", "plastik": "plastic", "kumm": "rubber",
           "email": "enamel", "keraamika": "ceramic", "tekstiil": "textile", "kangas": "fabric", "puuvill": "cotton", "ja": "and", "või": "or", "peal": "on",
           "vesimärk": "watermark", "õhuke": "thin", "paks": "thick", "leht": "sheet", "ülemise": "top", "servaga": "edge", "ülemist": "top", "serva": "edge",
           "pidi": "along the", "ülaäärt": "top edge", "aluspaberile": "to a backing sheet", "aluspapile": "to a backing board", "kõrgkuumus": "high-fired",
           "pronksivärviliseks": "bronze-coloured", "pürokseniit": "pyroxenite", "all": "lower", "vasakul": "left", "paremal": "right", "üleval": "upper",
           "osaliselt": "partly", "täielikult": "fully", "servadest": "at the edges", "nurkadest": "at the corners", "tagant": "from behind", "keskelt": "in the middle"}
def term_words(v):
    if not v: return None
    out = term(v, MAT)                                              # the phrase tables first
    def word(m):
        w = m.group(0); k = w.lower()
        return MATWORD.get(k, MAT.get(k, TECH.get(k, w)))
    out = re.sub(r"[A-Za-zÕÄÖÜõäöüŠšŽž]+", word, out)
    return out
def term_gal(v):
    if not v: return None
    out = []
    for p in [p.strip() for p in re.split(r'[;,\n]', v) if p.strip()][:4]:
        words = [TECHMAT.get(w.lower().strip("."), w) for w in p.split()]
        out.append(" ".join(words))
    return ", ".join(out)

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
    y, lab = year_of(r.get("date"))
    # Same artist, same title, same year -- impressions of one print, catalogued as
    # "1920" and "ca 1920", are one work. Without a year, the dating label decides:
    # a "Maastik" dated "1839–1893" is not the same sheet as one left undated, and a
    # wide range now carries no year of its own.
    g = (r["artist"], tkey(r["t"]), y, "" if y else (lab or "").lower())
    # A painting is one object: five Mägi canvases called Veneetsia, 1922, are five
    # works, not one work in five parts. Only multiples -- prints, photographs,
    # bookplates, posters -- fold on title and date; anything else folds only with
    # the same inventory number written two ways (MuIS's "153:116", EKM's "153/116").
    ess = (r.get("ess") or "").lower()
    if not re.search(r"graaf|foto|eksliibris|plakat|postkaart|trüki|kaart|reprodukt", ess):
        g = g + (re.sub(r"[^a-z0-9]", "", (r.get("num") or "").lower()),)
    groups.setdefault(g, []).append(r)
OBJECTS = len(recs)
recs = []
for g, members in groups.items():
    members.sort(key=lambda r: (0 if "muis" in r["src"] else 1, r.get("num") or ""))
    rep = dict(members[0]); rep["n"] = len(members)
    if len(members) > 1:
        # [number, technique (Estonian), date, muis id, ekm id, technique (English)]
        rep["mem"] = [[m.get("num") or "", (m.get("tech") or "").split(";")[0].strip(),
                       (m.get("date") or ""), m.get("muis") or "", m.get("oid") or "",
                       term((m.get("tech") or "").split(";")[0].strip(), TECH) or ""]
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
    # Only when the dating field said nothing at all. A wide range yields no year but is
    # still the museum's dating; a year off the title must not overrule it.
    if y is None and not lab:
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
      "m": term_words(r.get("mat")), "me": r.get("mat"),
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

# The auction houses and galleries write names their own way -- "Amandus Heinrich
# Adamson", "Carl Timoleon von Neff", "Henn-Olavi Roode", "Woldemar Tank" -- and each
# such spelling was becoming an artist of its own beside the museum's "Amandus Adamson".
# A name is the same person's when the surname matches and every given name of the
# shorter form has a close match in the longer (C/K, W/V, X/KS folded, one letter of
# slack), with one candidate only; a generation word must agree. Fewer, surer merges
# than guessing on the surname alone.
_vn = lambda t: re.sub(r"^c", "k", t.replace("x", "ks").replace("w", "v"))
def _vtoks(n): return [_vn(t) for t in re.findall(r"[^\s.,\-]+", " ".join(_toks(n)))]
_vsur = collections.defaultdict(list)
def resolve_variant(name):
    if NEVER.search(name) or re.search(r"\s[&/]\s|\sja\s|\sand\s", name): return None   # two hands are not a variant of one
    t = _vtoks(name)
    if len(t) < 2: return None
    hits = []
    for j in _vsur.get(t[-1], []):
        c = _vtoks(artists[j]["n"])
        if len(c) < 2 or _qual(artists[j]["n"]) != _qual(name): continue
        lo, hi = (t[:-1], c[:-1]) if len(t) <= len(c) else (c[:-1], t[:-1])
        # a short given name gets no slack: Are is not Mare, Ott is not Otto
        near = lambda a, b: a == b if min(len(a), len(b)) < 4 else _close(a, b)
        if all(any(near(a, b) for b in hi) for a in lo): hits.append(j)
    return hits[0] if len(hits) == 1 else None

def artist_index(name, bio_en=None):
    """Find an artist, or add one. Returns index or None for unusable names."""
    t = toks(name)
    if not t: return None
    if t in by_tok: return by_tok[t]
    if not _vsur:
        for j, a in enumerate(artists):
            v = _vtoks(a["n"])
            if len(v) >= 2: _vsur[v[-1]].append(j)
    j = resolve_variant(name)
    if j is not None: by_tok[t] = j; VARIANTS.append((name, artists[j]["n"])); return j
    artists.append({"n": name.strip(), "l": ["", ""], "ls": "ed", "b": "", "bs": "ed",
                    "ai": None, "c": 0, "ben": bio_en, "bens": "cca" if bio_en else None})
    by_tok[t] = len(artists) - 1
    v = _vtoks(name)
    if len(v) >= 2: _vsur[v[-1]].append(by_tok[t])
    return by_tok[t]
VARIANTS = []

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

# Occupation is the check the name match was missing. Where the museum had no dates,
# wd_plausible had nothing to say, and a veterinarian with 126 paintings got through.
# An item whose recorded occupations include nothing artistic is a different person.
# An item with no occupation recorded is left alone: minor artists often have none.
WD_OCC = json.load(open("wd_occ.json", encoding="utf-8")) if os.path.exists("wd_occ.json") else {}
WD_OCC_LAB = json.load(open("wd_occ_labels.json", encoding="utf-8")) if os.path.exists("wd_occ_labels.json") else {}
ARTY = re.compile(r"artist|painter|engraver|sculptor|designer|scenograph|illustrat|photograph|architect|"
                  r"print|graphic|ceram|glass|textile|jewel|goldsmith|silversmith|medal|lithograph|"
                  r"xylograph|draw|draft|draughts|cartoon|caricatur|animat|calligraph|typograph|muralist|"
                  r"miniatur|portrait|pastel|watercolo|exlibris|carver|restorer|poster|installation|"
                  r"performance|conceptual|art educator|art teacher|art historian|etcher|potter|enamel|"
                  r"mosaic|stained|bookbind|tapestry|weaver|woodcut|aquarell|fresco|icon", re.I)
ARTY_IDS = {q for q, l in WD_OCC_LAB.items() if ARTY.search(l)}
BAD_QID = {q for q, os_ in WD_OCC.items() if not (set(os_) & ARTY_IDS)}

WD_REJECTED = WD_CONFLICT = WD_NOTARTIST = 0
for a in artists:
    w, v = wd_get(WD, a["n"]), wd_get(WDD, a["n"])
    if w and w.get("qid") in BAD_QID: w = None; WD_NOTARTIST += 1
    if v and v.get("qid") in BAD_QID: v = None; WD_NOTARTIST += 1
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
        # Wikidata lists the Soviet Union as a citizenship for anyone who lived here
        # 1940-91. The state's position, and this catalogue's, is that the occupation
        # conferred none: an Estonian of that time is Estonian. The Russian Empire
        # before 1918 stands, there was no Estonian state then.
        if w.get("cit"):
            cit = [c for c in w["cit"] if c not in ("Soviet Union", "Nõukogude Liit")]
            if cit: a["cit"] = cit
        if w.get("qid"): a["qid"] = w["qid"]
        if w.get("born"): a["born"] = w["born"]
    if v:
        a["wdesc"] = v["desc"]
        if not a.get("qid"): a["qid"] = v.get("qid")
        f = affil(v["desc"])
        if f: a["aff"] = f
print("  wikidata rejected on date contradiction:", WD_REJECTED)
print("  wikidata rejected as not an artist:", WD_NOTARTIST)
print("  wikidata dropped as unresolvable conflict:", WD_CONFLICT)


# ---------- commercial galleries ----------
# These are NOT museum holdings: the work is in private hands or for sale, and the
# gallery is its current venue rather than an owner with an accession number. They
# carry kind="gallery" so a visitor can always tell the two apart, and every record
# links back to the gallery's own page. Prices are deliberately not collected.
GAL = json.load(open("gallery_records.json", encoding="utf-8")) if os.path.exists("gallery_records.json") else []
# ...and the listings that have left: a work a gallery marks sold, or one that was
# listed and is not any more (ledger.py). A past listing is a record of a work that
# passed through a known hand -- kept, as its own kind, never counted as for sale.
PAST = json.load(open("gallery_past.json", encoding="utf-8")) if os.path.exists("gallery_past.json") else []
for r in PAST: r["past"] = True
GAL = GAL + PAST
# A gallery that lists one work under two product ids -- Haus does, a hundred times --
# is one work. Same artist, same title, same size, same gallery: the first listing stays.
_seen, _dedup, _gal_dup = set(), [], 0
for g in GAL:
    k = (g["gallery"], " ".join(fold(g.get("artist") or "")), "".join(fold(g.get("title") or "")),
         re.sub(r"[^0-9x]", "", (g.get("dims") or "").lower().replace("×", "x").replace(",", ".")))
    if k[2] and k in _seen: _gal_dup += 1; continue
    _seen.add(k); _dedup.append(g)
print("  gallery listings that were the same work twice:", _gal_dup)
GAL = _dedup
gal_added = gal_unknown = gal_new_est = 0
NOBA_ARTISTS = json.load(open("noba_artists.json", encoding="utf-8")) if os.path.exists("noba_artists.json") else {}
# Marketplace records are decided last, once every gallery's own artists are in.
GAL.sort(key=lambda g: bool(g.get("only_known")))
# Each gallery parser decoded its own shortlist of HTML entities, which let
# "&#8220;" and "&#8221;" through into titles. Decode the lot here instead, once.
for g in GAL:
    for f in ("artist", "title", "tech", "dims"):
        if g.get(f): g[f] = re.sub(r'\s+', ' ', html.unescape(g[f])).strip()
    # A marketplace lists artists from the whole region. Its records are taken only
    # for artists the catalogue already has -- museum-held or in a gallery harvested
    # on its own -- and never add a name. The rest is a separate decision.
    if g.get("only_known") and toks(g["artist"]) not in by_tok:
        # ...unless NOBA's own artist page says the artist is based in Estonia. That
        # is the catalogue's line: art in Estonia, not art from the whole Baltic.
        na = NOBA_ARTISTS.get(g["artist"]) or {}
        if na.get("country") != "Eesti": gal_unknown += 1; continue
        gal_new_est += 1
    if not g.get("title"): continue           # before the artist is added: a titleless listing must not create a name
    ai = artist_index(g["artist"])
    if ai is None: continue
    # a biography from the artist's NOBA page, for artists who have none elsewhere
    na = NOBA_ARTISTS.get(g["artist"]) or {}
    if na.get("bio") and not artists[ai].get("b") and not artists[ai].get("ben"):
        artists[ai]["b"], artists[ai]["bs"] = na["bio"], "noba"
    y = int(g["year"]) if g.get("year") and g["year"].isdigit() else None
    tech = g.get("tech") or None
    works.append({"a": ai, "t": g["title"], "y": y,
        "yl": g.get("year") or None, "dsrc": "gallery" if y else None,
        "e": infer_med(None, tech, tech), "ee": None,
        "tc": term_gal(tech), "tce": tech, "m": None, "me": None,
        "dm": g.get("dims") or None, "mu": g["gallery"], "co": None,
        "nu": None, "d": None, "c": None, "s": "gallery", "mi": None, "oi": None,
        "k": "G" + re.sub(r'[^A-Za-z0-9]', '', g["gid"]), "n": 1,
        # an exhibition or portfolio page says a work was shown, not that it is for sale
        "mem": None, "kind": "sold" if (g.get("sold") or g.get("past")) else ("shown" if g.get("shown") else "gallery"), "url": g.get("url"),
        "gs": (1 if g.get("sold") else 0) if (g.get("sold") or g.get("past")) else None,   # 1 the gallery said sold, 0 no longer listed
        # the gallery's own photograph, for stock only: shown from the gallery's server, with
        # the gallery named, while the listing is live -- what the gallery wants of a work it
        # is selling. A past listing keeps no image: the sale is over and the picture is theirs.
        "im": ("g:" + g["img"]) if g.get("img") and not (g.get("sold") or g.get("past")) else None,
        "gl": g.get("last")})                                                             # last month seen for sale
    gal_added += 1
# NOBA publishes no birth years, but the biographies its artists write usually state
# one -- "sündinud 1987", "born 1974", "(s. 1962)". Read from the biography only for
# artists with no date from anywhere else, tagged NOBA, and only a year a working
# artist could plausibly have been born in.
BIO_BORN = re.compile(r"(?:sündinud|sündis|sünd\.?|\bs\.|\bborn|\bb\.)\s*(?:\d{1,2}\.?\s*(?:\d{1,2}\.|[a-zäöüõ]+)\s*)?(1[89]\d\d|20[01]\d)\b", re.I)
BIO_PAREN = re.compile(r"\((?:s\.|b\.|sünd\.?|born)?\s*(1[89]\d\d|20[01]\d)\s*[-–]?\s*(1[89]\d\d|20[0-2]\d)?\)")
bio_dated = 0
_first_work = {}
for w in works:
    if w["y"]: _first_work[w["a"]] = min(_first_work.get(w["a"], 9999), w["y"])
for i, a in enumerate(artists):
    if a["l"][0] or a.get("bs") != "noba": continue
    m = BIO_BORN.search(a["b"]) or BIO_PAREN.search(a["b"])
    if not m: continue
    b = int(m.group(1))
    # "(2008-2013)" in a biography is a course of study, not a life; a birth year is
    # only believed when the artist's earliest work comes at least fifteen years after it
    if not (1900 <= b <= 2010) or _first_work.get(i, 9999) < b + 15: continue
    a["l"], a["ls"] = [str(b), ""], "noba"; bio_dated += 1
print("  birth years read from NOBA biographies:", bio_dated)
print("  marketplace works skipped, artist not in catalogue and not based in Estonia:", gal_unknown)
print("  marketplace works by Estonia-based artists new to the catalogue:", gal_new_est)
print("  gallery works added:", gal_added, "of which past listings", sum(1 for w in works if w.get("kind") == "sold"),
      "(", sum(1 for w in works if w.get("kind") == "sold" and w.get("gs")), "sold,",
      sum(1 for w in works if w.get("kind") == "sold" and not w.get("gs")), "no longer listed ) from", len({g["gallery"] for g in GAL}), "galleries")

# ---------- dates the record does not give but the evidence does ----------
# Three inferences, each tagged in dsrc so the page, the CSV and the counts can keep
# them apart from a museum's own dating. Only museum works; only where the dating
# field said nothing at all (a museum's "dateerimata" or a wide range is left as it is).
#   title      : "u 1925", "ca 1930", "1930ndad" inside the title, the forms the
#                trailing-year rule above does not read
#   impression : a print, bookplate, illustration, poster or cast whose artist has the
#                same title dated elsewhere with exactly one year -- another impression
#                of the same plate; a painting called Maastik is never dated this way
#   artist     : a decade, "ca 1910ndad", where the artist's dated works (five or more)
#                all fall within thirty years, or the whole working life fits in
#                thirty; the museum gives none, and this is a bound, not a date
_MULTI = {"Print", "Bookplate", "Illustration", "Poster", "Sculpture", "Relief"}
_generic = re.compile(r"^(maastik|portree|natüürmort|akt|kompositsioon|vaade|motiiv|lilled|talv|kevad|sügis|suvi|naine|mees|joonistus|graafika|visand|etüüd|eskiis)\W*$", re.I)
_T2 = re.compile(r"(?<![\d])(?:u\.?|ca\.?|umbes)\s*(1[5-9]\d\d|20[0-2]\d)(?![\d])|(?<![\d])(1[5-9]\d0)ndad", re.I)
_dated_by = collections.defaultdict(set); _years_of = collections.defaultdict(list)
for w in works:
    if w.get("y") is not None and (w.get("kind") or "held") in ("held", "shown"):
        _dated_by[(w["a"], "".join(fold(w["t"])).rstrip("."))].add(w["y"]); _years_of[w["a"]].append(w["y"])
_inf = collections.Counter()
for w in works:
    if w.get("y") is not None or w.get("yl") or (w.get("kind") or "held") not in ("held", "shown"): continue
    a = artists[w["a"]]; b = int(a["l"][0]) if a["l"][0] else None; dd = int(a["l"][1]) if a["l"][1] else None
    m = _T2.search(w["t"])
    if m:
        ty = int(m.group(1) or m.group(2))
        if b is None or (b + 12 <= ty <= (dd or 2026) + 2):
            w["y"], w["yl"], w["dsrc"] = ty, (f"{ty}ndad" if m.group(2) else f"ca {ty}"), "title"; _inf["title"] += 1; continue
    if w.get("e") in _MULTI and not _generic.match(w["t"].strip()) and len(w["t"].split()) >= 2:
        ys = _dated_by.get((w["a"], "".join(fold(w["t"])).rstrip(".")))
        if ys and len(ys) == 1:
            w["y"] = next(iter(ys)); w["yl"] = str(w["y"]); w["dsrc"] = "impression"; _inf["impression"] += 1; continue
    ys = _years_of.get(w["a"], [])
    dec = None
    if len(ys) >= 5 and max(ys) - min(ys) <= 30: dec = (sorted(ys)[len(ys) // 2]) // 10 * 10
    elif b and dd and dd - (b + 20) <= 30 and dd - b >= 20: dec = ((b + 20 + dd) // 2) // 10 * 10
    if dec:
        w["y"], w["yl"], w["dsrc"] = dec, f"ca {dec}ndad", "artist"; _inf["artist"] += 1
print("  dates inferred:", dict(_inf))

# ---------- known works: the Konrad Mägi Foundation's catalogue ----------
# A catalogue raisonné records works the public sources cannot: in private hands, or
# lost. Those enter as "known" -- the work exists, the catalogue says so, and the holder
# is "Erakogu" (a private collection, never a name) or "asukoht teadmata" (whereabouts
# unknown). A work the catalogue places in an Estonian museum is already here from the
# museum and is not added again; one in an institution the catalogue does not otherwise
# cover (an archive, a society, a museum abroad) is added under that holder's name.
KM = json.load(open("konradmagi_records.json", encoding="utf-8")) if os.path.exists("konradmagi_records.json") else []
_musnames = {w["mu"] for w in works if w.get("kind") in (None, "held", "shown")}
_km_added = 0
for r in KM:
    if r["holder_kind"] == "held" and r["holder"] in _musnames: continue
    ai = artist_index("Konrad Mägi")
    if ai is None: break
    ds = r.get("date") or ""
    y = int(re.match(r"(\d{4})", ds).group(1)) if re.match(r"\d{4}", ds) else None
    med = r.get("medium") or None
    dm = re.sub(r"\s*×\s*", " x ", r["dims"]).replace(",", ".") if r.get("dims") else None
    holder = r["holder"] if r["holder_kind"] == "held" else ("Erakogu" if r["holder_kind"] == "private" else "Asukoht teadmata")
    works.append({"a": ai, "t": r["title"], "y": y, "yl": ds or None, "dsrc": "gallery" if y else None,
        "e": infer_med(None, med, med), "ee": None, "tc": term_gal(med), "tce": med, "m": None, "me": None,
        "dm": dm, "mu": holder, "co": None, "nu": None, "d": None, "c": None, "s": "kmsa", "mi": None, "oi": None,
        "k": "K" + re.sub(r"[^a-z0-9]", "", r["url"].rstrip("/").split("/")[-1]), "n": 1, "mem": None,
        "kind": "known", "url": r["url"], "im": ("g:" + r["img"]) if r.get("img") else None,
        "kc": r["category"]})
    _km_added += 1
print("  known works from the Konrad Mägi Foundation's catalogue:", _km_added, "of", len(KM))

# ---------- auction results ----------
# Results as the auction house published them (vernissage_auctions.py): a lot, the
# sale it was in, its starting price, its hammer price if it sold. A separate kind
# from a museum holding and from a gallery listing: nothing here is for sale, and
# the price is the record of a sale, not a valuation. An unsold lot is a result too.
AUC = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
# ...and the few results the houses' sites no longer carry but the press recorded at
# the time -- Köler's 172,561 € at Vaal in 2008, the 112,000 € at E-Kunstisalong in
# 2014 -- kept by hand in press_results.json with the article they come from.
AUC += json.load(open("press_results.json", encoding="utf-8")) if os.path.exists("press_results.json") else []
# A published figure that cannot be right -- the 1999 Mägi lot Haus prints as sold at the
# price the work made twenty years later, with no bid recorded -- loses the figure and,
# where the entry says so, the sale, with the reason shown on the record. Per lot, by
# hand, in auction_doubt.json; never by rule.
DOUBT = json.load(open("auction_doubt.json", encoding="utf-8")) if os.path.exists("auction_doubt.json") else {}
auc_added = auc_skipped = 0
for r in AUC:
    if r["aid"] in DOUBT:
        r["hammer"] = None; r["after"] = False; r["doubt"] = DOUBT[r["aid"]]
        if "sold" in DOUBT[r["aid"]]: r["sold"] = DOUBT[r["aid"]]["sold"]
    for f in ("artist", "title", "tech", "dims"):
        if r.get(f): r[f] = re.sub(r'\s+', ' ', html.unescape(r[f])).strip()
    if not r.get("title"): continue
    # a lot the house could not attribute, or attributed to two hands, is not one artist's
    if re.search(r"tundmatu|unknown|\s[&/]\s|\sja\s", r["artist"], re.I): auc_skipped += 1; continue
    ai = artist_index(r["artist"])
    if ai is None: continue
    y = int(r["year"]) if r.get("year") and r["year"].isdigit() else None
    tech = r.get("tech") or None
    works.append({"a": ai, "t": r["title"], "y": y,
        "yl": r.get("yl") or r.get("year") or None, "dsrc": "gallery" if y else None,
        "e": infer_med(None, tech, tech), "ee": None,
        "tc": term_gal(tech), "tce": tech, "m": None, "me": None,
        "dm": r.get("dims") or None, "mu": r["house"], "co": None,
        "nu": None, "d": None, "c": None, "s": "auction", "mi": None, "oi": None,
        "k": "A" + re.sub(r'[^A-Za-z0-9]', '', r["aid"]), "n": 1,
        "mem": None, "kind": "auction", "url": r.get("url"),
        "an": r["sale"], "ad": r.get("date") or r["when"], "as": r.get("start"), "ap": r.get("hammer"), "ao": 1 if r["sold"] else 0,
        "aa": 1 if r.get("after") else None, "apr": r.get("press"), "adb": r.get("doubt")})
    auc_added += 1
print("  auction results added:", auc_added, "sold", sum(1 for r in AUC if r["sold"]),
      "from", len({r["house"] for r in AUC}), "houses; unattributed or joint lots skipped:", auc_skipped)
# The same work comes back to the rooms: Mägi's Oberstdorfi maastik, unsold at Haus
# in 1999, sold there in 2019. Every lot stays a record -- each is a sale that
# happened -- but lots of one work (artist, title, size) are chained, and the page
# shows the work once, with its results in order, rather than twice as strangers.
_chain = collections.defaultdict(list)
for w in works:
    if w.get("kind") == "auction" and w.get("dm"):
        _chain[(w["a"], "".join(fold(w["t"])).rstrip("."), re.sub(r"[^0-9x]", "", w["dm"].lower().replace("×", "x").replace(",", ".")))].append(w)
_nc = 0
for lots in _chain.values():
    if len(lots) < 2: continue
    lots.sort(key=lambda w: str(w.get("ad") or ""))
    _nc += 1
    for k, w in enumerate(lots):
        w["ac"] = _nc                                    # the chain
        if k == len(lots) - 1: w["al"] = 1               # the latest lot carries the work on the page
print("  works offered more than once:", _nc, "chains over", sum(len(l) for l in _chain.values() if len(l) > 1), "lots")
# Vaal galerii prints life dates beside every lot's artist -- "s 1960", "1936–2022" --
# the only auction house that does. For an artist with no date from any museum,
# Wikidata or their own biography, that is taken, tagged Vaal, under the same gate as
# the NOBA biographies: a birth year the artist's earliest work comes at least
# fifteen years after. A death year is taken only with a birth year.
VAAL_LIFE = {}
for r in AUC:
    if r.get("life") and r.get("artist"):
        VAAL_LIFE.setdefault(toks(r["artist"]), r["life"])
vaal_dated = 0
for i, a in enumerate(artists):
    if a["l"][0] or a["l"][1]: continue
    lf = VAAL_LIFE.get(toks(a["n"]))
    if not lf: continue
    m = re.match(r"^(?:s\.?\s*)?(1[89]\d\d|20[01]\d)\s*(?:[-–]\s*(1[89]\d\d|20[0-2]\d))?$", lf.strip())
    if not m: continue
    b, d = int(m.group(1)), m.group(2)
    if _first_work.get(i, 9999) < b + 15: continue
    a["l"], a["ls"] = [str(b), d or ""], "vaal"; vaal_dated += 1
print("  life dates taken from Vaal galerii's catalogue:", vaal_dated)
print("  house and gallery spellings resolved to a catalogued artist:", len(VARIANTS))
for v in VARIANTS: print(f"     {v[0]!r} -> {v[1]!r}")

# ---------- training, movements, memberships ----------
# Where an artist trained is a real axis in Estonian art — the Pallas school in Tartu
# and the academy in Tallinn are different lineages, and Ants Laikmaa's atelier taught
# a generation before either. Wikidata records it as P69 (educated at), P135 (movement)
# and P463 (member of); the museums' own biographies name the same things but exist for
# only 478 artists, against 841 here. Groups with fewer than three artists are dropped:
# a facet of singletons is noise, not an axis.
GRP = json.load(open("wd_groups.json", encoding="utf-8")) if os.path.exists("wd_groups.json") else {}
KIND = {"P69": "school", "P135": "movement", "P463": "member"}
by_qid = {}
# A gymnasium is schooling, not art training. Keeping them makes the facet answer a
# question nobody asked ("who went to secondary school in Tartu") while burying the
# one it exists for — where a painter learned to paint.
NOT_ART = re.compile(r'gymnasium|gümnaasium|secondary|high school|realkool|'
                     r'university of technology|polütehnik', re.I)
for key, qids in GRP.items():
    prop, label = key.split("|", 1)
    if len(qids) < 3 or NOT_ART.search(label): continue
    for q in qids:
        by_qid.setdefault(q, []).append((KIND.get(prop, prop), label))
grp_n = 0
for a in artists:
    rows = by_qid.get(a.get("qid") or "")
    if not rows: continue
    a["grp"] = sorted({f"{k}:{v}" for k, v in rows})
    grp_n += 1
print("  artists with a school/movement/membership:", grp_n)

for w in works: w.setdefault("kind", "held")
# the medium field is English, but MuIS's object types came through untranslated for
# the long tail; the names a reader will meet get their English, the rest fold to Other
_MED_EN = {"Kavand": "Design", "Nõu": "Vessel", "Karikatuur": "Caricature", "Miniatuur": "Miniature", "Plakat": "Poster",
           "Figuur": "Figurine", "Visand": "Sketch", "Kaaned": "Book cover", "Taldrik": "Plate", "Raamat": "Book",
           "Videoinstallatsioon": "Video installation", "Postkaart": "Postcard", "Plaat": "Tile", "Aksessuaar": "Accessory",
           "Ehe": "Jewellery", "Kauss": "Bowl", "Laegas": "Casket", "Surimask": "Death mask", "Vaas": "Vase",
           "Graafikaplaat": "Printing plate", "Alus": "Stand", "Ümbris": "Cover", "Kahhel (keraamiline plaat)": "Tile",
           "Märkmik": "Notebook", "Dekoratiivne vorm": "Decorative form", "Toos": "Box", "Kangas": "Fabric", "Tähtpäevakaart": "Greeting card",
           "Mapp": "Portfolio", "Väljalõige": "Cutting", "Kott": "Bag", "Mööbel": "Furniture", "Kate": "Cover", "Pannoo": "Panel", "Kann": "Jug", "???": "Other"}
for w in works:
    if w.get("e") in _MED_EN: w["e"] = _MED_EN[w["e"]]
for i, a in enumerate(artists): a["c"] = sum(1 for w in works if w["a"] == i)

# ---------- where to find the holder ----------
# data/venues.json was compiled by checking each institution's site returned 200 and
# reading its page title back as evidence. Map it onto the museums that actually hold
# work here, and derive each gallery's home page from the records it supplied, so a
# reader can go from a record to the place that holds it.
SITES = {}
try:
    for v in json.load(open("venues.json", encoding="utf-8")):
        # several branches share one holder — the entry named for the holder wins,
        # so "Eesti Kunstimuuseum" links to the foundation and not to whichever of
        # Kumu, Kadriorg, Mikkel, Niguliste or Adamson-Eric happened to be last.
        if not (v.get("holder") and v.get("url")): continue
        if v["holder"] not in SITES or v.get("n") == v["holder"]:
            SITES[v["holder"]] = v["url"]
except FileNotFoundError:
    pass
for g in GAL:
    u = g.get("url") or ""
    m = re.match(r'(https?://[^/?]+)', u)
    if m and g.get("gallery"): SITES.setdefault(g["gallery"], m.group(1))
SITES = {k: v for k, v in SITES.items() if k in {w["mu"] for w in works if w.get("mu")}}
print("  holders with a website:", len(SITES))

# Life dates from Wikidata, for artists the museums left undated. Runs last, after the
# gallery pass has added its artists: 46 of the new matches are gallery-only names. Until now Wikidata's
# birth year was used only to check a match, never to fill one, and 514 matched
# artists sat without dates the item plainly carried. Filled only where the museum
# gave no birth year at all, and tagged "wd" so the page says whose date it is.
WD_DATES = json.load(open("wd_dates.json", encoding="utf-8")) if os.path.exists("wd_dates.json") else {}
# wd_dates.py's second pass: artists with no match and no dates, matched on the name
# with their own work years as the anchor, one candidate or nothing.
WD_NEW = json.load(open("wd_matches2.json", encoding="utf-8")) if os.path.exists("wd_matches2.json") else {}
# ...and the third pass (wd_dates3.py), which asks for a tie to Estonia and so can take
# artists with a single dated work, or none
WD_NEW.update(json.load(open("wd_matches3.json", encoding="utf-8")) if os.path.exists("wd_matches3.json") else {})
WD_DATED = WD_MATCHED = 0
for a in artists:
    if not a.get("qid") and a["n"] in WD_NEW and not (a["l"][0]):
        m = WD_NEW[a["n"]]
        a["qid"] = m["qid"]; WD_MATCHED += 1
        if m.get("desc") and not a.get("wdesc"):
            a["wdesc"] = m["desc"]
            f = affil(m["desc"])
            if f: a["aff"] = f
        if m.get("byear"):
            a["l"] = [str(m["byear"]), str(m["dyear"] or "")]; a["ls"] = "wd"; WD_DATED += 1
    elif a.get("qid") and not a["l"][0]:
        b, dd = WD_DATES.get(a["qid"], [None, None])
        if b: a["l"] = [str(b), str(dd or "")]; a["ls"] = "wd"; WD_DATED += 1
# A Wikidata birth year later than the artist's own earliest work is not a date but a
# verdict: wrong person. Undo the whole identity, not just the date, before the flags
# are computed against it.
WD_UNDONE = 0
_first = {}
for w in works:
    if w["y"]: _first[w["a"]] = min(_first.get(w["a"], 9999), w["y"])
for i, a in enumerate(artists):
    if a.get("ls") == "wd" and a["l"][0] and i in _first and _first[i] < int(a["l"][0]):
        for k in ("qid", "wdesc", "cit", "born", "aff", "grp"): a.pop(k, None)
        a["l"], a["ls"] = ["", ""], "ed"; WD_UNDONE += 1
print("  wikidata: newly matched", WD_MATCHED, "/ life dates filled", WD_DATED, "/ undone as wrong person", WD_UNDONE)

# A work dated before its artist was born, or after they died, is one of three things
# (checked last, once Wikidata has supplied the dates the museums did not):
# a cataloguing slip in the source (Šiškin's "1478"), a later impression or copy dated
# by its own making (heliogravures after Tšemesov, printed 1878), or a photograph of
# the work standing in for it (Wedekind portraits "1997"). The record stays as the
# museum holds it; the flag lets the page say what it sees, and keeps the year out of
# the artist's activity span, where a single 1478 would stretch Šiškin to the 1400s.
def _yr(s):
    m = re.search(r'\d{4}', str(s or "")); return int(m.group()) if m else None
FLAGGED = {"pre": 0, "post": 0}
for w in works:
    if w["y"] is None: continue
    b, d = _yr(artists[w["a"]]["l"][0]), _yr(artists[w["a"]]["l"][1])
    if b and w["y"] < b:        w["f"] = "pre";  FLAGGED["pre"] += 1
    elif d and w["y"] > d + 1:  w["f"] = "post"; FLAGGED["post"] += 1
print("  flagged: dated before birth", FLAGGED["pre"], "/ after death", FLAGGED["post"])

# ---------- images, for works in the public domain ----------
# A museum record gets a reference to the holder's own image of it -- MuIS's media
# id, or the EKM Digital Collection's file path -- only where the work itself is out
# of copyright: the artist dead by the end of THIS_YEAR-71, or born by THIS_YEAR-156
# with no death recorded. Nothing is copied; the page loads the picture from the
# museum when the record is opened and says whose it is. The photograph of a
# public-domain work is not itself protected (EU directive 2019/790 art. 14, in
# Estonian law since 2021), whatever the catalogue's rights label says. Everything
# by a later artist -- most of the catalogue -- stays without.
import gzip
_img = json.load(gzip.open("raw/image_urls.json.gz", "rt", encoding="utf-8")) if os.path.exists("raw/image_urls.json.gz") else {}
if os.path.exists("oai_images.json"): _img.update(json.load(open("oai_images.json", encoding="utf-8")))   # media ids from the OAI records
_ekm = json.load(open("ekm_images.json", encoding="utf-8")) if os.path.exists("ekm_images.json") else {}
# ...and each EKM picture's proportions (height over width, from the preview's pixel
# size, ekm_shapes.py), so the wall can lay a tile out before the picture arrives
_ekmr = json.load(open("ekm_shapes.json", encoding="utf-8")) if os.path.exists("ekm_shapes.json") else {}
_galr = json.load(open("gallery_shapes.json", encoding="utf-8")) if os.path.exists("gallery_shapes.json") else {}
_muisr = json.load(open("muis_shapes.json", encoding="utf-8")) if os.path.exists("muis_shapes.json") else {}
if os.path.exists("oai_shapes.json"): _muisr.update(json.load(open("oai_shapes.json", encoding="utf-8")))   # pixel sizes the OAI records carry
_Y = datetime.date.today().year
def _pd(a):
    b, d = _yr(a["l"][0]), _yr(a["l"][1])
    return bool((d and d <= _Y - 71) or (b and not d and b <= _Y - 156))
IMG = {"pd": 0, "muis": 0, "ekm": 0}
for w in works:
    if w.get("kind") not in (None, "held") or not _pd(artists[w["a"]]): continue
    IMG["pd"] += 1
    if w.get("mi") and ("muis:" + str(w["mi"])) in _img: w["im"] = "m:" + _img["muis:" + str(w["mi"])]; IMG["muis"] += 1
    elif w.get("oi") and str(w["oi"]) in _ekm:
        w["im"] = "e:" + _ekm[str(w["oi"])];            IMG["ekm"] += 1
        if str(w["oi"]) in _ekmr: w["ir"] = _ekmr[str(w["oi"])]
# What people come to an artist for goes first on the wall: highlights.json names, per
# artist, the works art history treats as the key ones, in order. A pictured work whose
# title matches gets a rank -- the exact title before a version or a study of it.
_HL = json.load(open("highlights.json", encoding="utf-8")) if os.path.exists("highlights.json") else {}
_hl_by_artist = {}
for i, a in enumerate(artists):
    if a["n"] in _HL: _hl_by_artist[i] = _HL[a["n"]]
_STUDY = re.compile(r"visand|etüüd|eskiis|kavand|fragment|detail|proovi|krokii|reproduk|trükiplaat|eeltöö|variant", re.I)
_hln = 0
for w in works:
    pats = _hl_by_artist.get(w["a"])
    if not pats or not w.get("im"): continue
    t = w["t"].strip().rstrip(".")
    for k, pat in enumerate(pats):
        if re.search(r"(?:^|[\s(„\"])" + pat, t, re.I):
            exact = re.fullmatch(pat + r"[.!?]?", t, re.I) is not None
            # the exact title, then a version of it; every study, sketch and plate of
            # any highlight comes after all of those -- Põrgu has twenty studies
            w["hl"] = (1000 + k) if _STUDY.search(t) else k * 2 + (0 if exact else 1); _hln += 1
            break
print("  highlighted works on the wall:", _hln, "for", len(_hl_by_artist), "artists")
# The opening of the whole catalogue's wall is chosen by hand: masterpieces.json lists,
# in order, the works of Estonian art a visitor should meet first -- one pictured record
# each, the exact title in the named medium and year where the collection has it.
_MP = json.load(open("masterpieces.json", encoding="utf-8")) if os.path.exists("masterpieces.json") else []
_by_artist_name = {a["n"]: i for i, a in enumerate(artists)}
_mpn = 0
for rank, (an, pat, med, yr) in enumerate(_MP, 1):
    ai = _by_artist_name.get(an)
    if ai is None: continue
    cands = [w for w in works if w["a"] == ai and w.get("im") and re.search(r"^" + pat + r"(\W|$)", w["t"], re.I) and w.get("mp") is None]
    if not cands: print("  masterpiece not found:", an, "-", pat); continue
    exact = lambda w: re.fullmatch(pat + r"[.!?]?", w["t"].strip(), re.I) is not None
    cands.sort(key=lambda w: (not exact(w), (w.get("e") or "") != med, abs((w.get("y") or 9999) - yr) if yr else 0, w.get("y") or 9999))
    cands[0]["mp"] = rank; _mpn += 1
for w in works:
    t = re.sub(r"\s{2,}", " ", w["t"]).strip().rstrip(",;:").strip()
    if t and t != w["t"]: w["t"] = t
print("  masterpieces placed at the head of the wall:", _mpn, "of", len(_MP))
# ...and the gallery pictures' shapes, measured from the files (gallery_shapes.py)
for w in works:
    im = w.get("im") or ""
    if im.startswith("g:") and im[2:] in _galr: w["ir"] = _galr[im[2:]]
    if im.startswith("m:") and im[2:] in _muisr: w["ir"] = _muisr[im[2:]]
print("  images: public-domain museum works", IMG["pd"], "-> MuIS", IMG["muis"], "EKM", IMG["ekm"])

data = {"meta": {"built": datetime.date.today().isoformat(),
                 "works": len(works), "objects": OBJECTS, "artists": len(artists),
                 "held": sum(1 for w in works if w["kind"]=="held"),
                 "shown": sum(1 for w in works if w["kind"]=="shown"),
                 "gallery": sum(1 for w in works if w["kind"]=="gallery"),
                 "galleries": len({w["mu"] for w in works if w["kind"]=="gallery"}),
                 "noba": sum(1 for w in works if w["kind"]=="gallery" and w["mu"]=="NOBA"),
                 "known": sum(1 for w in works if w.get("kind")=="known"),
                 "past": sum(1 for w in works if w.get("kind")=="sold"),
                 "past_sold": sum(1 for w in works if w.get("kind")=="sold" and w.get("gs")),
                 "auction": sum(1 for w in works if w["kind"]=="auction"),
                 "auction_sold": sum(1 for w in works if w["kind"]=="auction" and w.get("ao")),
                 "houses": len({w["mu"] for w in works if w["kind"]=="auction"}),
                 "cca_bios": sum(1 for a in artists if a.get("bens")=="cca"),
                 "with_origin": sum(1 for a in artists if a.get("cit")),
                 "with_aff": sum(1 for a in artists if a.get("aff")),
                 "dated": sum(1 for w in works if w["y"]),
                 "dated_from_title": sum(1 for w in works if w.get("dsrc") == "title"),
                 "dated_inferred": sum(1 for w in works if w.get("dsrc") in ("impression", "artist")),
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
data["meta"]["sites"] = SITES
# English renderings of the Estonian prose, where translate.py has made them
from translate import apply_translations
_na, _nw = apply_translations(data)
# MuIS opens a biography mid-sentence now and then ("painter, printmaker and pedagogue.
# At the beginning..."): the record's person field continued from the name. Shown as
# prose, it starts with a capital.
for a in data["artists"]:
    for f in ("b", "ben"):
        if a.get(f) and a[f][:1].islower(): a[f] = a[f][:1].upper() + a[f][1:]
        if a.get(f) and not re.search(r'[.!?…"”)\]]\s*$', a[f]): a[f] = a[f].rstrip() + "."   # a sentence ends with a stop
print("  translations applied:", _na, "biographies,", _nw, "descriptions")
json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("data.json", os.path.getsize("data.json")//1024, "KB")
for k, v in data["meta"].items(): print(" ", k, v)
dec = collections.Counter((w["y"]//10*10) for w in works if w["y"])
print("decades:", " ".join(f"{k}s:{v}" for k, v in sorted(dec.items())))
print("media:", collections.Counter(w["e"] for w in works).most_common(14))
print("museums:", collections.Counter(w["mu"] for w in works).most_common(8))
print("categories:", collections.Counter(w["c"] for w in works if w["c"]).most_common(14))
