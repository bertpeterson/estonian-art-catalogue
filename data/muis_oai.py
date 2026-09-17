# -*- coding: utf-8 -*-
"""MuIS art collections the catalogue lacks, through the OAI-PMH service -> oai_records.json

The first harvest read MuIS's object pages. MuIS also publishes its records through
OAI-PMH, the interface built for harvesters (https://www.muis.ee/OAIService/OAIService):
ListIdentifiers with the ESE prefix and a museum's set returns every object id with its
sub-collection in one response; GetRecord with the LIDO prefix returns the full record --
maker with role and dates, title, work type, technique, measurements, description,
the pictures' media ids with their pixel sizes. This reads the art collections named in
SETS, skips every id the catalogue already holds, fetches the rest one record at a time
(four in flight, a pause between), caches each answer, and writes records in the shape
records.json has, so merge.py needs nothing new. The pictures' ids and shapes go to
oai_images.json and oai_shapes.json.

    python3 muis_oai.py TM            one museum
    python3 muis_oai.py               every museum in SETS
"""
import re, json, os, sys, gzip, time, html, collections, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

OAI = "https://www.muis.ee/OAIService/OAIService"
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
CACHE = "oaicache"; os.makedirs(CACHE, exist_ok=True)
# museum set -> the sub-collections that are art (from ListSets; names in the comment)
SETS = {
    "TM":   ["TM:_:K"],                                          # Tartu Linnamuuseum · Kunstikogu
    "MM":   ["MM:_:K"],                                          # Eesti Meremuuseum · Kunstikogu
    "ERM":  ["ERM:K"],                                           # Eesti Rahva Muuseum · Kunstikogu
    "AM":   ["AM:_:G"],                                          # Eesti Ajaloomuuseum · Kujutav kunst
    "TKM":  ["TKM:TR:G", "TKM:TR:B", "TKM:TR:M", "TKM:TR:A", "TKM:TR:H", "TKM:TR:E", "TKM:TR:GD",
             "TKM:TR:S", "TKM:TR:FV", "TKM:ASM:ASM B", "TKM:ASM:ASM S", "TKM:RF"],   # Tartu Kunstimuuseum
    "EKM":  ["EKM:j:G", "EKM:j:M", "EKM:j:S", "EKM:j:B"],        # Eesti Kunstimuuseum · Graafika, Maal, Skulptuur, hõbe
}

def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(5 * (k + 1))
    return ""

def identifiers(mus):
    """every id in the museum's set, with its sub-collection; cached for a month"""
    p = os.path.join(CACHE, f"ids_{mus}.xml.gz")
    if os.path.exists(p) and time.time() - os.path.getmtime(p) < 30 * 86400:
        with gzip.open(p, "rt", encoding="utf-8") as f: x = f.read()
    else:
        x = get(f"{OAI}?verb=ListIdentifiers&metadataPrefix=ese&set={mus}")
        if x:
            with gzip.open(p, "wt", encoding="utf-8") as f: f.write(x)
    return re.findall(r"<identifier>oai:muis\.ee:(\d+)</identifier><datestamp>[^<]*</datestamp><setSpec>(.*?)</setSpec>", x)

def record(mid):
    p = os.path.join(CACHE, f"lido_{mid}.xml.gz")
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    x = get(f"{OAI}?verb=GetRecord&metadataPrefix=lido&identifier=oai:muis.ee:{mid}")
    if "<lido:lido>" in x:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(x)
    time.sleep(0.5)
    return x

U = html.unescape
def texts(x, tag): return [U(t).strip() for t in re.findall(rf"<lido:{tag}[^>]*>([^<]*)</lido:{tag}>", x)]
def block(x, tag): return re.findall(rf"<lido:{tag}[^>]*>(.*?)</lido:{tag}>", x, re.S)
def display_name(n):
    """'Neff, Karl Timoleon von' -> 'Karl Timoleon von Neff'; a name without a comma stays"""
    n = U(n).strip()
    if "," in n:
        sur, rest = [p.strip() for p in n.split(",", 1)]
        return f"{rest} {sur}".strip()
    return n
MEDIUM = {"õlivärvimine": "õli", "akvarellimine": "akvarell", "guaššimine": "guašš", "temperamaal": "tempera", "pastellimine": "pastell"}

def parse(mid, x, subset):
    if "<lido:lido>" not in x: return None
    r = {"id": mid, "oai_set": subset}
    t = texts(x, "appellationValue")
    r["title"] = next((U(v) for v in re.findall(r'<lido:titleSet[^>]*>\s*<lido:appellationValue[^>]*>([^<]*)', x)), "")
    # museum and collection
    m = re.search(r'<lido:repositoryName>.*?<lido:appellationValue>([^<]*)', x, re.S)
    r["museum"] = U(m.group(1)).strip() if m else ""
    m = re.search(r'<lido:classification lido:type="muuseumikogu">\s*<lido:term>([^<]*)', x)
    r["collection"] = U(m.group(1)).strip() if m else ""
    m = re.search(r'<lido:workID[^>]*>([^<]*)</lido:workID>', x)
    r["num"] = U(m.group(1)).strip() if m else ""
    m = re.search(r'<lido:objectWorkType[^>]*>\s*<lido:term>([^<]*)', x)
    r["essence"] = U(m.group(1)).strip() if m else ""
    # some museums leave the work type empty or "???" and open the title with it
    # instead -- "Graafika. Tartu näituseväljak", "Akvarell, koopia", "Exlibris"
    if r["essence"] in ("", "???"):
        tm = re.match(r"^(pliiatsijoonistus|tušijoonistus|joonistus|graafika|maal|akvarell|pastell|guašš|eksliibris|exlibris|skulptuur|foto|kavand|litograafia|ofort|puulõige|linoollõige|plakat|postkaart|õnnitluskaart)\b", r["title"], re.I)
        r["essence"] = {"exlibris": "eksliibris", "pliiatsijoonistus": "joonistus", "tušijoonistus": "joonistus"}.get(tm.group(1).lower(), tm.group(1).lower()) if tm else ""
    # the making event: maker, date, technique, material
    ev = next((e for e in block(x, "event") if "valmistamine" in e), "")
    author = None; life = None
    for a in block(ev, "actorInRole"):
        role = "".join(texts(a, "term")).lower()
        name = next((U(v) for v in re.findall(r'lido:pref="preferred"[^>]*>([^<]*)</lido:appellationValue>', a)), "")
        if not name: continue
        if author is None or role == "autor":     # the maker; "originaali autor" only if no maker
            author = name
            ed, ld = texts(a, "earliestDate"), texts(a, "latestDate")
            life = [ed[0] if ed else "", ld[0] if ld else ""] if (ed or ld) else None
            if role == "autor": break
    if author: r["author"] = author; r["artist"] = display_name(author); r["artist_key"] = author
    if life and (life[0] or life[1]): r["life"] = life
    dm = re.search(r"<lido:eventDate>.*?<lido:earliestDate>([^<]*)</lido:earliestDate>.*?<lido:latestDate>([^<]*)</lido:latestDate>", ev, re.S)
    if dm:
        a, b = dm.group(1).strip(), dm.group(2).strip()
        r["date"] = a if a == b or not b else f"{a}–{b}"
    tech, mat = [], []
    for kind, body in re.findall(r'<lido:termMaterialsTech lido:type="([^"]*)">(.*?)</lido:termMaterialsTech>', ev, re.S):
        terms = texts(body, "term")
        if not terms: continue
        last = terms[-1].lower()
        (tech if kind == "tehnika" else mat).append(MEDIUM.get(last, last))
    if tech: r["tech"] = ", ".join(dict.fromkeys(tech))
    if mat: r["mat"] = ", ".join(dict.fromkeys(mat))
    # measurements: "kõrgus: 69.0 cm; laius: 55.0 cm", the record's own before a frame's
    ms = []
    for s in block(x, "measurementsSet"):
        ty, un, va = texts(s, "measurementType"), texts(s, "measurementUnit"), texts(s, "measurementValue")
        if ty and va and un and un[0] != "pixel": ms.append(f"{ty[0]}: {va[0]} {un[0]}")
    if ms: r["dims"] = "; ".join(ms[:4])
    # description: the museum's description, not its comments or condition notes
    for d in block(x, "objectDescriptionSet"):
        kind = "".join(texts(d, "sourceDescriptiveNote")).lower()
        v = "".join(texts(d, "descriptiveNoteValue")).strip()
        if v and len(v) > 12 and kind in ("kirjeldus", "füüsiline kirjeldus", "sisu kirjeldus", ""):
            r["desc"] = v[:700]; break
    # pictures: the first jpg resource, with its pixel size for the wall
    for res in block(x, "resourceSet"):
        rid = re.search(r'<lido:resourceID[^>]*>([^<]*)</lido:resourceID>', res)
        if rid and 'lido:formatResource="jpg"' in res:
            r["media"] = rid.group(1).strip()
            w = re.search(r"<lido:measurementType>width</lido:measurementType>\s*<lido:measurementUnit>pixel</lido:measurementUnit>\s*<lido:measurementValue>([\d.]+)", res)
            h = re.search(r"<lido:measurementType>height</lido:measurementType>\s*<lido:measurementUnit>pixel</lido:measurementUnit>\s*<lido:measurementValue>([\d.]+)", res)
            if w and h and float(w.group(1)) > 0: r["shape"] = round(float(h.group(1)) / float(w.group(1)), 3)
            break
    return r

if __name__ == "__main__":
    which = sys.argv[1:] or list(SETS)
    have = {r["id"] for r in json.load(open("records.json", encoding="utf-8"))}
    out = json.load(open("oai_records.json", encoding="utf-8")) if os.path.exists("oai_records.json") else []
    done = {r["id"] for r in out}
    imgs = json.load(open("oai_images.json", encoding="utf-8")) if os.path.exists("oai_images.json") else {}
    shapes = json.load(open("oai_shapes.json", encoding="utf-8")) if os.path.exists("oai_shapes.json") else {}
    for mus in which:
        pairs = identifiers(mus)
        want = [(i, s) for i, s in pairs if s in SETS[mus] and i not in have and i not in done]
        print(f"{mus}: {len(pairs):,} ids listed; {len(want):,} to fetch from {len(SETS[mus])} sub-collections", flush=True)
        n = kept = 0
        with ThreadPoolExecutor(4) as ex:
            for (mid, subset), x in zip(want, ex.map(lambda p: record(p[0]), want)):
                n += 1
                r = parse(mid, x, subset)
                if r:
                    out.append(r); kept += 1
                    if r.get("media"):
                        imgs["muis:" + mid] = r["media"]
                        if r.get("shape"): shapes[r["media"]] = r["shape"]
                if n % 500 == 0:
                    json.dump(out, open("oai_records.json", "w", encoding="utf-8"), ensure_ascii=False)
                    json.dump(imgs, open("oai_images.json", "w", encoding="utf-8")); json.dump(shapes, open("oai_shapes.json", "w", encoding="utf-8"))
                    print(f"  {mus} {n:,}/{len(want):,}  kept {kept:,}", flush=True)
        json.dump(out, open("oai_records.json", "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(imgs, open("oai_images.json", "w", encoding="utf-8")); json.dump(shapes, open("oai_shapes.json", "w", encoding="utf-8"))
        c = collections.Counter(bool(r.get("author")) for r in out if r.get("oai_set") in SETS[mus])
        print(f"  {mus} done: {kept:,} records this run; with a maker {c[True]:,}, without {c[False]:,}", flush=True)
    print(f"\nOAI RECORDS: {len(out):,} in oai_records.json; {len(imgs):,} pictures")
