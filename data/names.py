# -*- coding: utf-8 -*-
"""How merge.py tells one artist's name from another's: spellings, aliases, generations.

merge.py runs on import, so the name matching lives here, where tests/test_names.py can
reach it. merge.py imports every name below and uses them as it always did; nothing here
reads a file or holds state.
"""
import re, unicodedata

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

# ---------- one person under two spellings ----------
# "Johan Köler" and "Johann Köler" are one man, "Erich Kügelgen" and "Erich von
# Kügelgen" are; merge.py's _same_person() settles it with the birth year, on these
# tokens. Names with a workshop, copy or attribution qualifier never merge -- a
# workshop is not its master.
PARTICLE = {"von", "van", "de", "der", "den", "du", "la", "le", "da", "di", "af", "zu", "und", "ja"}
NEVER = re.compile(r"töökoda|workshop|ateljee|koolkond|järgi|koopia|manner|ring|\?|\bja\b|&", re.I)   # a duo is two people
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

# ---------- the galleries' and auction houses' spellings ----------
def toks(n):
    n = unicodedata.normalize('NFKD', (n or "").lower())
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return tuple(sorted(t for t in re.split(r'[^a-z0-9]+', n) if len(t) > 1))

# The auction houses and galleries write names their own way -- "Amandus Heinrich
# Adamson", "Carl Timoleon von Neff", "Henn-Olavi Roode", "Woldemar Tank" -- and each
# such spelling was becoming an artist of its own beside the museum's "Amandus Adamson".
# A name is the same person's when the surname matches and every given name of the
# shorter form has a close match in the longer (C/K, W/V, X/KS folded, one letter of
# slack), with one candidate only; a generation word must agree. Fewer, surer merges
# than guessing on the surname alone.
_vn = lambda t: re.sub(r"^c", "k", t.replace("x", "ks").replace("w", "v"))
def _vtoks(n): return [_vn(t) for t in re.findall(r"[^\s.,\-]+", " ".join(_toks(n)))]
def resolve_variant(name, artists, vsur):
    """The index in artists of the one artist name is a spelling of, or None.
    vsur maps a folded surname to the indexes of the artists that carry it."""
    if NEVER.search(name) or re.search(r"\s[&/]\s|\sja\s|\sand\s", name): return None   # two hands are not a variant of one
    t = _vtoks(name)
    if len(t) < 2: return None
    hits = []
    for j in vsur.get(t[-1], []):
        c = _vtoks(artists[j]["n"])
        if len(c) < 2 or _qual(artists[j]["n"]) != _qual(name): continue
        lo, hi = (t[:-1], c[:-1]) if len(t) <= len(c) else (c[:-1], t[:-1])
        # a short given name gets no slack: Are is not Mare, Ott is not Otto
        near = lambda a, b: a == b if min(len(a), len(b)) < 4 else _close(a, b)
        if all(any(near(a, b) for b in hi) for a in lo): hits.append(j)
    return hits[0] if len(hits) == 1 else None
