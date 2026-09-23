# -*- coding: utf-8 -*-
"""Embeds: a small strip of an artist, a decade or a subject for other people's pages.

    <iframe src="https://museaal.ee/embed/konrad-magi.html" width="100%" height="230" loading="lazy"></iframe>
    <p><a href="https://museaal.ee/a/konrad-magi.html">Konrad Mägi at museaal.ee</a></p>

One page per artist (every artist; with pictures where the catalogue may show them,
the count and the media otherwise), per decade and per subject, in English at
/embed/<slug>.html and in Estonian at /embed/et/<slug>.html. Each is the catalogue's
face on someone else's site, so it shows only what a stranger should quote: pictures
from the holders' own servers (the same rule as the wall), the count, a link back.
No prices, no auction line, no header, no search. Links open in the host page
(target=_top). The embed follows the host's light or dark scheme. Not indexed -- the
artist page is; the embed code we hand out carries a plain link to it, which is the
link that counts.
"""
import os, re, html, json, collections
import build_hubs as H

BASE, A, W, val, e = H.BASE, H.A, H.W, H.val, H.e
GC = H.GC
CSS = ("html,body{margin:0;background:transparent}body{font:13px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#111;padding:10px 12px}"
       "@media(prefers-color-scheme:dark){body{color:#f1f2f4}.wt{background:#15171a}.wt span{color:#8b9098}.wt span i{color:#f1f2f4}.h{color:#8b9098}a.more{color:#9ec5ff}}"
       ".h{display:flex;justify-content:space-between;align-items:baseline;gap:12px;color:#666;font-size:.82rem;margin:0 0 8px}.h b{color:inherit;font-weight:600;font-size:1rem}"
       ".wall{display:grid;grid-template-columns:repeat(6,1fr);gap:6px}@media(max-width:520px){.wall{grid-template-columns:repeat(3,1fr)}}"
       ".wt{display:block;background:#f1f2f4;text-decoration:none;color:inherit;overflow:hidden}.wt img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover}"
       ".wt span{display:block;font-size:.66rem;line-height:1.25;padding:4px 5px 5px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.wt span i{font-style:italic;color:#111}"
       "a.more{color:#1a4fa3;text-decoration:none;white-space:nowrap}a.more:hover{text-decoration:underline}p.t{margin:6px 0 0;color:#666;font-size:.8rem}")
T = {"en": dict(works="works in Estonian collections", more="See all at museaal.ee →", dir="embed", art="a", hash="", pics="pictures from the holders' own servers"),
     "et": dict(works="teost Eesti kogudes", more="Kõik museaal.ee-s →", dir="embed/et", art="k", hash="lang=et&", pics="pildid hoidjate endi serveritest")}

def tiles_of(ws, n=6, mixed=True):
    pics = [w for w in ws if w.get("im")]
    pics.sort(key=lambda w: (w.get("mp") or 10**6, w.get("hl", 10**6), H.MRANK.get(val(w, "e"), 8), w.get("y") is None, w.get("y") or 0))
    seen, out, per = set(), [], collections.Counter()
    for w in pics:
        k = (w["a"], (w.get("t") or "").lower().strip(" ."))
        if k in seen or (mixed and per[w["a"]] >= 3): continue      # on a mixed strip, three per artist at most
        seen.add(k); per[w["a"]] += 1; out.append(w)
        if len(out) == n: break
    return out

def embed(lang, path, h1, sub, ws, link, app_hash, show_artist):
    t = T[lang]; tiles = tiles_of(ws, mixed=show_artist)
    wall = ('<div class="wall">' + "".join(
        f'<a class="wt" href="{BASE}/#{t["hash"]}artist={H.ARTIST_SLUG[w["a"]]}&open={e(H.key(w))}" target="_top" title="{e(w.get("t"))} · {e(A[w["a"]]["n"])}">'
        f'<img src="{e(H.imsrc(w["im"]))}" alt="{e(w.get("t"))}, {e(A[w["a"]]["n"])}" loading="lazy"{H.crop(w["im"])} referrerpolicy="no-referrer-when-downgrade">'
        f'<span><i>{e(w.get("t"))}</i>{(" · " + e(A[w["a"]]["n"])) if show_artist else ""}{(" · " + str(w["y"])) if w.get("y") else ""}</span></a>' for w in tiles) + "</div>") if tiles else ""
    media = H.media_phrase(ws, lang)
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(h1)} · museaal.ee</title><meta name="robots" content="noindex"><link rel="canonical" href="{link}">'
            f'<style>{CSS}</style>{GC}</head><body>'
            f'<div class="h"><span><b>{e(h1)}</b> · {e(sub)}</span><a class="more" href="{link}" target="_top">{t["more"]}</a></div>'
            + wall + (f'<p class="t">{e(media)}</p>' if not tiles and media else "") + "</body></html>")

def main():
    for lang in ("en", "et"):
        t = T[lang]
        for sub in ("", "decades", "subjects") if lang == "en" else ("", "kumnendid", "ained"):
            os.makedirs(f"site/{t['dir']}/{sub}".rstrip("/"), exist_ok=True)
    by_artist = collections.defaultdict(list)
    for w in W: by_artist[w["a"]].append(w)
    n = 0
    for lang in ("en", "et"):
        t = T[lang]
        for i, ws in by_artist.items():
            if not ws: continue
            a = A[i]; sl = H.ARTIST_SLUG[i]
            life = a.get("l") or ["", ""]
            dates = f"{life[0]}–{life[1]}" if life[0] or life[1] else ""
            nw = sum(1 for w in ws if not (w.get("ac") and not w.get("al")))
            sub = f"{dates + ' · ' if dates else ''}{H.fmt(nw, lang)} {t['works']}"
            open(f"site/{t['dir']}/{sl}.html", "w", encoding="utf-8").write(
                embed(lang, sl, a["n"], sub, ws, f"{BASE}/{t['art']}/{sl}.html", f"artist={sl}", False)); n += 1
        for dd in H.DECS:
            ws = H.by_dec[dd]; lab = H.dec_label(dd, lang)
            h1 = (f"Estonian art of the {dd}s" if lang == "en" else f"Eesti kunst {dd}ndatel") if dd != "before" else (f"Estonian art {lab}" if lang == "en" else f"Eesti kunst {lab}")
            d = "decades" if lang == "en" else "kumnendid"
            open(f"site/{t['dir']}/{d}/{dd}.html", "w", encoding="utf-8").write(
                embed(lang, f"{d}/{dd}", h1, f"{H.fmt(len(ws), lang)} {t['works']}", ws, H.dec_href(dd, lang), "", True)); n += 1
        for s in H.SUBS:
            ws = H.by_sub[s[0]]; lab = s[2] if lang == "en" else s[3]
            d = "subjects" if lang == "en" else "ained"
            open(f"site/{t['dir']}/{d}/{s[0] if lang == 'en' else s[1]}.html", "w", encoding="utf-8").write(
                embed(lang, f"{d}/{s[0]}", lab, f"{H.fmt(len(ws), lang)} {t['works']}", ws, H.sub_href(s, lang), "", True)); n += 1
    print(f"  embeds         {n:,} (artists, decades, subjects; both languages)")

if __name__ == "__main__":
    main()
