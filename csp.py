# -*- coding: utf-8 -*-
"""A Content-Security-Policy for every page in site/, written into its <head>.

GitHub Pages sets no security headers, so the policy travels in a <meta> tag. It
allows scripts only from this site, GoatCounter, and the inline scripts the build
itself wrote -- each named by the SHA-256 of its exact text, so an inline script
that arrived any other way does not run; pictures from any https server (the
museums' and galleries' own); styles inline (the tiles carry their shapes as
style attributes) and from Google Fonts; connections to this site (the data files)
and to GoatCounter; no plugins, no <base>, no forms. The app's inline event
handlers went in the same change: a policy with hashes does not admit them.

Runs last in build_site.sh, over every .html the build produced.
"""
import base64, hashlib, os, re, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "site"
POLICY = ("default-src 'self'; script-src 'self' https://gc.zgo.at{hashes}; "
          "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
          "img-src https: data:; connect-src 'self' https://museaal.goatcounter.com; "
          "base-uri 'none'; form-action 'none'; object-src 'none'; upgrade-insecure-requests")
INLINE = re.compile(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", re.S)

def policy_for(html):
    hashes = []
    for attrs, body in INLINE.findall(html):
        if "application/ld+json" in attrs: continue            # data, never executed
        h = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode()
        if h not in hashes: hashes.append(h)
    return POLICY.format(hashes="".join(f" 'sha256-{h}'" for h in hashes))

n = 0
for d, _, files in os.walk(ROOT):
    for f in files:
        if not f.endswith(".html"): continue
        p = os.path.join(d, f)
        html = open(p, encoding="utf-8").read()
        if 'http-equiv="Content-Security-Policy"' in html: continue
        tag = f'<meta http-equiv="Content-Security-Policy" content="{policy_for(html)}">'
        html2, k = re.subn(r'(<meta charset="utf-8">)', r"\1" + tag.replace("\\", "\\\\"), html, count=1)
        if not k: print("  no charset tag, policy not written:", p); continue
        open(p, "w", encoding="utf-8").write(html2); n += 1
print(f"CSP: policy written into {n:,} pages")
