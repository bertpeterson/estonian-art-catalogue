# -*- coding: utf-8 -*-
"""Build register.html — the single-file snapshot published as a Claude Artifact.

The artifact has a hard 16 MB ceiling and no way to fetch data at runtime, so it
cannot follow the catalogue as it grows. github.io is canonical; this file is a
dated snapshot and says so on its own masthead, in both languages, with a link to
the live site. Run it deliberately, not on every change.
"""
import json, datetime, sys

SITE = "https://bertpeterson.github.io/estonian-art-catalogue/"
head = open('tpl_head.html', encoding='utf-8').read()
app  = open('tpl_app.html',  encoding='utf-8').read()
data = json.load(open('data/data.json', encoding='utf-8'))
i18n = json.load(open('i18n.json',      encoding='utf-8'))

built = data.get("meta", {}).get("built") or datetime.date.today().isoformat()
for lang in ("EN", "ET"):
    i18n[lang]["snapshot"] = i18n[lang]["snapshot"].replace("{date}", built)

notice = (f'    <p class="snapshot"><span data-i18n="snapshot"></span> '
          f'<a href="{SITE}" target="_blank" rel="noopener">'
          f'bertpeterson.github.io/estonian-art-catalogue</a></p>\n')
anchor = '    <p class="standfirst" data-i18n-html="standfirst"></p>'
assert head.count(anchor) == 1, "masthead anchor not found"
head = head.replace(anchor, notice + anchor)

block = ("<script>\nconst DATA=" + json.dumps(data, ensure_ascii=False, separators=(',',':'))
         + ";\nconst I18N=" + json.dumps(i18n, ensure_ascii=False, separators=(',',':')) + ";\n</script>\n")
out = head + "\n" + block + app
open('register.html', 'w', encoding='utf-8').write(out)

mb = len(out.encode()) / 1048576
print(f"register.html {mb:.2f} MB   snapshot of {built}   headroom {16-mb:.2f} MB")
if mb > 15.5: print("WARNING: at the 16 MB artifact ceiling", file=sys.stderr)
