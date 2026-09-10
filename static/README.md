Files here are copied verbatim into `site/` on every build.

`build_site.py` starts by deleting `site/` outright, so anything dropped in there by
hand disappears on the next build. Things that must survive — the Google Search
Console verification file, and the CNAME file when the site moves to its own domain —
live here instead.
