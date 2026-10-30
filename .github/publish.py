# -*- coding: utf-8 -*-
"""The scheduled runs' last step, in a job of its own (auctions.yml, galleries.yml, reharvest.yml, stock.yml).

The job that reads the galleries and auction houses runs scrapers, pip packages and image decoders, and holds no
token that can write: what it changed in tracked files comes here as an artifact. This job, in a fresh checkout of
the same commit and holding the write token, takes a file only if it is a data file this run may change -- a
regular file, already tracked, at a path one of the run's patterns names, and a whole JSON document (gzipped, for
data/raw) where it is one -- and refuses the whole run otherwise, before anything is committed. Never
data/mood_api.json, which names the Worker the pages call and the Content-Security-Policy lets in, and never
data/masterpieces.json, the artwall chosen by hand. So code that the reading job ran cannot reach the repository
through it, whatever it does there.

    python3 -I .github/publish.py <the artifact's folder> <pattern> [<pattern> ...]      # from the checkout's root

A pattern is a path from the repository's root; * stands for one name, never a folder ("data/*.json").
"""
import gzip, json, os, re, subprocess, sys

NEVER = {"data/mood_api.json", "data/masterpieces.json"}

src, patterns = sys.argv[1], sys.argv[2:]
if not patterns: sys.exit("publish: no patterns, nothing may be taken")
allowed = [re.compile("^" + re.escape(p).replace(r"\*", r"[^/]+") + "$") for p in patterns]
tracked = set(subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0"))

bad, take = [], []
for d, dirs, files in os.walk(src):                    # a link to a folder is listed, never followed
    for name in sorted(files) + sorted(x for x in dirs if os.path.islink(os.path.join(d, x))):
        p = os.path.join(d, name)
        rel = os.path.relpath(p, src).replace(os.sep, "/")
        if os.path.islink(p) or not os.path.isfile(p):
            bad.append(f"{rel}: not a regular file"); continue
        if rel in NEVER or not any(a.match(rel) for a in allowed):
            bad.append(f"{rel}: not a file this run may change"); continue
        if rel not in tracked:
            bad.append(f"{rel}: not a tracked file"); continue
        raw = open(p, "rb").read()
        try:
            if rel.endswith(".json.gz"): json.loads(gzip.decompress(raw))
            elif rel.endswith(".json"): json.loads(raw)
        except Exception as e:
            bad.append(f"{rel}: not a whole JSON document ({e.__class__.__name__})"); continue
        take.append((rel, raw))

if bad:
    print("publish: REFUSED, nothing taken or committed:")
    for b in bad: print("   ", b)
    sys.exit(1)
for rel, raw in take:
    if os.path.islink(rel): sys.exit(f"publish: {rel} is a link in the checkout")
    with open(rel, "wb") as f: f.write(raw)
    print("  taking", rel)
print(f"publish: {len(take)} file(s) taken")
