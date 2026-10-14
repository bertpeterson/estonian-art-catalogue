# -*- coding: utf-8 -*-
"""Teachers, pupils and circles -> lineage.json

Who learnt from whom, and who stood together. Three sources, each kept in its own cache:

  1. Wikidata: "student of" (P1066) and "student" (P802), where both ends are in the
     catalogue. Thin -- a few dozen links -- but sourced.               -> wd_teachers.json
  2. The biographies. For each one, the catalogue artists whose surname occurs in it
     are the candidates; Claude reads the text and says which of them the artist
     studied under or taught, and which of the circles below the artist belonged to,
     quoting the words. A candidate list keeps the answer to people the catalogue
     has, and the quote keeps it to what the text says.               -> lineage_bios.json
  3. The schools and memberships Wikidata already gave (data.json "grp").

    python3 lineage.py wd                # fetch the Wikidata links
    python3 lineage.py bios --dry-run    # how many bios, what it would cost
    python3 lineage.py bios              # the Claude pass (needs ANTHROPIC_API_KEY); then rebuilds
    python3 lineage.py                   # combine the caches into lineage.json

lineage.json is keyed on names, as similar.json is not: it survives a re-merge that
renumbers the artists. A bio whose text changes is read again on the next bios run.
"""
import json, os, re, sys, hashlib, time, unicodedata, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
WD, BIOS, OUT = (os.path.join(HERE, f) for f in ("wd_teachers.json", "lineage_bios.json", "lineage.json"))
MODEL = os.environ.get("MT_MODEL", "claude-sonnet-5")
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"

# The circles: Estonian groups and studios a reader would look up. Each has a page
# (build_circles.py); "grp" names the Wikidata labels that already mean membership.
CIRCLES = [
    dict(id="pallas", en="Pallas", et="Pallas", grp=["school:Pallas"],
         d_en="The art school of the Pallas society in Tartu, 1919–1940, where Konrad Mägi, Ado Vabbe and Anton Starkopf taught.",
         d_et="Kunstiühingu Pallas kunstikool Tartus aastatel 1919–1940, kus õpetasid Konrad Mägi, Ado Vabbe ja Anton Starkopf."),
    dict(id="laikmaa", en="Ants Laikmaa's studio school", et="Ants Laikmaa ateljeekool", grp=["school:Atelier School of Ants Laikmaa"],
         d_en="The studio school Ants Laikmaa opened in Tallinn in 1903, the first art school of its kind in Estonia.",
         d_et="Ants Laikmaa 1903. aastal Tallinnas avatud ateljeekool, esimene omataoline kunstikool Eestis."),
    dict(id="young-estonia", en="Young Estonia", et="Noor-Eesti", grp=[],
         d_en="The literary and artistic movement of 1905.", d_et="1905. aasta kirjandus- ja kunstiliikumine."),
    dict(id="vikerla", en="Vikerla", et="Vikerla", grp=[],
         d_en="The young artists' union in Tallinn, founded in 1917.", d_et="Noorte kunstnike ühing Tallinnas, asutatud 1917."),
    dict(id="group-of-estonian-artists", en="Group of Estonian Artists", et="Eesti Kunstnikkude Rühm", grp=[],
         d_en="The group founded in Tartu in 1923 that took up cubism and constructivism.",
         d_et="1923. aastal Tartus asutatud rühmitus, kes võttis omaks kubismi ja konstruktivismi."),
    dict(id="ank-64", en="ANK '64", et="ANK '64", grp=["member:ANK '64"],
         d_en="The Tallinn group formed in 1964 around Tõnis Vint.", d_et="1964. aastal Tõnis Vindi ümber kogunenud Tallinna rühmitus."),
    dict(id="visarid", en="Visarid", et="Visarid", grp=[],
         d_en="The Tartu group of the late 1960s around Kaljo Põllu.", d_et="1960. aastate lõpu Tartu rühmitus Kaljo Põllu ümber."),
    dict(id="soup-69", en="SOUP '69", et="SOUP '69", grp=["member:SOUP '69"],
         d_en="The Tallinn group of 1969 that brought pop art to Estonia.", d_et="1969. aasta Tallinna rühmitus, kes tõi Eestisse popkunsti."),
]

SYSTEM = """You read biographies of artists from an Estonian art catalogue and extract who taught whom, and which groups the artist belonged to. Each biography may come in Estonian, English or both (the English is a translation of the Estonian).

For each item you get: the artist, their life dates, the biography, and "candidates" -- people from the catalogue whose surname appears in the text, each with an id and life dates.

Return, for each item:
- "teachers": ids of candidates the text says the artist studied under, was taught by, studied in the studio or class of, or was a pupil of. Estonian cues: "õppis ... juures", "... õpilane", "... ateljees", "... juhendamisel", "... käe all". Studying at a school is NOT enough unless the text names that person as teacher or the studio as theirs ("studied at Ants Laikmaa's studio school" makes Laikmaa a teacher).
- "pupils": ids of candidates the text says the artist taught.
- "circles": ids from the circle list below that the text says the artist studied at, belonged to or exhibited with as a member.
- "ev": for every id you return, the shortest quote from the text (in its own language) that says so.

Circles:
CIRCLES

Rules: only what the text states, never what you know from elsewhere. If a surname could be more than one candidate and the text does not make clear which (first name, initial, dates), leave it out. A person named only as a friend, colleague, subject of a portrait, author written about, or family member is not a teacher. When nothing applies, return empty lists.

Input: a JSON array of items. Output: a JSON array of the same length, in the same order, each {"teachers":[], "pupils":[], "circles":[], "ev":{}} -- nothing else, no code fence."""
SYSTEM = SYSTEM.replace("CIRCLES", "\n".join(f'- {c["id"]}: {c["en"]} ({c["et"]})' for c in CIRCLES))

def norm(s): return unicodedata.normalize("NFC", s or "")
def life(a):
    l = a.get("l") or ["", ""]
    return f"{l[0] or '?'}–{l[1] or ''}"
def born(a):
    m = re.search(r"\d{4}", str((a.get("l") or [""])[0] or ""))
    return int(m.group()) if m else None

def load():
    d = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
    return d["artists"]

# ---- 1. Wikidata -----------------------------------------------------------------------------
def fetch_wd(A):
    qids = sorted({a["qid"] for a in A if a.get("qid") and a.get("c", 0) > 0})
    pairs = set()
    for k in range(0, len(qids), 250):
        vals = " ".join("wd:" + q for q in qids[k:k + 250])
        query = f"""SELECT ?p ?t ?s WHERE {{ VALUES ?p {{ {vals} }}
  {{ ?p wdt:P1066 ?t }} UNION {{ ?p wdt:P802 ?s }} }}"""
        for attempt in range(3):
            try:
                req = urllib.request.Request("https://query.wikidata.org/sparql", urllib.parse.urlencode({"query": query}).encode(),
                                             {"User-Agent": UA, "Accept": "application/sparql-results+json"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    rows = json.loads(r.read().decode())["results"]["bindings"]
                break
            except Exception as e:
                if attempt == 2: raise SystemExit("  Wikidata: " + type(e).__name__)
                time.sleep(4 * (attempt + 1))
        q = lambda b, k: b[k]["value"].rsplit("/", 1)[-1] if k in b else None
        for b in rows:
            p = q(b, "p")
            if q(b, "t"): pairs.add((q(b, "t"), p))          # p was a student of t
            if q(b, "s"): pairs.add((p, q(b, "s")))          # s was a student of p
    json.dump(sorted(pairs), open(WD, "w"), indent=0)
    inside = [x for x in pairs if x[0] in qids and x[1] in qids]
    print(f"  Wikidata: {len(pairs)} teacher links, {len(inside)} with both ends in the catalogue")

# ---- 2. the biographies ----------------------------------------------------------------------
def surnames(name):
    """The words a bio would use for this artist: the last word of the name and any
    variant in brackets ("Aleksander Krims (Radava)" -> Krims, Radava)."""
    alts = re.findall(r"\(([^)]+)\)", name)
    base = re.sub(r"\([^)]*\)", " ", name).split()
    out = set(base[-1:]) if len(base) > 1 else set()
    for x in alts: out.update(w for w in x.split() if w[:1].isupper())
    return {w.strip(".,") for w in out if len(w.strip(".,")) >= 3}

def stem(w):
    # Estonian declines surnames: Triik -> Triigi, Okas -> Okase, Laikmaa -> Laikmaale
    return w if len(w) <= 4 else w[:max(4, len(w) - 2)]

def items_for(A):
    live = [i for i, a in enumerate(A) if a.get("c", 0) > 0]
    index = {}
    for i in live:
        for s in surnames(A[i]["n"]): index.setdefault(stem(s), set()).add(i)
    pat = re.compile(r"\b(" + "|".join(sorted(map(re.escape, index), key=len, reverse=True)) + r")\w*")
    items = []
    for i in live:
        a = A[i]
        text = "\n\n".join(dict.fromkeys(x for x in (a.get("b"), a.get("ben")) if x))
        if not text: continue
        cand = set()
        for m in pat.finditer(text): cand |= index.get(m.group(1), set())
        cand.discard(i)
        cand = sorted(cand, key=lambda j: -A[j].get("c", 0))[:40]
        cmap = {f"c{n}": A[j]["n"] for n, j in enumerate(cand, 1)}
        key = hashlib.sha1(json.dumps([a["n"], text, sorted(cmap.values())], ensure_ascii=False).encode()).hexdigest()
        items.append((key, dict(artist=a["n"], life=life(a), bio=text,
                                candidates={k: f"{v} ({life(A[j])})" for (k, v), j in zip(cmap.items(), cand)}), cmap))
    return items

def ask(client, batch):
    src = [it for _, it, _ in batch]
    for attempt in range(3):
        try:
            r = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM,
                                       messages=[{"role": "user", "content": json.dumps(src, ensure_ascii=False)}])
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", "".join(b.text for b in r.content if b.type == "text").strip())
            out = json.loads(text)
            if isinstance(out, list) and len(out) == len(src) and all(isinstance(x, dict) for x in out):
                return out, r.usage
        except json.JSONDecodeError: pass
        except Exception as e:
            fatal = type(e).__name__ in ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "TypeError")
            if fatal or any(w in str(e).lower() for w in ("credit", "billing", "api_key")):
                raise SystemExit("  API: " + type(e).__name__ + ": " + str(e)[:120])
        time.sleep(2 * (attempt + 1))
    if len(batch) == 1: print("  gave up on", src[0]["artist"], flush=True); return [None], None
    outs = []
    for one in batch: outs += ask(client, [one])[0]
    return outs, None

def read_bios(A, dry):
    cache = json.load(open(BIOS, encoding="utf-8")) if os.path.exists(BIOS) else {}
    items = items_for(A)
    need = [x for x in items if x[0] not in cache]
    chars = sum(len(json.dumps(it, ensure_ascii=False)) for _, it, _ in need)
    print(f"  bios: {len(items)}, cached {len(items) - len(need)}, to read {len(need)} (~{chars // 3:,} tokens in, ~${chars / 3 / 1e6 * 2 + len(need) * 60 / 1e6 * 10:.2f} at {MODEL})", flush=True)
    if dry or not need: return
    import anthropic
    client = anthropic.Anthropic()
    batches = [need[k:k + 8] for k in range(0, len(need), 8)]
    tin = tout = 0
    def work(b):
        out, u = ask(client, b)
        return b, out, u
    with ThreadPoolExecutor(4) as ex:
        for n, (b, out, u) in enumerate(ex.map(work, batches), 1):
            for (key, it, cmap), o in zip(b, out):
                if o is None: continue
                ids = lambda k: [x for x in o.get(k, []) if isinstance(x, str)]
                ev = o.get("ev") or {}
                cache[key] = dict(artist=it["artist"],
                                  teachers=[[cmap[x], ev.get(x, "")] for x in ids("teachers") if x in cmap],
                                  pupils=[[cmap[x], ev.get(x, "")] for x in ids("pupils") if x in cmap],
                                  circles=[[x, ev.get(x, "")] for x in ids("circles") if x in {c["id"] for c in CIRCLES}])
            if u: tin += u.input_tokens; tout += u.output_tokens
            if n % 10 == 0 or n == len(batches):
                json.dump(cache, open(BIOS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
                print(f"  {n}/{len(batches)} batches; tokens in {tin:,} out {tout:,}", flush=True)
    json.dump(cache, open(BIOS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"  ≈ ${tin / 1e6 * 2 + tout / 1e6 * 10:.2f}")

# ---- 3. combine ------------------------------------------------------------------------------
def combine(A):
    byname = {a["n"]: a for a in A if a.get("c", 0) > 0}
    byqid = {a["qid"]: a["n"] for a in byname.values() if a.get("qid")}
    links = {}                                              # (teacher, pupil) -> [sources, quote]
    def add(t, p, src, quote=""):
        if t == p or t not in byname or p not in byname: return
        bt, bp = born(byname[t]), born(byname[p])
        if bt and bp and bt > bp + 5: return                # a teacher born well after the pupil: a misreading
        x = links.setdefault((t, p), [set(), ""])
        x[0].add(src); x[1] = x[1] or quote
    if os.path.exists(WD):
        for t, p in json.load(open(WD)):
            if t in byqid and p in byqid: add(byqid[t], byqid[p], "wd")
    members = {c["id"]: {} for c in CIRCLES}                # circle -> name -> source
    for c in CIRCLES:
        for a in byname.values():
            if set(a.get("grp", [])) & set(c["grp"]): members[c["id"]][a["n"]] = "wd"
    cache = json.load(open(BIOS, encoding="utf-8")) if os.path.exists(BIOS) else {}
    current = {key for key, _, _ in items_for(A)}
    for key, r in cache.items():
        if key not in current or r["artist"] not in byname: continue   # a bio since edited or an artist since merged
        for t, q in r["teachers"]: add(t, r["artist"], "bio", q)
        for p, q in r["pupils"]: add(r["artist"], p, "bio", q)
        for c, q in r["circles"]: members[c].setdefault(r["artist"], "bio")
    # a circle with fewer than three members in the catalogue gets no page and no link
    out = dict(circles=[dict(c, members=sorted(members[c["id"]])) for c in CIRCLES if len(members[c["id"]]) >= 3],
               links=sorted([t, p, "+".join(sorted(s)), q] for (t, p), (s, q) in links.items()))
    for c in out["circles"]: c.pop("grp")
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    linked = {x for l in out["links"] for x in l[:2]}
    print(f"  lineage.json: {len(out['links'])} teacher links among {len(linked)} artists; circles "
          + ", ".join(f"{c['en']} {len(c['members'])}" for c in out["circles"]))

if __name__ == "__main__":
    A = load()
    if "wd" in sys.argv[1:]: fetch_wd(A)
    if "bios" in sys.argv[1:]:
        read_bios(A, "--dry-run" in sys.argv)
        if "--dry-run" in sys.argv: sys.exit(0)
    combine(A)
