# -*- coding: utf-8 -*-
"""Art by mood: /mood.html and /meeleolu.html, and the data they read, /data/mood.json.

A visitor picks up to three words -- solemn, misty, tender -- or describes a feeling in a
few words, and sees the museum works whose pictures answer to them best. The scores come
from data/moods.py (a CLIP image model on the Mac: each picture against each word; run
it after lookalikes.py); this only lays them out. The page asks for the data when it
opens, so the catalogue's own first load is untouched.

A typed feeling is matched to the vocabulary by word stems in both languages (STEMS
below: "üksildane sügisõhtu" is lonely and autumnal) -- no model runs in the browser.

The tiles are the site's own: the holder's picture (a lighter copy where data/thumbs.py
has one), the shape the photograph has without its colour chart, the chart's side
cropped away, and a link to the record in the catalogue.
Run after build_stats.py (it adds to the sitemap) and before csp.py.
"""
import json, os, re, hashlib, datetime
import build_hubs as H
import sys; sys.path.insert(0, "data")
from shape_of import shape_of

BASE, A, W, e = H.BASE, H.A, H.W, H.e
V = json.load(open("data/data.json", encoding="utf-8"))["vocab"]

# a typed word counts for a mood when one of these begins it (lower case; Estonian
# stems short enough to take the endings: "üksild" is üksildane, üksildase, üksildust)
STEMS = {
 "solemn": "solemn grave dignif sacred holy reveren church funeral mourn requiem pühalik püha tõsine väärik kirik matus lein",
 "serene": "seren calm peace tranquil relax restful unhurr rahu tasane lõõgast puhka",
 "contemplative": "contempla thought pensive reflect think medita wonder ponder mõtlik mõtiskl mõtte mõtle medite süvene",
 "melancholy": "melanchol sad sadn sorrow wistful grief unhapp tears weep depress mourn melanhool kurb kurva nukker masend nutt",
 "lonely": "lonel alone solitar isolat empty abandon forsak üksik üksild üksi tühi mahajäe",
 "nostalgic": "nostalg memor rememb childhood longing yearn bygone nostalg mälest mäleta lapsepõl igatse möödun",
 "tender": "tender gentle affection caring mother mothe baby child tenderness õrn hell lembe hool ema laps",
 "intimate": "intima private cosy cozy homely domestic interior intiim lähedu kodu hubane privaat tuba",
 "joyful": "joy joyf happy happi cheer glad delight smil laugh bliss rõõm õnnel lõbus naer",
 "playful": "playful whimsic silly funny humor humour fun game mischie mängul nali nalja vallatu humoor",
 "festive": "festiv celebrat party holiday feast christmas carnival pidu pidul pühad jõul tähist karneval",
 "romantic": "romant love lovers passion kiss couple wedding romant armastu armu kirg suudl pulm",
 "dreamy": "dream surreal fantas fairy magic sleep visionar unenäo unista une fantaas muinas maagil sürreal",
 "mysterious": "myster enigma secret strange hidden unknown occult salapär müstil saladus kummali varjatud",
 "eerie": "eerie uncann creepy spooky ghost haunt scary horror sinister kõhe jube õudne kummitus õud",
 "anxious": "anxi tense nervous uneas worr stress restless fear afraid panic ärev närvi mure pinge rahutu hirm",
 "gloomy": "gloom bleak grim brood dismal somber sombre dreary murky sünge trööst morn kõle",
 "dramatic": "dramat drama intens action battle struggl turbul dramaat draama lahing võitlus tormil",
 "heroic": "hero epic myth legend brave courag warrior kangel eepil müüt legend vapper julge sõdal kalevi",
 "bright": "bright luminous radian shining shine light airy hele särav kiirgav helge valgus",
 "dark": "dark shadow black dim murk tume pime vari must",
 "sunny": "sun sunny sunshine sunlit hot päike palav",
 "golden": "golden gold amber glow honey kuld kuldne kuma mesi",
 "twilight": "twilight dusk evening sunset dawn gloaming hämar videvik õhtu loojang koit",
 "moonlit": "moon night nocturn star midnight kuu öö öine tähe kesköö",
 "misty": "mist fog haze hazy vapour vapor smoke udu udune hägu aur",
 "vivid": "vivid colourful colorful bold vibrant saturat loud intense erk värvik kirev ere",
 "muted": "muted pastel subtle pale faded soft mahe pastell tuhm kahvatu pehme",
 "warm": "warm red orange fire cosy soe sooja punane oranž tuli",
 "cold": "cold cool icy blue frost chill freez külm jahe sinine jää pakane",
 "stormy": "storm wind wave tempest rough thunder rain gale torm tuul laine äike vihm",
 "still": "still quiet silent silence motionless hush calm vaikne vaikus liikumatu tasa",
 "wintry": "winter wintr snow ice frozen talv lumi lume külmunud",
 "spring": "spring blossom bloom april fresh kevad õitse õied värske",
 "summery": "summer meadow beach swim july heat suvi suve heinamaa rand",
 "autumnal": "autumn fall leaves harvest october november sügis lehed lõikus",
}

T = {"en": dict(file="mood.html", other="meeleolu.html", other_l="Eesti keeles", site="Estonian Art Catalogue",
                h="Art by mood", lede="Pick up to three words, or describe a feeling. The wall shows the museum works whose pictures answer to it best. An image model has looked at every picture itself, not at the records, so it finds a mood the way you would: by looking.",
                describe="Describe a feeling", ph="a quiet, misty morning", find="Find",
                groups=dict(feeling="Feeling", light="Light", colour="Colour", weather="Season and weather"),
                kinds=dict(paint="Paintings", paper="Works on paper", all="All art"),
                surprise="Surprise me", clear="Clear", more="Show more", none="Pick a word to begin.",
                nomatch="No mood word in that. Try one of the words below.", of="of", works="works", loading="Loading the pictures…",
                note="The moods are read by CLIP, an image model, from the museums' own photographs of public-domain works: a guide to looking, not a judgement of the work. Each picture opens its record in the catalogue.",
                hash=""),
     "et": dict(file="meeleolu.html", other="mood.html", other_l="In English", site="Eesti Kunstikataloog",
                h="Kunst meeleolu järgi", lede="Vali kuni kolm sõna või kirjelda tunnet. Seinal on muuseumiteosed, mille pilt sellele kõige paremini vastab. Pildimudel on iga pilti ise vaadanud, mitte kirjet, nii et ta leiab meeleolu nagu sinagi: vaadates.",
                describe="Kirjelda tunnet", ph="vaikne udune hommik", find="Otsi",
                groups=dict(feeling="Tunne", light="Valgus", colour="Värv", weather="Aastaaeg ja ilm"),
                kinds=dict(paint="Maalid", paper="Tööd paberil", all="Kõik"),
                surprise="Üllata mind", clear="Tühjenda", more="Näita rohkem", none="Alusta sõna valimisega.",
                nomatch="Selles ei olnud ühtki meeleolusõna. Proovi mõnda allolevat.", of="/", works="teost", loading="Pildid laadivad…",
                note="Meeleolu loeb pildimudel CLIP muuseumide endi fotodelt vabakasutuses teostest: see on juhatus vaatamiseks, mitte hinnang teosele. Iga pilt avab teose kirje kataloogis.",
                hash="lang=et&")}

def data():
    M = json.load(open("data/moods.json", encoding="utf-8"))
    by_key = {H.key(w): w for w in W if w.get("im")}
    aidx, arts = {}, []
    works, wi = [], {}
    def ref(k):
        if k in wi: return wi[k]
        w = by_key.get(k)
        if not w: return None
        im = H.SMALL.get(w["im"], w["im"])
        if im.startswith("g:"):
            u = re.sub(r"^http:", "https:", im[2:])
            if not re.match(r"https://", u): return None
            im = "g:" + u
        # the tile's shape: the photograph's without its chart, else the record's dimensions
        rp, rw, ch = w.get("ir"), shape_of(w.get("dm")), H.CHARTS.get(w["im"])
        r = rp or rw or 1
        if ch and rp: r = rp / (1 - ch[1]) if ch[0] in "lr" else rp * (1 - ch[1])
        a = w["a"]
        if a not in aidx: aidx[a] = len(arts); arts.append([A[a]["n"], H.ARTIST_SLUG[a]])
        mu = V["mu"][w["mu"]] if isinstance(w.get("mu"), int) else (w.get("mu") or "")
        wi[k] = len(works)
        works.append([w.get("t") or "", aidx[a], w.get("y") or "", im, round(min(2.2, max(0.45, r)) * 100), ch[0] if ch else "", k, mu])
        return wi[k]
    lists = {}
    for kind in ("paint", "paper", "all"):
        lists[kind] = {}
        for word, lst in M[kind].items():
            lists[kind][word] = [[i, z] for i, z in ((ref(k), z) for k, z in lst) if i is not None]
    mus = sorted({x[7] for x in works})
    for x in works: x[7] = mus.index(x[7])
    stems = {w: s.split() for w, s in STEMS.items()}
    return {"words": M["words"], "lists": lists, "works": works, "artists": arts,
            "mu": mus, "mu_en": [H.MUSEUM_EN.get(m, m) for m in mus], "stems": stems}

CSS = """
:root{--paper:#0B0C0E;--raise:#111316;--field:#15171A;--ink:#F1F2F4;--ink-soft:#C7CACE;--grey:#8B9098;--rule:#2B2E34;--on:#F1F2F4;--on-ink:#0B0C0E;
  --serif:"Newsreader","Iowan Old Style",Georgia,serif;--sans:"Archivo","Helvetica Neue",Arial,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;color-scheme:dark}
:root[data-theme=light]{--paper:#FFFFFF;--raise:#FAFAFB;--field:#F1F2F4;--ink:#0B0C0E;--ink-soft:#33363B;--grey:#6C7178;--rule:#DCDFE3;--on:#0B0C0E;--on-ink:#FFFFFF;color-scheme:light}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{max-width:1240px;margin:0 auto;padding-inline:28px;padding-block:22px 60px;display:grid;gap:22px}
@media (max-width:640px){.wrap{padding-inline:16px}}
nav{font:500 .72rem/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--grey)}
nav a{text-decoration:none;color:var(--ink)}nav a:hover{text-decoration:underline}
header{display:grid;gap:10px;border-bottom:1px solid var(--ink);padding-bottom:20px}
h1{margin:0;font:500 clamp(2.1rem,4.6vw,3.2rem)/1 var(--serif);letter-spacing:-.015em;text-wrap:balance}
.lede{margin:0;max-width:66ch;color:var(--ink-soft);font-size:1.02rem}
form.describe{display:flex;flex-wrap:wrap;gap:8px;align-items:center;max-width:640px}
form.describe label{font:500 .68rem/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--grey);flex-basis:100%}
form.describe input{flex:1 1 260px;min-width:0;font:italic 400 1.1rem/1.2 var(--serif);color:var(--ink);background:var(--raise);border:1px solid var(--rule);padding:10px 12px}
form.describe input:focus{outline:2px solid var(--ink);outline-offset:1px}
.btn{font:500 .74rem/1 var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--ink);background:none;border:1px solid var(--rule);padding:10px 13px;cursor:pointer}
.btn:hover{border-color:var(--grey)}.btn.solid{background:var(--on);color:var(--on-ink);border-color:var(--on)}
.msg{flex-basis:100%;margin:0;font-size:.85rem;color:var(--grey)}
.groups{display:grid;gap:12px}
.group{display:grid;grid-template-columns:150px 1fr;gap:10px;align-items:start}
@media (max-width:700px){.group{grid-template-columns:1fr;gap:6px}}
.gname{font:500 .68rem/2.5 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{font:italic 400 1.02rem/1 var(--serif);color:var(--ink);background:var(--raise);border:1px solid var(--rule);padding:8px 13px 9px;border-radius:999px;cursor:pointer}
.chip:hover{border-color:var(--grey)}.chip[aria-pressed=true]{background:var(--on);color:var(--on-ink);border-color:var(--on)}
.bar{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;border-top:1px solid var(--rule);padding-top:14px}
.seg{display:flex}.seg .btn+.btn{border-left:0}.seg .btn[aria-pressed=true]{background:var(--on);color:var(--on-ink);border-color:var(--on)}
.status{font:500 .78rem/1.4 var(--mono);color:var(--grey);letter-spacing:.03em;font-variant-numeric:tabular-nums}
.status b{color:var(--ink);font-weight:500}
.wall{display:flex;gap:14px;align-items:flex-start}.col{flex:1 1 0;min-width:0;display:grid;gap:18px}
.t{display:block;text-decoration:none}
.t img{display:block;width:100%;height:auto;object-fit:cover;background:var(--field)}
.t span{display:block;padding-top:6px;font-size:.76rem;line-height:1.3;color:var(--grey)}
.t span i{display:block;font:italic 400 .98rem/1.2 var(--serif);color:var(--ink)}
.t:hover span i{text-decoration:underline}
.more{justify-self:center}
footer{border-top:1px solid var(--rule);padding-top:14px;font-size:.82rem;color:var(--grey);max-width:78ch}
footer a{color:var(--ink)}
:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
"""

JS = r"""
(() => {
const L = document.documentElement.lang === "et" ? "et" : "en", T = JSON.parse(document.getElementById("t").textContent);
const $ = id => document.getElementById(id);
let D = null, sel = [], kind = "paint", shown = 48, lastCols = 0;
const src = im => im.startsWith("m:") ? "https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id=" + encodeURIComponent(im.slice(2))
  : im.startsWith("e:") ? "https://digikogu.ekm.ee/static/preview/image/" + im.slice(2).replace(/\/([^\/]+)$/, "/t2_$1") : im.slice(2);
const POS = {l: "100% 50%", r: "0% 50%", t: "50% 100%", b: "50% 0%"};
const word = en => D.words.find(w => w.en === en);
function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  sel = (p.get("w") || "").split(",").filter(w => D.words.some(x => x.en === w)).slice(0, 3);
  kind = ["paint", "paper", "all"].includes(p.get("k")) ? p.get("k") : "paint";
}
function writeHash() {
  const p = new URLSearchParams();
  if (sel.length) p.set("w", sel.join(","));
  if (kind !== "paint") p.set("k", kind);
  const h = p.toString().replace(/%2C/g, ",");
  try { history.replaceState(null, "", location.pathname + (h ? "#" + h : "")); } catch (e) {}
}
function chips() {
  const g = $("groups"); g.textContent = "";
  for (const key of Object.keys(T.groups)) {
    const row = document.createElement("div"); row.className = "group";
    const n = document.createElement("div"); n.className = "gname"; n.textContent = T.groups[key];
    const c = document.createElement("div"); c.className = "chips";
    for (const w of D.words.filter(w => w.g === key)) {
      const b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.textContent = w[L];
      b.setAttribute("aria-pressed", sel.includes(w.en));
      b.onclick = () => { sel = sel.includes(w.en) ? sel.filter(x => x !== w.en) : [...sel, w.en].slice(-3); update(); };
      c.append(b);
    }
    row.append(n, c); g.append(row);
  }
  document.querySelectorAll("[data-k]").forEach(b => b.setAttribute("aria-pressed", b.dataset.k === kind));
}
function ranked() {
  const lists = sel.map(w => D.lists[kind][w] || []);
  const maps = lists.map(l => new Map(l)), floors = lists.map(l => l.length ? l[l.length - 1][1] - 0.5 : 0);
  const score = new Map();
  lists.forEach(l => l.forEach(([i]) => score.set(i, 0)));
  for (const i of score.keys()) score.set(i, maps.reduce((s, m, j) => s + (m.has(i) ? m.get(i) : floors[j]), 0));
  return [...score.entries()].sort((a, b) => b[1] - a[1]).map(x => x[0]);
}
function wall() {
  const el = $("wall"), st = $("status"); el.textContent = "";
  if (!sel.length) { st.textContent = T.none; $("more").hidden = true; return; }
  const all = ranked(), top = all.slice(0, shown);
  st.textContent = "";
  const b = document.createElement("b"); b.textContent = sel.map(w => word(w)[L]).join(" + ");
  st.append(b, ` · ${T.kinds[kind]} · ${top.length} ${T.of} ${all.length} ${T.works}`);
  // shortest column first, so the best matches run along the top, as on the site's wall
  const n = Math.max(2, Math.min(6, Math.floor(el.clientWidth / 200))), cols = [], hs = [];
  for (let j = 0; j < n; j++) { const c = document.createElement("div"); c.className = "col"; cols.push(c); hs.push(0); el.append(c); }
  lastCols = n;
  for (const i of top) {
    const [t, ai, y, im, r, rs, k, mu] = D.works[i], [an, as] = D.artists[ai];
    const a = document.createElement("a"); a.className = "t";
    a.href = "./#" + T.hash + "artist=" + as + "&open=" + encodeURIComponent(k);
    a.title = `${t} · ${an}${y ? ", " + y : ""} · ${(L === "en" ? D.mu_en : D.mu)[mu]}`;
    const img = document.createElement("img"); img.loading = "lazy"; img.decoding = "async"; img.alt = `${t}, ${an}`;
    img.referrerPolicy = "no-referrer-when-downgrade"; img.src = src(im);
    img.style.aspectRatio = `1 / ${(r / 100).toFixed(3)}`; if (rs) img.style.objectPosition = POS[rs];
    img.addEventListener("error", () => a.remove(), {once: true});      // a picture the holder no longer gives takes its tile with it
    const c = document.createElement("span"), ti = document.createElement("i"); ti.textContent = t;
    c.append(ti, `${an}${y ? ", " + y : ""}`);
    a.append(img, c);
    const j = hs.indexOf(Math.min(...hs)); cols[j].append(a); hs[j] += r / 100 + 0.3;
  }
  $("more").hidden = shown >= Math.min(all.length, 192);
}
function update(keepShown) { if (!keepShown) shown = 48; chips(); wall(); writeHash(); $("msg").hidden = true; }
// a typed feeling: each word that begins with one of a mood's stems counts for it
function describe(text) {
  const toks = text.toLowerCase().normalize("NFC").match(/[a-zõäöüšž]+/g) || [], hits = new Map();
  // a stem of three letters or fewer takes only a short ending: "sun" is sunny, not Sunday; "kuu" is kuul, not kuulus
  const fits = (tok, s) => s.length <= 3 ? tok.startsWith(s) && tok.length <= s.length + 2 : tok.startsWith(s);
  toks.forEach((tok, n) => { for (const [w, st] of Object.entries(D.stems)) if (st.some(s => fits(tok, s))) if (!hits.has(w)) hits.set(w, n); });
  const got = [...hits.entries()].sort((a, b) => a[1] - b[1]).map(x => x[0]).slice(0, 3);
  if (!got.length) { $("msg").textContent = T.nomatch; $("msg").hidden = false; return; }
  sel = got; update();
}
$("describe").addEventListener("submit", ev => { ev.preventDefault(); describe($("feel").value); });
document.querySelectorAll("[data-k]").forEach(b => b.onclick = () => { kind = b.dataset.k; update(); });
$("surprise").onclick = () => {
  const ws = D.words.map(w => w.en), a = ws[Math.random() * ws.length | 0];
  let b = ws[Math.random() * ws.length | 0]; sel = Math.random() < 0.6 && b !== a ? [a, b] : [a]; update();
};
$("clear").onclick = () => { sel = []; $("feel").value = ""; update(); };
$("more").onclick = () => { shown += 48; update(true); };
$("status").textContent = T.loading;
fetch($("wall").dataset.src).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(d => {
  D = d; readHash();
  if (!sel.length && !location.hash) sel = ["serene"];          // the page opens on a wall, not an empty shell
  chips(); wall();
}).catch(err => { $("status").textContent = String(err); });
let rt = 0;
addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { if (D && sel.length && Math.max(2, Math.min(6, Math.floor($("wall").clientWidth / 200))) !== lastCols) wall(); }, 150); });
addEventListener("hashchange", () => { if (D) { readHash(); shown = 48; chips(); wall(); } });
})();
"""

def page(lang, ver):
    t = T[lang]
    me, other = f"{BASE}/{t['file']}", f"{BASE}/{t['other']}"
    tj = json.dumps({k: t[k] for k in ("groups", "kinds", "none", "nomatch", "of", "works", "loading", "hash")}, ensure_ascii=False).replace("</", "<\\/")
    kinds = "".join(f'<button type="button" class="btn" data-k="{k}" aria-pressed="{str(k == "paint").lower()}">{e(v)}</button>' for k, v in t["kinds"].items())
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(t["h"])} · museaal.ee</title><meta name="description" content="{e(t["lede"][:290])}">'
            f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
            '<link rel="preconnect" href="https://www.muis.ee"><link rel="preconnect" href="https://digikogu.ekm.ee">'
            f'<style>{CSS}</style>{H.GC}</head><body><div class="wrap">'
            f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{e(t["site"])}</a> › {e(t["h"])} · <a href="{other}" hreflang="{"et" if lang == "en" else "en"}">{e(t["other_l"])}</a></nav>'
            f'<header><h1>{e(t["h"])}</h1><p class="lede">{e(t["lede"])}</p></header>'
            f'<form class="describe" id="describe"><label for="feel">{e(t["describe"])}</label>'
            f'<input id="feel" type="text" autocomplete="off" placeholder="{e(t["ph"])}"><button class="btn solid" type="submit">{e(t["find"])}</button>'
            f'<p class="msg" id="msg" hidden></p></form>'
            f'<div class="groups" id="groups"></div>'
            f'<div class="bar"><div class="seg" role="group">{kinds}</div>'
            f'<button type="button" class="btn" id="surprise">{e(t["surprise"])}</button><button type="button" class="btn" id="clear">{e(t["clear"])}</button>'
            f'<span class="status" id="status" aria-live="polite"></span></div>'
            f'<div class="wall" id="wall" data-src="data/mood.json?v={ver}"></div>'
            f'<button type="button" class="btn more" id="more" hidden>{e(t["more"])}</button>'
            f'<footer>{e(t["note"])} {H.CONTACT[lang]}</footer></div>'
            f'<script type="application/json" id="t">{tj}</script><script>{JS}</script></body></html>')

def main():
    d = data()
    blob = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    ver = hashlib.sha1(blob.encode()).hexdigest()[:8]
    open("site/data/mood.json", "w", encoding="utf-8").write(blob)
    urls = []
    for lang in ("en", "et"):
        open(f"site/{T[lang]['file']}", "w", encoding="utf-8").write(page(lang, ver)); urls.append(f"{BASE}/{T[lang]['file']}")
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print(f"  by mood        {len(d['words'])} words, {len(d['works']):,} works; mood.json {len(blob) // 1024} KB; mood.html, meeleolu.html")

if __name__ == "__main__":
    main()
