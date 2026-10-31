# -*- coding: utf-8 -*-
"""The build's mark on the inline scripts it writes itself, for csp.py.

csp.py puts a hash of each inline script into its page's Content-Security-Policy. It used to hash every script it
found, so a <script> that reached a page from scraped text through an escaping slip would have been hashed and run
like the site's own. Now the builders write their own scripts as <script data-built="MARK">, MARK a random value made for
this build (build_site.sh exports it), which no gallery, auction house or museum record can know: csp.py hashes only
marked scripts, takes the mark out of the page, and stops the build at any other script that would run.

    import script_mark as SM
    STAMP = SM.mark("<script>...</script>")       # a constant, or a template read from a file, before any data goes in
    f"{SM.OPEN}{JS}</script>"                      # an f-string
"""
import os, secrets

MARK = os.environ.get("MUSEAAL_SCRIPT_MARK") or secrets.token_hex(16)
os.environ["MUSEAAL_SCRIPT_MARK"] = MARK          # a builder run on its own: its own mark; csp.py then refuses its pages
OPEN = f'<script data-built="{MARK}">'


def mark(html):
    """every bare <script> in a template or constant of the builder's own, marked; call it before data goes in"""
    return html.replace("<script>", OPEN)
