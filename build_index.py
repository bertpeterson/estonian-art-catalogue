# -*- coding: utf-8 -*-
"""Assemble site/index.html: the head from tpl_head.html (its empty labels filled in
English, the masthead figures and the description from the data, the preload and the
shared-link picture), the baked landing page from site/landing.json, and the app from
tpl_app.html with its data files' versions filled in. Run by build_site.sh after
build_site.py and build_landing.py. It used to live inline in build_site.sh, where it
also patched the app's shard loader and boot sequence into the template by text
substitution; those are in tpl_app.html itself now."""
import hashlib
def _v(p):
    # GitHub Pages serves data/*.json with cache-control: max-age=600, so for ten
    # minutes after a deploy a returning browser keeps the old copy -- which is how
    # a fixed i18n.json still rendered "th_auto" on the live site. Versioning each
    # URL by its own content means a changed file is a different URL and is fetched
    # immediately, while an unchanged one stays cached.
    return hashlib.sha1(open(p,'rb').read()).hexdigest()[:8]
V_INDEX, V_I18N = _v('site/data/index.json'), _v('site/data/i18n.json')
import json, re
_m = json.load(open('data/data.json',encoding='utf-8'))
_meta, _ys = _m['meta'], [w['y'] for w in _m['works'] if w.get('y')]
# Two descriptions shipped before -- one here, one in the template -- and the template's
# quoted "52,000 artworks by 3,600 artists" from whenever it was last typed. One, from the data.
DESC = ('<meta name="description" content="A catalogue of %s works of art by %s artists in Estonian public '
        'collections and galleries, %d\u2013%d. Museum records from MuIS and the EKM Digital Collection, gallery '
        'stock from the galleries\' own catalogues; every record links back to its source.">'
        % (f"{_meta['works']:,}", f"{_meta['artists']:,}", min(_ys), max(_ys)))
h=open('tpl_head.html',encoding='utf-8').read()
a=open('tpl_app.html',encoding='utf-8').read()
miss=[]
head='''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
''' + DESC + '''
'''
# The masthead figures are in the HTML from the first paint. They were "0" placeholders
# the app filled once the 11 MB index had loaded, so a reload showed 0 · 0 · 0 for a
# moment; the app still overwrites them, but with the same numbers.
_gal = sum(1 for w in _m['works'] if w.get('kind') == 'gallery')
_holders = {w['mu'] for w in _m['works'] if w.get('kind') == 'gallery'}
_auc = sum(1 for w in _m['works'] if w.get('kind') == 'auction')
for _id, _val in (('stat-w', _meta['works']), ('stat-a', _meta['artists']), ('stat-m', _meta['museums'] if 'museums' in _meta else len({w['mu'] for w in _m['works'] if w.get('kind', 'held') == 'held'})),
                  ('stat-g', len(_holders)), ('stat-s', _gal), ('stat-au', _auc)):
    h = h.replace(f'<b id="{_id}">0</b>', f'<b id="{_id}">{_val:,}</b>', 1)
h = h.replace('id="stat-sale" hidden>', 'id="stat-sale">', 1).replace('id="stat-auc" hidden>', 'id="stat-auc">', 1)
# Every label the HTML leaves empty for the app to fill is filled at build time with
# its English text, from the same dictionary. The first paint then reads as a page,
# not a skeleton; the app re-applies the visitor's language on load as before. The
# subtitle's year placeholders are the real years. The "(hidden after load)" attributes
# that kept the empty header from showing are dropped for the same reason.
import re as _re
_I = json.load(open('i18n.json', encoding='utf-8'))
def _fill(m):
    tag, attrs, key = m.group(1), m.group(2), m.group(3)
    txt = _I['EN'].get(key, '')
    if key == 'sub': txt = _re.sub(r'\d{4}\s*[–-]\s*\d{4}', f'{min(_ys)}–{max(_ys)}', txt)
    return f'<{tag}{attrs}data-i18n="{key}"{m.group(4)}>{txt}</{tag}>'
h = _re.sub(r'<(\w+)([^>]*?)data-i18n="([a-z_0-9]+)"([^>]*)></\1>', _fill, h)
def _fillh(m):
    tag, attrs, key = m.group(1), m.group(2), m.group(3)
    return f'<{tag}{attrs}data-i18n-html="{key}"{m.group(4)}>{_I["HTML_EN"].get(key, "")}</{tag}>'
h = _re.sub(r'<(\w+)([^>]*?)data-i18n-html="([a-z_0-9]+)"([^>]*)></\1>', _fillh, h)
a=a.replace('__V_INDEX__',V_INDEX).replace('__V_I18N__',V_I18N)
# the index's download starts as the head is parsed, not when the script at the foot
# of the page runs; crossorigin matches fetch()'s default mode, so the one download
# serves both. Not low priority any more: the wall's pictures past the first row wait
# until they near the screen (window.__lz), so the first row and the index share the
# connection instead of forty pictures taking it
h=h.replace('<meta property="og:type"', f'<link rel="preload" href="data/index.json?v={V_INDEX}" as="fetch" crossorigin>\n<meta property="og:type"',1)
body=h.replace('<meta charset="utf-8">\n','',1)
body=re.sub(r'<meta name="description"[^>]*>\n?','',body,count=1)   # the template's static copy
# the shared-link card: the same description, and the first of the chosen works as its
# picture -- the holder's own file, by reference, as on the wall
body=re.sub(r'<meta property="og:description" content="[^"]*">', DESC.replace('name="description"','property="og:description"'), body, count=1)
_top=min((w for w in _m['works'] if w.get('mp') is not None and w.get('im')), key=lambda w: w['mp'], default=None)
if _top:
    _im=_top['im']
    _src=(f"https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id={_im[2:]}" if _im.startswith("m:")
          else "https://digikogu.ekm.ee/static/preview/image/"+re.sub(r"/([^/]+)$", r"/t2_\1", _im[2:]) if _im.startswith("e:") else _im[2:])
    _alt=(_top.get('t') or '')+', '+_m['artists'][_top['a']]['n']
    body=body.replace('<meta name="twitter:card" content="summary">',
        f'<meta property="og:image" content="{_src}">\n<meta property="og:image:alt" content="{_alt.replace(chr(34), "&quot;")}">\n<meta name="twitter:card" content="summary_large_image">',1)
    print("og:image:", _alt)
# the landing page's first paint, baked (build_landing.py): the door and the opening of
# the artwall as plain HTML, cleared at once by an inline script when the address names
# another view, and replaced by the app when it boots
import json as _json, os as _os
if _os.path.exists('site/landing.json'):
    _L=_json.load(open('site/landing.json',encoding='utf-8'))
    body=body.replace('<section class="doors" id="doors" hidden></section>','<section class="doors" id="doors">'+_L['doors']+'</section>',1)
    body=body.replace('<main id="register"></main>','<main id="register">'+_L['register']+'</main>\n<script>if(location.hash&&!/^#(lang=\\w+|theme=\\w+)(&|$)/.test(location.hash)){document.getElementById("register").innerHTML="";document.getElementById("doors").hidden=true}</script>',1)
open('site/index.html','w',encoding='utf-8').write(head+body+"\n"+a+"\n</body>\n</html>\n")
import os
print("MISSED:",miss if miss else "none")
print("site/index.html %.0f KB"%(os.path.getsize('site/index.html')/1024))