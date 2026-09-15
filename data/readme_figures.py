# -*- coding: utf-8 -*-
"""Write the current figures into README.md.

validate.py warns when the README quotes a figure the data no longer matches. Until
now the fix was a hand-edit after every re-merge; the monthly gallery re-harvest
makes that a monthly chore, so it is a script. Every pattern here is anchored on
the wording around the number, and a pattern that no longer matches is reported
rather than silently skipped -- the README changing shape must not hide a stale
figure again.
"""
import io, json, re, sys, os

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
m = json.load(open(os.path.join(root, "data", "data.json"), encoding="utf-8"))["meta"]
p = os.path.join(root, "README.md")
s = io.open(p, encoding="utf-8").read()
f = lambda n: f"{n:,}"

subs = [
    (r"\*\*[\d,]+ artworks\*\*",                        f"**{f(m['works'])} artworks**"),
    (r"\*\*[\d,]+ artists\*\*",                         f"**{f(m['artists'])} artists**"),
    (r"\| [\d,]+ \| Muuseumide Infosüsteem",           f"| {f(m['muis'])} | Muuseumide Infosüsteem"),
    (r"\| [\d,]+ \| The Art Museum of Estonia's own", f"| {f(m['ekm'])} | The Art Museum of Estonia's own"),
    (r"\| (\w+) commercial galleries and NOBA \| [\d,]+ \|", lambda mm: f"| {mm.group(1)} commercial galleries and NOBA | {f(m['gallery'])} |"),
    (r"\| Auction results: ([^|]+) \| [\d,]+ lots \|",      lambda mm: f"| Auction results: {mm.group(1)} | {f(m['auction'])} lots |"),
    (r"Of the works for sale, [\d,]+ are NOBA listings, [\d,]+ the galleries' own",
     f"Of the works for sale, {f(m['noba'])} are NOBA listings, {f(m['gallery'] - m['noba'])} the galleries' own"),
    (r"[\d,]+ objects appear in both",                  f"{f(m['both'])} objects appear in both"),
    (r"which is why [\d,]+ source objects",             f"which is why {f(m['objects'])} source objects"),
    (r"collapse to [\d,]+ works\.",                     f"collapse to {f(m['works'])} works."),
    (r"[\d,]+ of them, [\d.]+% — derive",               f"{f(m['held'])} of them, {m['held']/m['works']*100:.1f}% — derive"),
    (r"works\.csv\.gz(\s+)[\d,]+ rows",                 lambda mm: f"works.csv.gz{mm.group(1)}{f(m['works'])} rows"),
    (r"artists\.csv\.gz(\s+)[\d,]+ rows",               lambda mm: f"artists.csv.gz{mm.group(1)}{f(m['artists'])} rows"),
]
missing = []
for pat, rep in subs:
    s, n = re.subn(pat, rep, s, count=1)
    if n == 0: missing.append(pat)
io.open(p, "w", encoding="utf-8").write(s)
print(f"README figures: {len(subs) - len(missing)} written")
if missing:
    print("  patterns that no longer match the README (figure may be stale):")
    for x in missing: print("   ", x)
    sys.exit(1)
