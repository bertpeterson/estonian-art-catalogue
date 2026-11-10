# -*- coding: utf-8 -*-
"""The daily look at the galleries' stock -> stock_gone.json

The weekly run (galleries.yml) reads every gallery afresh. Between two such runs a work
that sells stayed on museaal.ee for up to a week, its card linking to a gallery page that
says sold. Once a day this reads again the galleries that are quick to read -- through the
same scripts the weekly run uses, so each gallery's own way of saying sold is the one read
-- and notes every work for sale here that has left: sold, where the gallery says so,
otherwise no longer listed.

    python3 stock_check.py          # read the quick galleries, update stock_gone.json
    python3 stock_check.py apply    # data.json: the works in stock_gone.json become past listings
    python3 stock_check.py unapply  # data.json as it was before `apply`, once the site is built

Removals only. A new work or a changed price waits for the weekly run, which empties
stock_gone.json: its harvest says the same, and a work back on sale comes back. Artrovert
and Tokko & Arrak are left to it (a page a work, ~3 s each), as are the NOBA artist pages
that mark a sale by dropping the price. A gallery whose reading finds fewer than 70% of the
works it had still on sale is skipped that day -- a failed fetch, not a sell-out.

build_site.sh runs `apply` first, so every page built -- the artist pages, Buy art, the
register -- reads the stock the same way. In data.json a work that left becomes what
merge.py makes of a past listing: kind "sold", gs 1 (the gallery said sold) or 0 (no
longer listed), no picture, no price.

data.json is tracked, and the build is not what changes it: merge.py is. So `apply` keeps
the file as it was (data.before_apply.json, not tracked) and build_site.sh ends with
`unapply`, which puts it back -- unless something else has written data.json since, when
it is left alone. A build no longer leaves the checkout modified; the next build applies
stock_gone.json again.
"""
import json, os, re, sys, shutil, subprocess, datetime, hashlib

here = os.path.dirname(os.path.abspath(__file__))
GONE = os.path.join(here, "stock_gone.json")
# the script, and the gallery whose records it replaces in gallery_records.json
QUICK = [("artner", "Artner"), ("vernissage", "Vernissage"), ("artman", "Artman"), ("artkeller", "Art Keller"), ("idla", "Idla Antiik"),
         ("artandtonic", "Art & Tonic"), ("eks", "E-Kunstisalong"), ("kogo", "Kogo galerii"), ("ruki", "Ruki galerii"),
         ("tutar", "Tütar galerii"), ("haus", "Haus Galerii"), ("noba", "NOBA")]
# what the scripts write besides gallery_records.json; put back afterwards, so a run leaves only stock_gone.json changed
SIDE = ["gallery_records.json", "noba_raw.json", "noba_sold.json"]
key = lambda gid: "G" + re.sub(r"[^A-Za-z0-9]", "", gid)           # merge.py's k for a gallery record

def load(f, empty):
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else empty

def check():
    today = datetime.date.today().isoformat()
    d = json.load(open(os.path.join(here, "data.json"), encoding="utf-8"))
    mu = d["vocab"]["mu"]
    stock = {}                                                          # gallery -> keys for sale
    for w in d["works"]:
        if w.get("kind") == "gallery": stock.setdefault(mu[w["mu"]] if isinstance(w["mu"], int) else w["mu"], set()).add(w["k"])
    gone = load(GONE, {})
    back = {f: open(os.path.join(here, f), "rb").read() for f in SIDE if os.path.exists(os.path.join(here, f))}
    try:
        for script, gal in QUICK:
            have = stock.get(gal, set())
            if not have: continue
            try:
                r = subprocess.run([sys.executable, "-u", f"{script}.py"], cwd=here, timeout=900, capture_output=True, text=True)
                ok = r.returncode == 0
            except subprocess.TimeoutExpired:
                ok = False
            if not ok: print(f"  {gal:16} not read today"); continue
            now = {}
            for g in load(os.path.join(here, "gallery_records.json"), []):
                if g.get("gallery") != gal: continue
                sold = bool(g.get("sold")) or bool(re.search(r"\b(müüdud|sold)\b", g.get("tech") or "", re.I))
                now[key(g["gid"])] = sold
            live = sum(1 for k in have if now.get(k) is False)
            if live < 0.7 * len(have):
                print(f"  {gal:16} skipped: {live} of {len(have)} still read as for sale"); continue
            left = 0
            for k in have:
                if now.get(k) is False: gone.pop(k, None)
                elif k not in gone: gone[k] = [today, int(bool(now.get(k)))]; left += 1
            print(f"  {gal:16} {len(have) - live} of {len(have)} gone, {left} new today")
    finally:
        for f, b in back.items(): open(os.path.join(here, f), "wb").write(b)
    json.dump(dict(sorted(gone.items())), open(GONE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"stock_gone.json: {len(gone)} works no longer for sale since the weekly run")

BEFORE = os.path.join(here, "data.before_apply.json")       # data.json as `apply` found it
MARK = BEFORE + ".sha256"                                    # ...and the hash of what `apply` wrote in its place

def sha(f):
    h = hashlib.sha256()
    with open(f, "rb") as x:
        for b in iter(lambda: x.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def unapply():
    """data.json as it was before `apply`, if it is still what `apply` wrote: a merge.py run since is left standing"""
    if not os.path.exists(BEFORE): return
    f = os.path.join(here, "data.json")
    mine = os.path.exists(MARK) and os.path.exists(f) and open(MARK).read().strip() == sha(f)
    if mine: os.replace(BEFORE, f)
    else: os.remove(BEFORE)
    if os.path.exists(MARK): os.remove(MARK)

def apply():
    gone = load(GONE, {})
    if not gone: return
    f = os.path.join(here, "data.json")
    d = json.load(open(f, encoding="utf-8"))
    n = s = 0
    for w in d["works"]:
        g = gone.get(w.get("k"))
        if not g or w.get("kind") != "gallery": continue
        w["kind"], w["gs"], w["im"], w["gl"] = "sold", g[1], None, g[0][:7]
        w.pop("pr", None)
        n += 1; s += g[1]
    if not n: return
    m = d["meta"]
    m["gallery"] -= n; m["past"] += n; m["past_sold"] += s
    unapply()                                   # a build that stopped midway left its copy: that one is the original
    shutil.copy2(f, BEFORE)
    with open(f, "w", encoding="utf-8") as out: json.dump(d, out, ensure_ascii=False, separators=(",", ":"))
    with open(MARK, "w") as out: out.write(sha(f))
    print(f"  stock          {n} works no longer for sale since the weekly run ({s} sold), from stock_gone.json")

if __name__ == "__main__":
    apply() if sys.argv[1:] == ["apply"] else unapply() if sys.argv[1:] == ["unapply"] else check()
