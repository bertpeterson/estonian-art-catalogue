#!/bin/bash
# Rebuild the self-hosted static site from data/data.json
set -e
cd "$(dirname "$0")"
# i18n.json is generated, not hand-kept. build_site.py only copies it, so edits to
# i18n.py reached the repo but never the site until this ran here.
python3 -u i18n.py
python3 build_site.py
python3 - <<'PY'
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
def sub(old,new,tag):
    global a
    if old not in a: miss.append(tag)
    a=a.replace(old,new,1)
sub('(function(){\n  "use strict";','(function(){\n  "use strict";\n  const boot = (DATA, I18N) => {',"open")
sub('  function rowHTML(w, showArtist){',
'''  const SHARDS = new Map();
  const shardOf = w => w.y != null ? String(Math.floor(w.y/10)*10) : "und";
  async function loadShard(key, attempt = 0){
    if (SHARDS.has(key)) return SHARDS.get(key);
    // A retry must skip the browser cache: the failure we are retrying is often a
    // cached 404 or 5xx, and re-requesting the identical URL just returns it again.
    const url = `data/detail/${key}.json?v=__V_INDEX__` + (attempt ? `&r=${attempt}` : "");
    const p = fetch(url, attempt ? {cache: "reload"} : undefined)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(async () => {
        // Never cache a failure. The old code stored {} on error, so a single network
        // blip removed that decade's descriptions and dimensions for the rest of the
        // session — and the record then said "No description in the record", which is
        // a false claim about the museum rather than an honest one about the fetch.
        SHARDS.delete(key);
        if (attempt < 2){
          await new Promise(r => setTimeout(r, 400 * (attempt + 1)));
          return loadShard(key, attempt + 1);
        }
        return null;
      });
    SHARDS.set(key, p);
    const v = await p;
    if (v) SHARDS.set(key, v); else SHARDS.delete(key);
    return v;
  }
  function detailOf(w){
    const s = SHARDS.get(shardOf(w));
    return (s && !(s instanceof Promise) && s[w.i]) || null;
  }

  function rowHTML(w, showArtist){''',"shards")
for old,new,tag in [
  ('${w.n>1 && w.mem ?','${w.n>1 && (detailOf(w)||{}).mem ?','mem guard'),
  ('${w.mem.map(m =>','${detailOf(w).mem.map(m =>','mem map'),
  ('${w.d ?','${(detailOf(w)||{}).d ?','desc guard'),
  ('(LANG==="en"&&w.de?esc(T("mt_desc")):esc(T("estonianprose")))','(LANG==="en"&&detailOf(w).de?esc(T("mt_desc")):esc(T("estonianprose")))','desc label'),
  ('${esc(LANG==="en"&&w.de?w.de:w.d)}','${esc(LANG==="en"&&detailOf(w).de?detailOf(w).de:detailOf(w).d)}','desc text'),
  ('${w.dm?`<div class="d-k">','${(detailOf(w)||{}).dm?`<div class="d-k">','dims guard'),
  ('${esc(w.dm)}','${esc(detailOf(w).dm)}','dims text'),
  # source-record links: the ids live in the shard, so read them through detailOf
  ('${w.mi?`<a class="permalink"','${(detailOf(w)||{}).mi?`<a class="permalink"','muis link guard'),
  ('museaalview/${esc(w.mi)}','museaalview/${esc(detailOf(w).mi)}','muis link id'),
  ('${w.oi?`<a class="permalink"','${(detailOf(w)||{}).oi?`<a class="permalink"','ekm link guard'),
  ('oid-${esc(w.oi)}','oid-${esc(detailOf(w).oi)}','ekm link id')]:
    sub(old,new,tag)
sub('''    const b = e.target.closest(".row-btn"); if (!b) return;
    const id = b.dataset.id;
    state.open = state.open === id ? null : id;
    render(); pushHash();''',
'''    const b = e.target.closest(".row-btn"); if (!b) return;
    const id = b.dataset.id;
    if (state.open === id){ state.open = null; render(); pushHash(); return; }
    state.open = id;
    const w = W.find(x => x.k === id);
    if (w && w.h && !detailOf(w)) loadShard(shardOf(w)).then(() => { if (state.open === id) render(); });
    render(); pushHash();''',"open handler")
sub('    if (scroll && state.open){',
'''    if (state.open){
      const w0 = W.find(x => x.k === state.open);
      if (w0 && w0.h && !detailOf(w0)) loadShard(shardOf(w0)).then(() => render());
    }
    if (scroll && state.open){''',"deep link")
sub('''  }


})();''','''  }
  }   // end boot

  Promise.all([
    fetch("data/index.json?v=__V_INDEX__").then(r => r.json()),
    fetch("data/i18n.json?v=__V_I18N__").then(r => r.json())
  ]).then(([data, i18n]) => boot(data, i18n))
   .catch(err => {
     document.getElementById("register").innerHTML =
       `<p class="empty">Could not load the catalogue data.<br><small>${String(err)}</small></p>`;
   });
})();''',"boot")
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
for _id, _val in (('stat-w', _meta['works']), ('stat-a', _meta['artists']), ('stat-m', _meta['museums'] if 'museums' in _meta else len({w['mu'] for w in _m['works'] if w.get('kind', 'held') == 'held'})),
                  ('stat-g', len(_holders)), ('stat-s', _gal)):
    h = h.replace(f'<b id="{_id}">0</b>', f'<b id="{_id}">{_val:,}</b>', 1)
h = h.replace('<div id="stat-gwrap" hidden>', '<div id="stat-gwrap">', 1).replace('id="stat-sale" hidden>', 'id="stat-sale">', 1)
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
body=h.replace('<meta charset="utf-8">\n','',1)
body=re.sub(r'<meta name="description"[^>]*>\n?','',body,count=1)   # the template's static copy
open('site/index.html','w',encoding='utf-8').write(head+body+"\n"+a+"\n</body>\n</html>\n")
import os
print("MISSED:",miss if miss else "none")
print("site/index.html %.0f KB"%(os.path.getsize('site/index.html')/1024))
PY

# flat exports for reuse (CSV + JSONL), written into site/data/export/
(cd data && python3 -u validate.py && python3 -u export_csv.py)

# crawlable artist pages + sitemap (the app itself is a fragment-addressed SPA)
python3 -u build_pages.py
