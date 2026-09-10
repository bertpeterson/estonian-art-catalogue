#!/bin/bash
# Rebuild the self-hosted static site from data/data.json
set -e
cd "$(dirname "$0")"
python3 build_site.py
python3 - <<'PY'
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
  async function loadShard(key){
    if (SHARDS.has(key)) return SHARDS.get(key);
    const p = fetch(`data/detail/${key}.json`).then(r => r.ok ? r.json() : {}).catch(() => ({}));
    SHARDS.set(key, p);
    const v = await p; SHARDS.set(key, v); return v;
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
  ('${esc(w.d)}','${esc(detailOf(w).d)}','desc text'),
  ('${w.dm?`<div class="d-k">','${(detailOf(w)||{}).dm?`<div class="d-k">','dims guard'),
  ('${esc(w.dm)}','${esc(detailOf(w).dm)}','dims text'),
  # source-record links: the ids live in the shard, so read them through detailOf
  ('${w.mi?`<a class="permalink"','${(detailOf(w)||{}).mi?`<a class="permalink"','muis link guard'),
  ('museaalview/${esc(w.mi)}','museaalview/${esc(detailOf(w).mi)}','muis link id'),
  ('${w.oi?`<a class="permalink"','${(detailOf(w)||{}).oi?`<a class="permalink"','ekm link guard'),
  ('oid-${esc(w.oi)}','oid-${esc(detailOf(w).oi)}','ekm link id'),
  ('${w.url?`<a class="permalink"','${(detailOf(w)||{}).url?`<a class="permalink"','src link guard'),
  ('href="${esc(w.url)}"','href="${esc(detailOf(w).url)}"','src link href'),
  # the thumbnail url lives in the shard too
  ('${w.im ? `<figure','${(detailOf(w)||{}).im ? `<figure','image guard'),
  ('href="${esc(w.im)}"','href="${esc(detailOf(w).im)}"','image link'),
  ('src="${esc(w.im)}"','src="${esc(detailOf(w).im)}"','image src')]:
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
    fetch("data/index.json").then(r => r.json()),
    fetch("data/i18n.json").then(r => r.json())
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
<meta name="description" content="A catalogue of works of art held in Estonian public collections, 1577-2026, compiled from MuIS and the EKM Digital Collection.">
'''
body=h.replace('<meta charset="utf-8">\n','',1)
open('site/index.html','w',encoding='utf-8').write(head+body+"\n"+a+"\n</body>\n</html>\n")
import os
print("MISSED:",miss if miss else "none")
print("site/index.html %.0f KB"%(os.path.getsize('site/index.html')/1024))
PY

# flat exports for reuse (CSV + JSONL), written into site/data/export/
(cd data && python3 -u validate.py && python3 -u export_csv.py)
