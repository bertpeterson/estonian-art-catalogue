# -*- coding: utf-8 -*-
"""Art by mood: /mood.html and /meeleolu.html, and the data they read, /data/mood.json.

A visitor picks up to three words -- solemn, misty, tender -- or describes a feeling in a
few words, and sees the museum works whose pictures answer to them best. The scores come
from data/moods.py (a CLIP image model on the Mac: each picture against each word; run
it after lookalikes.py); this only lays them out. The page asks for the data when it
opens, so the catalogue's own first load is untouched.

A typed feeling is read by Claude Haiku through a small Cloudflare Worker (worker/, whose
address is in data/mood_api.json): it answers with up to five of the vocabulary's words,
most important first, and the page ranks with them. The Worker is generated here from the
vocabulary (worker/mood-worker.js). Without it, or when it does not answer, the page
matches the typed words to the vocabulary by stems in both languages (STEMS below:
"üksildane sügisõhtu" is lonely and autumnal). No model runs in the browser.

The chips show the moods and the subjects; the MORE words (hopeful, cosy, majestic ...)
are reached by typing only.

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
 "sea": "sea seas seascape ocean coast shore meri mere rannik", "lake": "lake pond järv tiik", "river": "river stream brook jõgi oja",
 "forest": "forest wood woods mets metsa", "trees": "tree birch pine oak puu kask mänd tamm", "fields": "field meadow farmland põld niit",
 "garden": "garden park aed park", "mountains": "mountain hill alps mägi mäe mägede", "sky": "sky cloud taevas pilv",
 "village": "village farm farmhouse küla talu", "city": "city town street urban linn tänav", "harbour": "harbour harbor port dock ship sadam laev",
 "church": "church chapel cathedral kirik kabel", "interior": "interior room indoors inside interjöör tuba", "portrait": "portrait face faces portree nägu",
 "children": "child kid boy girl laps poiss tüdruk", "family": "family mother father pere ema isa", "work": "work labour labor worker harvest töö tööli",
 "music": "music musician violin song muusika viiul laul", "dance": "dance dancing dancer ballet tants balle", "horses": "horse hobu",
 "animals": "animal cow dog cat loom lehm koer kass", "birds": "bird birds lind linnu", "flowers": "flower bouquet blossom lill lille",
 "stilllife": "stilllife natüürmort vaikelu", "boats": "boat ship sail paat laev purje",
 "hopeful": "hope hopeful lootus", "cosy": "cosy cozy snug hubane", "sacred": "sacred holy religio püha religioo", "majestic": "majest grand monument majesteet suursugu",
 "fragile": "fragil delicat habras", "sensual": "sensual sensuous meeleli", "innocent": "innocen naive süütu", "energetic": "energ vigor vigour energi",
 "proud": "proud pride uhke", "elegant": "elegan grace elegant", "lively": "livel bustl elav", "empty": "empty deserted tühi",
 "spiritual": "spiritu vaimne", "idyllic": "idyll pastoral idüll", "wild": "wild untamed metsik", "harsh": "harsh severe karm",
 "angry": "anger angry furious viha", "abstract": "abstract abstrakt", "expressive": "express ekspress", "decorative": "decorat ornament dekorat",
 "simple": "simple plain minimal lihtne", "ornate": "ornate rikkali", "rustic": "rustic peasant talupoja maaläh", "modern": "modern modernis",
}

T = {"en": dict(file="mood.html", other="meeleolu.html", other_l="Eesti keeles", site="Estonian Art Catalogue",
                h="Art by mood", lede="Pick up to three words, or describe in your own words what you would like to see. The wall shows the museum works whose pictures answer to it best. An image model has looked at every picture itself, not at the records, so it finds a mood the way you would: by looking.",
                describe="Describe what you would like to see", ph="a quiet morning after bad news", find="Find",
                groups=dict(feeling="Feeling", light="Light", colour="Colour", weather="Season and weather", subject="Subject"), readas="Read as", reading="Reading…",
                kinds=dict(paint="Paintings", paper="Works on paper", all="All art"),
                surprise="Surprise me", clear="Clear", more="Show more", none="Pick a word to begin.",
                nomatch="No mood word in that. Try one of the words below.", of="of", works="works", loading="Loading the pictures…", failed="The pictures could not be loaded. Reload the page to try again.",
                note="The moods are read by CLIP, an image model, from the museums' own photographs of public-domain works: a guide to looking, not a judgement of the work. A typed description is read by Claude, which picks the words; the sentence is not stored. Each picture opens its record in the catalogue.",
                hash=""),
     "et": dict(file="meeleolu.html", other="mood.html", other_l="In English", site="Eesti Kunstikataloog",
                h="Kunst meeleolu järgi", lede="Vali kuni kolm sõna või kirjelda oma sõnadega, mida tahaksid näha. Seinal on muuseumiteosed, mille pilt sellele kõige paremini vastab. Pildimudel on iga pilti ise vaadanud, mitte kirjet, nii et ta leiab meeleolu nagu sinagi: vaadates.",
                describe="Kirjelda, mida tahaksid näha", ph="üksildane sügisõhtu mere ääres", find="Otsi",
                groups=dict(feeling="Tunne", light="Valgus", colour="Värv", weather="Aastaaeg ja ilm", subject="Aine"), readas="Loetud kui", reading="Loen…",
                kinds=dict(paint="Maalid", paper="Tööd paberil", all="Kõik"),
                surprise="Üllata mind", clear="Tühjenda", more="Näita rohkem", none="Alusta sõna valimisega.",
                nomatch="Selles ei olnud ühtki meeleolusõna. Proovi mõnda allolevat.", of="/", works="teost", loading="Pildid laadivad…", failed="Pilte ei õnnestunud laadida. Proovi lehte uuesti laadida.",
                note="Meeleolu loeb pildimudel CLIP muuseumide endi fotodelt vabakasutuses teostest: see on juhatus vaatamiseks, mitte hinnang teosele. Kirjeldust loeb Claude, kes valib sõnad; lauset ei salvestata. Iga pilt avab teose kirje kataloogis.",
                hash="lang=et&")}

LABEL_EN = {"stilllife": "still life"}

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
            lists[kind][word] = [[i, round(z, 1)] for i, z in ((ref(k), z) for k, z in lst) if i is not None]
    mus = sorted({x[7] for x in works})
    for x in works: x[7] = mus.index(x[7])
    stems = {w: s.split() for w, s in STEMS.items()}
    for w in M["words"]: w["label"] = LABEL_EN.get(w["en"], w["en"])      # the English the page shows; "en" is the word's id
    return ({"words": M["words"], "works": works, "artists": arts,
             "mu": mus, "mu_en": [H.MUSEUM_EN.get(m, m) for m in mus], "stems": stems}, lists)

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
form.describe input{flex:1 1 260px;min-width:0;font:400 1.1rem/1.2 var(--serif);color:var(--ink);background:var(--raise);border:1px solid var(--rule);padding:10px 12px}
form.describe input:focus{outline:2px solid var(--ink);outline-offset:1px}
.btn{font:500 .74rem/1 var(--mono);letter-spacing:.07em;text-transform:uppercase;color:var(--ink);background:none;border:1px solid var(--rule);padding:10px 13px;cursor:pointer}
.btn:hover{border-color:var(--grey)}.btn.solid{background:var(--on);color:var(--on-ink);border-color:var(--on)}
.msg{flex-basis:100%;margin:0;font-size:.85rem;color:var(--grey)}
.groups{display:grid;gap:12px}
.group{display:grid;grid-template-columns:150px 1fr;gap:10px;align-items:start}
@media (max-width:700px){.group{grid-template-columns:1fr;gap:6px}}
.gname{font:500 .68rem/2.5 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{font:400 1.02rem/1 var(--serif);color:var(--ink);background:var(--raise);border:1px solid var(--rule);padding:8px 13px 9px;border-radius:999px;cursor:pointer}
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
const $ = id => document.getElementById(id), wallEl = $("wall"), API = wallEl.dataset.api || "";
let D = null, sel = [], kind = "paint", shown = 48, lastCols = 0;
const LISTS = {}, WEIGHT = [1, 0.85, 0.7, 0.6, 0.5];       // the first word counts most
const src = im => im.startsWith("m:") ? "https://www.muis.ee/digitaalhoidla/api/meedia/pisipilt?id=" + encodeURIComponent(im.slice(2))
  : im.startsWith("e:") ? "https://digikogu.ekm.ee/static/preview/image/" + im.slice(2).replace(/\/([^\/]+)$/, "/t2_$1") : im.slice(2);
const POS = {l: "100% 50%", r: "0% 50%", t: "50% 100%", b: "50% 0%"};
const word = en => D.words.find(w => w.en === en);
const label = en => { const w = word(en); return w ? (L === "et" ? w.et : w.label) : en; };
function lists(k) {                                          // each kind's rankings, fetched the first time they are wanted
  if (!LISTS[k]) LISTS[k] = fetch(wallEl.dataset.src.replace("mood.json", "mood-" + k + ".json")).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
  return LISTS[k];
}
function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  sel = (p.get("w") || "").split(",").filter(w => D.words.some(x => x.en === w)).slice(0, 5);
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
      const b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.textContent = label(w.en);
      b.setAttribute("aria-pressed", sel.includes(w.en));
      b.onclick = () => { sel = sel.includes(w.en) ? sel.filter(x => x !== w.en) : [...sel, w.en].slice(-3); $("msg").hidden = true; update(); };
      c.append(b);
    }
    row.append(n, c); g.append(row);
  }
  document.querySelectorAll("[data-k]").forEach(b => b.setAttribute("aria-pressed", b.dataset.k === kind));
}
function ranked(ls) {
  const per = sel.map(w => ls[w] || []);
  const maps = per.map(l => new Map(l)), floors = per.map(l => l.length ? l[l.length - 1][1] - 0.5 : 0);
  const score = new Map();
  per.forEach(l => l.forEach(([i]) => score.set(i, 0)));
  for (const i of score.keys()) score.set(i, maps.reduce((s, m, j) => s + WEIGHT[j] * (m.has(i) ? m.get(i) : floors[j]), 0));
  return [...score.entries()].sort((a, b) => b[1] - a[1]).map(x => x[0]);
}
async function wall() {
  const st = $("status");
  if (!sel.length) { wallEl.textContent = ""; st.textContent = T.none; $("more").hidden = true; return; }
  const want = kind, ls = await lists(want).catch(() => null);
  if (want !== kind) return;                                  // a newer choice has been made meanwhile
  wallEl.textContent = "";
  if (!ls) { st.textContent = T.failed; return; }
  const all = ranked(ls), top = all.slice(0, shown);
  st.textContent = "";
  const b = document.createElement("b"); b.textContent = sel.map(label).join(" + ");
  st.append(b, ` · ${T.kinds[kind]} · ${top.length} ${T.of} ${all.length} ${T.works}`);
  // shortest column first, so the best matches run along the top, as on the site's wall
  const n = Math.max(2, Math.min(6, Math.floor(wallEl.clientWidth / 200))), cols = [], hs = [];
  for (let j = 0; j < n; j++) { const c = document.createElement("div"); c.className = "col"; cols.push(c); hs.push(0); wallEl.append(c); }
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
function update(keepShown) { if (!keepShown) shown = 48; chips(); wall(); writeHash(); }
function say(text) { $("msg").textContent = text; $("msg").hidden = !text; }
// the typed words, matched by stems: the way in when the reader is not there
function byStems(text) {
  const toks = text.toLowerCase().normalize("NFC").match(/[a-zõäöüšž]+/g) || [], hits = new Map();
  // a stem of three letters or fewer takes only a short ending: "sun" is sunny, not Sunday; "kuu" is kuul, not kuulus
  const fits = (tok, s) => s.length <= 3 ? tok.startsWith(s) && tok.length <= s.length + 2 : tok.startsWith(s);
  toks.forEach((tok, n) => { for (const [w, st] of Object.entries(D.stems)) if (st.some(s => fits(tok, s))) if (!hits.has(w)) hits.set(w, n); });
  return [...hits.entries()].sort((a, b) => a[1] - b[1]).map(x => x[0]).slice(0, 5);
}
async function describe(text) {
  text = text.trim(); if (!text) return;
  let got = null, k = "keep";
  if (API) {
    say(T.reading);
    try {
      const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), 6000);
      const r = await fetch(API, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({q: text}), signal: ctl.signal});
      clearTimeout(timer);
      if (r.ok) { const j = await r.json(); got = (j.words || []).filter(w => word(w)); k = j.kind || "keep"; }
    } catch (e) {}
  }
  if (!got || !got.length) got = byStems(text);
  if (!got.length) { say(T.nomatch); return; }
  sel = got; if (["paint", "paper", "all"].includes(k)) kind = k;
  say(`${T.readas}: ${got.map(label).join(", ")}`);
  update();
}
$("describe").addEventListener("submit", ev => { ev.preventDefault(); describe($("feel").value); });
document.querySelectorAll("[data-k]").forEach(b => b.onclick = () => { kind = b.dataset.k; update(); });
$("surprise").onclick = () => {
  const ws = D.words.filter(w => w.g !== "more").map(w => w.en), a = ws[Math.random() * ws.length | 0];
  let b = ws[Math.random() * ws.length | 0]; sel = Math.random() < 0.6 && b !== a ? [a, b] : [a]; say(""); update();
};
$("clear").onclick = () => { sel = []; $("feel").value = ""; say(""); update(); };
$("more").onclick = () => { shown += 48; update(true); };
$("status").textContent = T.loading;
fetch(wallEl.dataset.src).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(d => {
  D = d; readHash();
  if (!sel.length && !location.hash) sel = ["serene"];          // the page opens on a wall, not an empty shell
  chips(); wall();
}).catch(err => { $("status").textContent = T.failed; });
let rt = 0;
addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { if (D && sel.length && Math.max(2, Math.min(6, Math.floor(wallEl.clientWidth / 200))) !== lastCols) wall(); }, 150); });
addEventListener("hashchange", () => { if (D) { readHash(); shown = 48; chips(); wall(); } });
})();
"""

def page(lang, ver, api):
    t = T[lang]
    me, other = f"{BASE}/{t['file']}", f"{BASE}/{t['other']}"
    tj = json.dumps({k: t[k] for k in ("groups", "kinds", "none", "nomatch", "of", "works", "loading", "hash", "readas", "reading", "failed")}, ensure_ascii=False).replace("</", "<\\/")
    api_attr = f' data-api="{e(api)}"' if api else ""        # the Worker that reads a typed description
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
            f'<div class="wall" id="wall" data-src="data/mood.json?v={ver}"{api_attr}></div>'
            f'<button type="button" class="btn more" id="more" hidden>{e(t["more"])}</button>'
            f'<footer>{e(t["note"])} {H.CONTACT[lang]}</footer></div>'
            f'<script type="application/json" id="t">{tj}</script><script>{JS}</script></body></html>')

API = (json.load(open("data/mood_api.json", encoding="utf-8")).get("url") or "") if os.path.exists("data/mood_api.json") else ""

def worker():
    """worker/mood-worker.js: the template with this vocabulary written in; paste it into the Worker"""
    words = [w["en"] for w in json.load(open("data/moods.json", encoding="utf-8"))["words"]]
    js = open("worker/template.js", encoding="utf-8").read().replace("__WORDS__", json.dumps(words))
    js = js.replace("// GENERATED by build_mood.py", "// GENERATED by build_mood.py -- do not edit;", 1)
    old = open("worker/mood-worker.js", encoding="utf-8").read() if os.path.exists("worker/mood-worker.js") else ""
    if js != old:
        open("worker/mood-worker.js", "w", encoding="utf-8").write(js)
        print("  by mood        worker/mood-worker.js changed: paste it into the Worker again (worker/README.md)")

def main():
    d, lists = data()
    blob = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    parts = {k: json.dumps(v, ensure_ascii=False, separators=(",", ":")) for k, v in lists.items()}
    ver = hashlib.sha1((blob + "".join(parts.values())).encode()).hexdigest()[:8]
    open("site/data/mood.json", "w", encoding="utf-8").write(blob)
    for k, v in parts.items(): open(f"site/data/mood-{k}.json", "w", encoding="utf-8").write(v)
    urls = []
    for lang in ("en", "et"):
        open(f"site/{T[lang]['file']}", "w", encoding="utf-8").write(page(lang, ver, API)); urls.append(f"{BASE}/{T[lang]['file']}")
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    if os.path.exists("worker/template.js"): worker()
    print(f"  by mood        {len(d['words'])} words, {len(d['works']):,} works; mood.json {len(blob) // 1024} KB, "
          + ", ".join(f"{k} {len(v) // 1024} KB" for k, v in parts.items()) + f"; typed text read by {'the Worker' if API else 'stems only'}")

if __name__ == "__main__":
    main()
