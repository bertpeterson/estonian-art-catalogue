# -*- coding: utf-8 -*-
"""Read the galleries side by side -> gallery_records.json

    python3 fetch_galleries.py              # every gallery, as the weekly and monthly runs list them
    python3 fetch_galleries.py haus kogo    # only these

One after another, the weekly run's reading took 164 minutes (8 Oct 2026), most of it
waiting on a few galleries that serve a page a work. They are different servers, so
each is read at the same time as the others, and each still at its own polite pace.

Every script replaces its own gallery's records in gallery_records.json, reading the
file first -- side by side they would write over one another. So each group runs in a
folder of its own: links to everything in data/ (the scripts, their caches, their side
files, each group's its own), and a copy of gallery_records.json. Afterwards every
gallery takes its records from the group whose script changed them, in the order the
groups are listed -- the order a run one after another left them in. Artman reads
Artner's fresh records (a work at both is left to Artner), so it follows Artner; NOBA's four steps
are one group, in their order; its artist steps read the other galleries' records as
they were before this run, so a name new elsewhere this week counts for NOBA next week.

A script that fails -- a page its gallery would not serve, store_api.py -- leaves that
group's galleries with last week's records, and the run goes on with the others: Allee's
pages refused on GitHub's runners stopped the whole weekly run three Thursdays running
(1-15 Oct 2026); Allee's stock is no longer read since 29 Oct 2026, its records
standing as last read. The group is noted in gallery_kept.json with the day it was first not
read; one not read for two weeks fails the run, once every group has finished and its
log has been printed, so a parser that broke for good is still looked at.
"""
import json, os, sys, shutil, subprocess, tempfile, time, datetime
from concurrent.futures import ThreadPoolExecutor

here = os.path.dirname(os.path.abspath(__file__))
REC = "gallery_records.json"
KEPT = os.path.join(here, "gallery_kept.json")    # group -> the day it was first not read
GROUPS = [["haus"], ["kogo"], ["temnikova"], ["tutar"], ["artrovert"], ["ruki"], ["eks"], ["vernissage"],
          ["konradmagi"], ["artner", "artman"], ["tokkoarrak"], ["artandtonic"],
          ["noba", "noba_artists", "noba_artworks", "noba"]]

def run(group):
    d = tempfile.mkdtemp(prefix="gal-")
    for f in os.listdir(here):
        if f != REC: os.symlink(os.path.join(here, f), os.path.join(d, f))
    if os.path.exists(os.path.join(here, REC)): shutil.copy(os.path.join(here, REC), d)
    t0, log, ok = time.time(), [], True
    for s in group:
        r = subprocess.run([sys.executable, "-u", f"{s}.py"], cwd=d, capture_output=True, text=True)
        log.append(f"=== {s} ===\n{r.stdout}{r.stderr}")
        if r.returncode: ok = False; log.append(f"FAILED: {s}.py exited {r.returncode}\n"); break
    out = json.load(open(os.path.join(d, REC), encoding="utf-8")) if ok and os.path.exists(os.path.join(d, REC)) else None
    shutil.rmtree(d, ignore_errors=True)
    return "".join(log) + f"--- {' + '.join(group)}: {time.time() - t0:.0f} s\n", ok, out

def by_gallery(recs):
    g = {}
    for r in recs: g.setdefault(r.get("gallery"), []).append(r)
    return g

if __name__ == "__main__":
    groups = [g for g in GROUPS if not sys.argv[1:] or set(g) & set(sys.argv[1:])]
    before = json.load(open(os.path.join(here, REC), encoding="utf-8")) if os.path.exists(os.path.join(here, REC)) else []
    old = by_gallery(before)
    with ThreadPoolExecutor(len(groups)) as ex: results = list(ex.map(run, groups))
    new, owner, failed = {}, {}, []
    for group, (log, ok, out) in zip(groups, results):
        print(log, flush=True)
        if not ok: failed.append(group[0]); continue
        got = by_gallery(out)
        for name in set(old) | set(got):
            if got.get(name) == old.get(name): continue
            if name in owner: sys.exit(f"{name}: changed by both {owner[name]} and {group[0]}")
            owner[name] = group[0]; new[name] = got.get(name, [])
    keep = [r for r in before if r.get("gallery") not in new]
    for group in groups:                                   # each group's galleries, in the groups' order
        for name in [n for n, o in owner.items() if o == group[0]]: keep += new[name]
    json.dump(keep, open(os.path.join(here, REC), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"gallery_records.json: {len(keep)} records; changed: {', '.join(sorted(new)) or 'none'}")
    kept, today = (json.load(open(KEPT)) if os.path.exists(KEPT) else {}), datetime.date.today()
    for group in groups:
        if group[0] in failed: kept.setdefault(group[0], today.isoformat())
        else: kept.pop(group[0], None)
    json.dump(dict(sorted(kept.items())), open(KEPT, "w"), indent=0)
    if failed: print(f"not read, last week's records kept: {', '.join(failed)}")
    stale = [g for g, d in kept.items() if (today - datetime.date.fromisoformat(d)).days >= 14]
    if stale: sys.exit(f"not read for two weeks or more: {', '.join(f'{g} (since {kept[g]})' for g in stale)}")
