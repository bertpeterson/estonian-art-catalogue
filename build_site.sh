#!/bin/bash
# Rebuild the self-hosted static site from data/data.json
set -e
cd "$(dirname "$0")"
# i18n.json is generated, not hand-kept. build_site.py only copies it, so edits to
# i18n.py reached the repo but never the site until this ran here.
python3 -u i18n.py
(cd data && python3 similar.py) || exit 1     # a["sim"]: six nearest artists, into data.json
python3 build_site.py
python3 build_landing.py || exit 1
python3 -u build_index.py || exit 1

# flat exports for reuse (CSV + JSONL), written into site/data/export/
(cd data && python3 -u validate.py && python3 -u export_csv.py)

# crawlable artist pages + sitemap (the app itself is a fragment-addressed SPA)
python3 -u build_pages.py
# the hubs: by decade, medium, museum and subject, both languages (appends to the sitemap)
python3 -u build_hubs.py || exit 1
# the embeds: a strip per artist, decade and subject for other people's pages
python3 -u build_embed.py || exit 1
# the catalogue in figures
python3 -u build_stats.py
# the Content-Security-Policy, into every page, from the inline scripts as written
python3 -u csp.py site || exit 1
# a build that lost its pages must not ship: the artist pages went out missing once
# when build_pages.py failed inside a pipe and the OK line hid it
[ -f site/a/index.html ] && [ "$(ls site/a | wc -l)" -gt 1000 ] && [ -f site/stats.html ] && [ -f site/stats-et.html ] || { echo "BUILD FAILED: site/a or stats missing"; exit 1; }
