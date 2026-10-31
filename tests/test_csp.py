# -*- coding: utf-8 -*-
"""csp.py hashes only the inline scripts the build marked as its own (script_mark.py), takes the mark out of the
page, never hashes a JSON data block, and stops the build at any other inline script: a <script> that reached a page
from scraped text is not let in by the policy written for that page.

    python3 -m unittest discover tests
"""
import base64, hashlib, os, re, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MARK = "0123456789abcdef0123456789abcdef"
h = lambda body: "'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"


def run(pages):
    """csp.py over a site of these pages: (exit code, output, {page: html after})"""
    d = tempfile.mkdtemp()
    try:
        for name, html in pages.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f: f.write(html)
        env = {**os.environ, "MUSEAAL_SCRIPT_MARK": MARK}
        r = subprocess.run([sys.executable, "-B", "csp.py", d], cwd=ROOT, env=env, capture_output=True, text=True)
        after = {}
        for n in pages:
            with open(os.path.join(d, n), encoding="utf-8") as f: after[n] = f.read()
        return r.returncode, r.stdout + r.stderr, after
    finally:
        shutil.rmtree(d)


def page(body):
    return f'<!doctype html><html><head><meta charset="utf-8"></head><body>{body}</body></html>'


class Csp(unittest.TestCase):
    def test_own_scripts_hashed_and_unmarked(self):
        code, out, after = run({"a.html": page(f'<script data-built="{MARK}">go()</script>'
                                               '<script type="application/json" id="t">{"x":1}</script>'
                                               '<script type="application/ld+json">{"@type":"Person"}</script>')})
        self.assertEqual(code, 0, out)
        html = after["a.html"]
        policy = re.search(r'content="([^"]*)"', html).group(1)
        self.assertIn(h("go()"), policy)
        self.assertNotIn(h('{"x":1}'), policy)                  # data blocks never run, so never hashed
        self.assertNotIn("data-built", html)                     # the mark does not ship
        self.assertIn("<script>go()</script>", html)

    def test_a_script_the_build_did_not_write_stops_it(self):
        code, out, after = run({"ok.html": page(f'<script data-built="{MARK}">go()</script>'),
                                "bad.html": page('<p>Maastik"><script>alert(document.domain)</script></p>')})
        self.assertNotEqual(code, 0)
        self.assertIn("bad.html", out)
        self.assertNotIn(h("alert(document.domain)"), after["bad.html"])
        self.assertNotIn("Content-Security-Policy", after["bad.html"])

    def test_a_guessed_or_old_mark_is_not_enough(self):
        code, out, _ = run({"x.html": page('<script data-built="ffffffffffffffffffffffffffffffff">alert(1)</script>')})
        self.assertNotEqual(code, 0)

    def test_no_mark_no_build(self):
        env = {k: v for k, v in os.environ.items() if k != "MUSEAAL_SCRIPT_MARK"}
        r = subprocess.run([sys.executable, "-B", "csp.py", tempfile.gettempdir() + "/none"], cwd=ROOT, env=env,
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
