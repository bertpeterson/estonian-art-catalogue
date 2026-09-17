# -*- coding: utf-8 -*-
"""Similar artists -> a["sim"] on every artist in data.json

For someone who likes what they see on an artist's page and wants more of it. Two artists
are near when their work looks alike from a distance: the same decades, the same media,
the same techniques, the same subjects in the titles (maastik, portree, akt, natüürmort,
linn, meri...), and, where the record knows it, the same movement, school or museum
category. Each is a vector over its bag; the cosine of each, weighted, is the distance;
an artist's six nearest, among artists with at least five works, are kept. The weights
are a judgement: period and medium first, because a viewer who liked Mägi's 1910s
paintings is better sent to Triik than to a 1970s printmaker who also drew landscapes.
"""
import json, re, collections, unicodedata
import numpy as np

d = json.load(open("data.json", encoding="utf-8"))
A, W, V = d["artists"], d["works"], d["vocab"]
name = lambda f, v: V[f][v] if isinstance(v, int) and f in V else v
MIN_WORKS, K = 5, 6

# the subjects a title names; a small vocabulary, folded, one hit per word
SUBJ = {"maastik": "landscape", "vaade": "landscape", "mets": "landscape", "meri": "sea", "rand": "sea", "laev": "sea", "sadam": "sea",
        "portree": "portrait", "autoportree": "portrait", "pea": "portrait", "akt": "nude", "figuur": "figure", "naine": "figure", "mees": "figure", "laps": "figure",
        "natuurmort": "stilllife", "lilled": "stilllife", "vaas": "stilllife", "linn": "city", "tanav": "city", "maja": "city", "kirik": "city", "tallinn": "city", "tartu": "city",
        "talv": "winter", "kevad": "season", "sugis": "season", "suvi": "season", "ohtu": "light", "hommik": "light",
        "kompositsioon": "abstract", "abstraktsioon": "abstract", "vorm": "abstract", "illustratsioon": "illustration", "eksliibris": "exlibris", "plakat": "poster",
        "kalevipoeg": "myth", "muinasjutt": "myth", "too": "labour", "tootaja": "labour", "kolhoos": "labour", "loom": "animal", "hobune": "animal", "lind": "animal", "kass": "animal", "koer": "animal"}
fold = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))

n = len(A)
dec, med, tech, subj, tags = (collections.defaultdict(collections.Counter) for _ in range(5))
count = collections.Counter()
for w in W:
    a = w["a"]; count[a] += 1
    if w.get("y"): dec[a][w["y"] // 10 * 10] += 1
    e = name("e", w.get("e"))
    if e: med[a][e] += 1
    tc = name("tc", w.get("tc")) or ""
    for t in re.split(r"[,;/ ]+", fold(tc)):
        if len(t) > 2: tech[a][t] += 1
    for word in re.findall(r"[a-z]+", fold(w.get("t") or "")):
        if word in SUBJ: subj[a][SUBJ[word]] += 1
    c = name("c", w.get("c"))
    if c: tags[a]["cat:" + c] += 1
for i, a in enumerate(A):
    for g in a.get("grp") or []: tags[i][g] += 3       # a stated movement or school weighs like three works
    if a.get("aff"): tags[i]["aff:" + a["aff"]] += 1

def matrix(bags):
    keys = {k: j for j, k in enumerate(sorted({k for b in bags.values() for k in b}))}
    M = np.zeros((n, len(keys)), dtype=np.float32)
    for i, b in bags.items():
        for k, v in b.items(): M[i, keys[k]] = v
    M = np.sqrt(M)                                     # damp the prolific
    nrm = np.linalg.norm(M, axis=1, keepdims=True); nrm[nrm == 0] = 1
    return M / nrm
# neighbouring decades count a little: a 1920s painter is near a 1930s one
Md = matrix(dec)
Dk = sorted({k for b in dec.values() for k in b}); Dm = np.zeros((n, len(Dk)), dtype=np.float32)
for i, b in dec.items():
    for k, v in b.items():
        j = Dk.index(k); Dm[i, j] += v
        if j > 0: Dm[i, j - 1] += v * 0.5
        if j + 1 < len(Dk): Dm[i, j + 1] += v * 0.5
Dm = np.sqrt(Dm); nrm = np.linalg.norm(Dm, axis=1, keepdims=True); nrm[nrm == 0] = 1; Dm /= nrm
Mm, Mt, Ms, Mg = matrix(med), matrix(tech), matrix(subj), matrix(tags)
Wt = [(Dm, 0.30), (Mm, 0.22), (Mt, 0.15), (Ms, 0.18), (Mg, 0.15)]

cand = np.array([count[i] >= MIN_WORKS for i in range(n)])
sims = 0
for start in range(0, n, 512):
    sl = slice(start, min(n, start + 512))
    S = sum(wt * (M[sl] @ M.T) for M, wt in Wt)
    S[:, ~cand] = -1
    for r, i in enumerate(range(sl.start, sl.stop)):
        S[r, i] = -1
        if count[i] < 2: continue                          # one work says too little about a style
        order = np.argsort(-S[r])[:K]
        A[i]["sim"] = [int(j) for j in order if S[r, j] > 0.35]
        sims += bool(A[i]["sim"])
json.dump(d, open("data.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"SIMILAR ARTISTS: {sims:,} of {n:,} artists have neighbours; {int(cand.sum()):,} candidates")
for nm in ["Konrad Mägi", "Eduard Wiiralt", "Jüri Arrak", "Karin Luts", "Malle Leis", "Johann Köler", "Kristjan Raud"]:
    i = next(i for i, a in enumerate(A) if a["n"] == nm)
    print(f"  {nm:16} -> " + ", ".join(A[j]["n"] for j in A[i].get("sim", [])))
