# -*- coding: utf-8 -*-
"""Read every gallery's and house's robots.txt before the monthly harvest; stop if one says no.

"No" is any of: `Disallow: /` for all agents, for this project's agent, or for ClaudeBot (the
agent of the assistant that runs this project -- it is treated as addressed to us); or a
Cloudflare Content-Signal line with `search=no` (a catalogue that lists works and links back is
search in that vocabulary). A missing file, or one that only fences off admin paths, is a yes.
Exit 1 stops the workflow before anything is fetched, the same way harvest_guard.py does after.
"""
import re, sys, urllib.request

HOSTS = ["haus.ee", "www.kogogallery.ee", "temnikova.ee", "www.tutar.ee", "www.artrovert.ee", "rukigalerii.ee",
         "alleegalerii.ee", "vernissage.ee", "eestikunstioksjonid.ee", "www.vaal.ee", "oksjon.vaal.ee",
         "www.e-kunstisalong.ee", "noba.ac"]
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
OURS = {"*", "estonianartcatalogue", "claudebot", "claude-user", "claude-searchbot", "anthropic-ai"}

def verdict(txt):
    """(ok, reason) for one robots.txt"""
    groups, last_ua = [], False          # a run of User-agent lines opens one group
    for raw in txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line: continue
        m = re.match(r"(?i)content-signal\s*:\s*(.*)", raw.strip())
        if m and re.search(r"search\s*=\s*no", m.group(1), re.I): return False, "Content-Signal search=no"
        k, _, v = line.partition(":"); k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if not last_ua: groups.append(([], []))
            groups[-1][0].append(v.lower()); last_ua = True
        else:
            last_ua = False
            if k == "disallow" and groups: groups[-1][1].append(v)
    for ags, dis in groups:
        if any(a in OURS or a.startswith("claude") for a in ags) and any(d in ("/", "/*", "*") for d in dis):
            return False, f"Disallow: / for {', '.join(ags)}"
    return True, "ok"

bad = []
for h in HOSTS:
    try:
        r = urllib.request.Request(f"https://{h}/robots.txt", headers={"User-Agent": UA})
        with urllib.request.urlopen(r, timeout=30) as f: txt = f.read().decode("utf-8", "replace") if f.status == 200 else ""
    except Exception as e:
        txt = ""
    ok, why = verdict(txt)
    print(f"  {'ok ' if ok else 'NO '} {h:28} {why}")
    if not ok: bad.append((h, why))
if bad:
    print("\nROBOTS: a source asks not to be collected from; the run stops here:", bad); sys.exit(1)
print(f"\nROBOTS: {len(HOSTS)} sources read, none says no")
