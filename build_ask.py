# -*- coding: utf-8 -*-
"""Find a work: /find.html and /leia.html, and the stock they read, /data/stock.json.

A visitor sets the controls -- a price range, the medium, the size, mood words -- or says
what they are looking for, and the page shows works the galleries have for sale now, twelve at a time.
The assistant is Claude Sonnet behind the mood page's Worker (its /ask door,
worker/template.js): it gets the conversation and the controls as they are, and answers
with a short, factual reply and the whole search -- mood words from the same vocabulary,
title words, media, a size, a budget, an artist -- which the controls then show. It never
sees the works. The page ranks the stock itself from that search: the mood scores of the
gallery's own picture (data/stock_moods.py, on the museum pictures' scale), the title,
the medium read off the technique, the asking price the gallery's page states, and the
size read off the dimensions. Every card links to the gallery's own page, where the work
is sold.

Only current stock with the gallery's picture; a work without a price is shown only
while no budget is set. Run after build_mood.py (it adds to the sitemap) and before csp.py.

The same stock goes out for machines too: schema.org offers on the for-sale pages, every
value named in /data/for-sale.csv, and /llms.txt saying what the site is and where that lives.
"""
import json, os, re, hashlib, datetime, urllib.parse, collections, base64, shutil, csv
import build_hubs as H
import list_sync as LS   # My List across devices (list-sync.js)
import build_mood as BM
import script_mark as SM  # the build's mark on its own inline scripts (csp.py)

BASE, A, W, e = H.BASE, H.A, H.W, H.e
V = BM.V
API = BM.API

import sys; sys.path.insert(0, "data")
from moods import PAINT, PAPER

def kind_of(w):
    c = V["e"][w["e"]] if isinstance(w.get("e"), int) and w["e"] < len(V["e"]) else None
    return "paint" if c in PAINT else "paper" if c in PAPER else "sculpture" if c == "Sculpture" else "photo" if c == "Photograph" else ""

def size_of(dm):
    """small up to 40 cm on the longer side, medium to 100, large beyond; '' unknown"""
    if not dm: return ""
    s = dm.lower().replace(",", ".")
    n = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)][:2]
    if not n: return ""
    cm = max(n) / (10 if re.search(r"\bmm\b", s) else 1)
    return "" if cm < 3 else "small" if cm <= 40 else "medium" if cm <= 100 else "large"

def dims_of(dm):
    """[longer, shorter] side in cm from '60 x 80 cm', 'Diam: 47,8 cm', '600 x 400 mm'; None if unreadable"""
    if not dm: return None
    s = dm.lower().replace(",", ".")
    n = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)][:2]
    if not n: return None
    if re.search(r"\bmm\b", s): n = [x / 10 for x in n]
    if len(n) == 1: n = n * 2
    L, S = max(n), min(n)
    return [round(L, 1), round(S, 1)] if 5 <= L <= 600 and S >= 2 else None

def dims_show(dm):
    """the dimensions on a card, one way for every gallery: '62.0 x 81.0 cm' -> '62 × 81 cm'. What isn't plain numbers
    is left as the gallery wrote it; a side over 10 m is a typing slip at the source ('300 x 15000 cm') and not shown"""
    s = (dm or "").strip()
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?(?:\s*[x×X]\s*\d+(?:[.,]\d+)?)*)\s*(cm|mm)?(\s*\([^()]*\))?", s, re.I)    # '(raamiga)' stays
    if not m: return s
    n = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", m[1])]
    unit = (m[2] or "").lower()
    if unit == "cm" and max(n) > 1000: return ""
    return " × ".join(f"{x:g}" for x in n) + (" " + unit if unit else "") + (m[3] or "")

# the technique on a card, one way for every gallery ('Õli lõuendil', 'Õli/papp', 'graafika', 'Painting' on the Estonian
# page); the medium filter still reads the gallery's own words (media_of)
TECH_ET = {"painting": "Maal", "photography": "Foto", "printmaking": "Graafika", "drawing": "Joonistus", "mixed media": "Segatehnika",
           "sculpture": "Skulptuur", "oil on canvas": "Õli, lõuend", "muu": "", "other": ""}
TECH_ON = {"lõuendil": "lõuend", "papil": "papp", "masoniidil": "masoniit", "kartongil": "kartong", "paberil": "paber", "vineeril": "vineer"}

def tech_show(t):
    t = (t or "").strip()
    if t.lower() in TECH_ET: return TECH_ET[t.lower()]
    m = re.fullmatch(r"(.+?)(?:\s+|\s*[./]\s*)(lõuendil|papil|masoniidil|kartongil|paberil|vineeril|lõuend|papp|masoniit|kartong|paber|vineer)", t, re.I)
    if m and not m[1].endswith(","): t = m[1] + ", " + TECH_ON.get(m[2].lower(), m[2].lower())
    return t[:1].upper() + t[1:]

# the medium, from the technique as the gallery states it: a bit each, a work may have two (an oil painting is
# also a painting). Only what the technique says: a painting that names no medium is not "oil".
OIL = re.compile(r"õli(?!\s*pastel)|\boil\b(?!\s*pastel)|ölmal", re.I)      # oil pastel is a crayon, not paint
PRINT = re.compile(r"graafika|lino|serigraaf|siiditrükk|printmaking|\bprint|giclée|giclee|litograaf|\blito|kuivnõel|söövitus|ofort|gravüür|"
                   r"puulõige|digitrük|trükk|trükis|etching|lithograph|screen ?print|woodcut|linocut|aquatint|akvatint|mezzotint|metsotint|"
                   r"monotüüp|monotyp|kollagraaf|drypoint|engraving", re.I)
PAINTISH = re.compile(r"õli|\boil|akrüül|acryl|tempera|guaš|gouache|akvarell|watercol|segatehnika|mixed", re.I)
SCULPT = re.compile(r"skulpt|sculpt|pronks|bronze|keraamika|ceramic|portselan|graniit|marmor", re.I)
ACRYL = re.compile(r"akrüül|acryl", re.I)
WATER = re.compile(r"akvarell|watercol", re.I)
MIXED = re.compile(r"segatehnika|mixed|autoritehnika|kollaaž|collage", re.I)
DRAW = re.compile(r"joonistus|pliiats|tušš|\bsöe|\bsüsi|charcoal|pencil|\bink\b|pastell|pastel|drawing|grafiit|sangviin|sepia", re.I)
# the controls show the eight first: the six media the stock names most (2026-10-02), then sculpture and photography.
# "painting" (any medium) shows only when the chat asks for "a painting"
MEDIA = ["oil", "acrylic", "watercolour", "mixed", "print", "drawing", "sculpture", "photo", "painting"]
BIT = {"oil": 1, "print": 2, "sculpture": 4, "painting": 8, "drawing": 16, "photo": 32, "acrylic": 64, "watercolour": 128, "mixed": 256}

def media_of(kind, tech):
    m = 0
    if kind == "photo": return BIT["photo"]
    for k, r in (("oil", OIL), ("acrylic", ACRYL), ("watercolour", WATER), ("mixed", MIXED), ("print", PRINT), ("drawing", DRAW)):
        if r.search(tech): m |= BIT[k]
    if kind == "sculpture" or SCULPT.search(tech): m |= BIT["sculpture"]
    if kind == "paint" and not (m & BIT["print"] and not PAINTISH.search(tech)): m |= BIT["painting"]    # a giclée on canvas is a print
    if kind == "paper" and not m: m |= BIT["drawing"]          # on paper, and neither printed nor painted
    return m

T = {"en": dict(file="find", other="leia", other_l="Eesti keeles", site="Estonian Art Catalogue",
                h="Buy Art", title="Buy Estonian art: {n} works for sale, with prices", lede="Art for your home from the catalogue's galleries, for sale now. Each work links to the gallery that sells it.",
                desc="Paintings, prints and sculpture by Estonian artists for sale: {n} works from Estonian galleries, each with the gallery's asking price. Filter by price, medium, size, mood and artist; every work links to the gallery that sells it.",
                sh="Estonian art for sale", sp="Buy paintings, prints, watercolours and sculpture by Estonian artists from the galleries that sell them: {n} works, each with its asking price and a link to the gallery. museaal.ee is a catalogue, not a shop; the sale is the gallery's.",
                hello="Set the filters, or describe what you need: the room, size, budget, subject or mood.",
                label="Your message", ph="Describe the work you're looking for.", send="Send",
                more="Show more", at="at", noprice="Price on request", none="No work for sale matches this search. Widen the price range or clear a filter.",
                thinking="Thinking…", how="How it searched", like="Works like", choosing="Choosing from these", failed="The assistant could not be reached. Try again in a moment.", robot="This browser did not pass the site's robot check, so the assistant cannot answer here. The filters still work. For the assistant, try another browser or turn off content blockers.", record="In the catalogue",
                kinds=dict(paint="paintings", paper="works on paper", sculpture="sculpture", photo="photographs"),
                sizes=dict(small="small", medium="medium", large="large"), under="under", over="over", shown="Shown",
                media=dict(oil="Oil", acrylic="Acrylic", watercolour="Watercolour", mixed="Mixed media", print="Print", drawing="Drawing",
                           sculpture="Sculpture", photo="Photography", painting="Paintings, any medium"),
                price="Price", anyprice="Any price", upto="up to", from_="from", lowest="Lowest price", highest="Highest price",
                medium="Medium", size="Size", sizeany="Any", sizehint=dict(small="up to 40 cm", medium="40–100 cm", large="over 100 cm"),
                mood="Mood", moremoods="More words", fewer="Fewer", clear="Clear", count="{n} works", count1="1 work", show="Show {c}",
                artistonly="{who}: {n} for sale outside these settings.", showthem="Show them",
                daily="today's selection", fromchat="From the chat", artist="Artist", artistph="Type a name", artistlist="Artists with works for sale", names="Start with a name", titlew="In the title", filters="Filters",
                groups=dict(feeling="Feeling", light="Light", colour="Colour", weather="Season and weather", subject="Subject"),
                about="Sources & privacy", note="The works are the galleries' current stock with their asking prices, read weekly from each gallery's own site; the gallery's page is the one to trust. Your messages are read by Claude, which runs the searches and picks the works it suggests; they are not stored. The auction figures under a work are its artist's record as the houses published it, hammer prices: a record, not a valuation. The moods are read from the gallery's photograph by CLIP, an image model: a guide, not a judgement of the work.",
                sl_add="Add to My List", sl_remove="Remove from My List", fy="For you", fybtn="Similar to My List ({n})",
                fyhint="Bookmark three works, here, on the mood wall or in the catalogue, or save an artist, and this puts first what looks like them and the artists you saved.",
                fysee="See My List", fybit="based on My List",
                sortby="Sort", sorts=dict(best="Selection", up="Price: low to high", down="Price: high to low", new="Recently listed"),
                apage="All {n} works by {name} on one page, with prices →",
                hash=""),
     "et": dict(file="leia", other="find", other_l="In English", site="Eesti Kunstikataloog",
                h="Osta kunsti", title="Osta Eesti kunsti: müügil {n} teost koos hindadega", lede="Kunst sinu koju kataloogi galeriidest, praegu müügil. Iga teos viib seda müüva galerii lehele.",
                desc="Eesti kunstnike maalid, graafika ja skulptuurid müügil: {n} teost Eesti galeriidest, igaüks galerii hinnaga. Vali hinna, tehnika, suuruse, meeleolu ja kunstniku järgi; iga teos viib seda müüva galerii lehele.",
                sh="Eesti kunsti müük", sp="Osta Eesti kunstnike maale, graafikat, akvarelle ja skulptuure otse neid müüvatelt galeriidelt: {n} teost, igaüks hinnaga ja lingiga galeriile. museaal.ee on kataloog, mitte pood; teose müüb galerii.",
                hello="Sea filtrid või kirjelda, mida vajad: tuba, suurus, eelarve, teema või meeleolu.",
                label="Sinu sõnum", ph="Kirjelda teost, mida otsid.", send="Saada",
                more="Näita rohkem", at="", noprice="Hind päringul", none="Müügil pole ühtki teost, mis sellele otsingule vastaks. Laienda hinnavahemikku või eemalda mõni filter.",
                thinking="Mõtlen…", how="Kuidas otsisin", like="Sarnased teosele", choosing="Valin nende seast", failed="Abilist ei õnnestunud kätte saada. Proovi hetke pärast uuesti.", robot="See brauser ei läbinud saidi robotikontrolli, seega abiline ei saa siin vastata. Filtrid töötavad edasi. Abilise kasutamiseks proovi teist brauserit või lülita sisublokeerijad välja.", record="Kataloogis",
                kinds=dict(paint="maalid", paper="tööd paberil", sculpture="skulptuur", photo="fotod"),
                sizes=dict(small="väike", medium="keskmine", large="suur"), under="alla", over="üle", shown="Näidatud",
                media=dict(oil="Õli", acrylic="Akrüül", watercolour="Akvarell", mixed="Segatehnika", print="Graafika", drawing="Joonistus",
                           sculpture="Skulptuur", photo="Foto", painting="Maalid, iga tehnika"),
                price="Hind", anyprice="Iga hind", upto="kuni", from_="alates", lowest="Madalaim hind", highest="Kõrgeim hind",
                medium="Tehnika", size="Suurus", sizeany="Kõik", sizehint=dict(small="kuni 40 cm", medium="40–100 cm", large="üle 100 cm"),
                mood="Meeleolu", moremoods="Rohkem sõnu", fewer="Vähem", clear="Tühjenda", count="{n} teost", count1="1 teos", show="Näita {c}",
                artistonly="{who}: väljaspool neid seadeid müügil {n}.", showthem="Näita",
                daily="tänane valik", fromchat="Vestlusest", artist="Kunstnik", artistph="Kirjuta nimi", artistlist="Kunstnikud, kelle teoseid on müügil", names="Alusta nimest", titlew="Pealkirjas", filters="Filtrid",
                groups=dict(feeling="Tunne", light="Valgus", colour="Värv", weather="Aastaaeg ja ilm", subject="Aine"),
                about="Allikad ja privaatsus", note="Teosed on galeriide praegune müügivalik ja nende hinnad, loetud iga nädal galeriide endi lehtedelt; usaldusväärne on galerii leht. Sinu sõnumeid loeb Claude, kes teeb otsingud ja valib soovitatavad teosed; neid ei salvestata. Teose all olevad oksjoniandmed on kunstniku tulemused nii, nagu oksjonimajad need avaldasid (haamrihinnad): ülevaade, mitte hinnang. Meeleolu loeb galerii fotolt pildimudel CLIP: see on juhatus, mitte hinnang teosele.",
                sl_add="Lisa minu nimekirja", sl_remove="Eemalda minu nimekirjast", fy="Sulle", fybtn="Sarnased minu nimekirjaga ({n})",
                fyhint="Märgi järjehoidjaga kolm teost, siin, meeleolu seinal või kataloogis, või salvesta kunstnik, ja ette tulevad nendega sarnased ja sinu salvestatud kunstnikud.",
                fysee="Vaata minu nimekirja", fybit="minu nimekirja põhjal",
                sortby="Järjesta", sorts=dict(best="Valik", up="Hind: odavamad ees", down="Hind: kallimad ees", new="Hiljuti lisatud"),
                apage="{name}: kõik {n} müügil olevat teost ühel lehel, koos hindadega →",
                hash="lang=et&")}

def data():
    # how many works the museums hold by each artist: the daily selection leans to names a visitor may know
    held = collections.Counter(w["a"] for w in W if (w.get("kind") or "held") in ("held", "shown"))
    # and their record at auction, as the houses published it: lots, sold, the lowest and highest hammer price
    lots = collections.defaultdict(list)
    for w in W:
        if w.get("kind") == "auction" and not w.get("anr"): lots[w["a"]].append(w)      # no published result: not a record
    def auc(a):
        # from four sales up, the middle half of the hammer prices: a charity lot at €1 or one record sale said
        # little about what the artist's works fetch (seen: "€1–€100 000")
        L = lots.get(a, []); ps = sorted(w["ap"] for w in L if w.get("ao") and w.get("ap")); q = len(ps) >= 4
        lo, hi = (ps[len(ps) // 4], ps[(3 * len(ps)) // 4]) if q else (ps[0], ps[-1]) if ps else (0, 0)
        return [len(L), sum(1 for w in L if w.get("ao")), lo, hi, int(q)]
    S = json.load(open("data/stock_moods.json", encoding="utf-8")) if os.path.exists("data/stock_moods.json") else {}
    words = [w["en"] for w in json.load(open("data/moods.json", encoding="utf-8"))["words"]]
    aidx, arts, gals, works, ims = {}, [], {}, [], []
    seen = set()
    # the day the weekly run first saw each work, for "Recently listed" (the same dates as the feeds, rss below)
    first = json.load(open("data/gallery_seen.json", encoding="utf-8")) if os.path.exists("data/gallery_seen.json") else {}
    listed = {"G" + re.sub(r"[^A-Za-z0-9]", "", g): (datetime.date.fromisoformat(x.get("day") or x["first"] + "-01") - datetime.date(2020, 1, 1)).days
              for g, x in first.items()}
    for w in W:
        if w.get("kind") != "gallery" or not (w.get("im") or "").startswith("g:"): continue
        u = re.sub(r"^http:", "https:", w["im"][2:])
        if not u.startswith("https://") or not (w.get("url") or "").startswith("http"): continue
        k = H.key(w)
        if k in seen: continue
        seen.add(k)
        a = w["a"]
        if a not in aidx: aidx[a] = len(arts); arts.append([A[a]["n"], H.ARTIST_SLUG[a], held[a]] + auc(a))
        g = H.val(w, "mu") or ""
        gals.setdefault(g, len(gals))
        tech = H.val(w, "tce") or H.val(w, "tc") or ""                    # as the gallery states it; the English page shows field 15
        tech_en = H.val(w, "tc") or tech
        if re.search(r"\bmüüdud\b|\bsold\b", tech, re.I): continue          # a gallery's "sold" read as the technique
        works.append([w.get("t") or "", aidx[a], w.get("y") or "", u, tech_show(tech)[:60], dims_show(w.get("dm")),
                      size_of(w.get("dm")), kind_of(w), w.get("pr") or 0, gals[g], w["url"], k,
                      [x for j, z in S.get(w["im"], [])[:8] if z >= 1.0 for x in (j, round(z * 10))],   # word, z x 10, flat
                      dims_of(w.get("dm")) or 0,
                      media_of(kind_of(w), " ".join(filter(None, (H.val(w, "tce"), H.val(w, "tc"))))),
                      tech_en[:60] if tech_en != tech_show(tech) else "",
                      listed.get(k, 0)])                                    # field 16: days since 2020 it has been listed from
        ims.append(w["im"])
    return {"words": words, "artists": arts, "galleries": list(gals), "works": works, "_ims": ims, "_aidx": aidx}

JS = r"""
(function(){
var T=JSON.parse(document.getElementById('t').textContent), page=document.getElementById('chat');
var EN=document.documentElement.lang==='en', api=page.dataset.api, src=page.dataset.src, log=document.getElementById('log'), form=document.getElementById('ask'), input=document.getElementById('q');
// the A/B test of the assistant: each browser gets one version and keeps it -- 'a' looks with its tools first, 'o' answers
// in one call -- and the counts carry it; ?v=a or ?v=o picks one (the side-by-side comparison)
var V=(/[?&]v=([ao])(&|$)/.exec(location.search)||[])[1];
if(!V){try{V=localStorage.getItem('find-v')}catch(e){}if(V!=='a'&&V!=='o'){V=Math.random()<.5?'a':'o';try{localStorage.setItem('find-v',V)}catch(e){}}}
var talked=false, wentOut=false;
HUMAN.start(page.dataset.ts,document.getElementById('human'));
function gc(p,t){if(window.goatcounter&&goatcounter.count)goatcounter.count({path:p,title:t||p,event:true})}
var D=null, P=null, msgs=[], shownKeys={}, busy=false, labels=JSON.parse(document.getElementById('labels').textContent);
function stock(){ return P=P||fetch(src).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(d){
  var af=d.af=d.artists.map(function(a){return fold(a[0])});
  d.fame=d.artists.map(function(a){return Math.min(1,Math.log10(1+(a[2]||0))/3.3)});   // ~2,000 works in the museums: 1
  d.byKey={};d.works.forEach(function(w,k){var m={},f=w[12];for(var i=0;i<f.length;i+=2)m[d.words[f[i]]]=f[i+1]/10;w.m=m;w.af=af[w[1]];w.i=k;d.byKey[w[11]]=w}); D=d; tally(); apage(); return d}).catch(function(e){P=null;throw e})}
function el(tag,cls,text){var x=document.createElement(tag);if(cls)x.className=cls;if(text!=null)x.textContent=text;return x}
function eur(n){return '€'+String(n).replace(/\B(?=(\d{3})+(?!\d))/g,' ')}
function cm(d){return d?Math.round(d[0])+(d[1]!==d[0]?' × '+Math.round(d[1]):'')+' cm':''}
function hash(s){var h=0;for(var i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))|0;return (h>>>0)/4294967296}
function bubble(who,text){var b=el('div','msg '+who);b.appendChild(el('p',null,text));log.appendChild(b);b.scrollIntoView({block:'nearest',behavior:'smooth'});return b}

// ---- the search: one state, which the controls show and set, and the assistant reads and sets ----
function blank(){return {words:[],terms:[],media:[],min:0,max:0,size:'any',artist:'',you:false}}
var DAY=new Date().toISOString().slice(0,10);
var Q=blank(), MB={};             // each medium's bit in a work's field 14, from the page (build_ask.py BIT)
var PG=12, SORT='';               // works a page (12 fills two, three, four or six columns); the visitor's sort, kept apart from the search the assistant sees
// the order the visitor chose; works with no price come last, whichever way the prices run
function sorted(l){if(!SORT)return l;l=l.slice();
  if(SORT==='new')return l.sort(function(a,b){return (b[16]||0)-(a[16]||0)});
  var up=SORT==='up'?1:-1;return l.sort(function(a,b){return !a[8]-!b[8]||up*(a[8]-b[8])})}
function fold(s){return s.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase()}
// a name as typed, in any case form: 'leisi' or 'leisilt' finds Malle Leis
function hitName(af,x){return af.indexOf(x)>=0||af.split(' ').some(function(n){return n.length>=3&&x.indexOf(n)===0&&x.length-n.length<=3})}
function esc(s){return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
// every work the search admits, best first; a search that names something (words, title words) admits only what answers to it
function rank(q){
  var wt=[1,.8,.65,.5,.4], out=[], mm=0, ty=q.you&&TASTE&&TASTE.n?TASTE:null;
  q.media.forEach(function(m){mm|=MB[m]||0});
  var tr=q.terms.map(function(t){return new RegExp('(^|[^\\p{L}\\p{N}])'+esc(t),'iu')});
  var who=q.artist?fold(q.artist).split(/[\s.,-]+/).filter(function(x){return x.length>1}):[];
  D.works.forEach(function(w){
    if(mm&&!(w[14]&mm))return;
    if(q.max>0&&!(w[8]&&w[8]<=q.max))return;
    if(q.min>0&&!(w[8]&&w[8]>=q.min))return;
    if(who.length&&!who.every(function(x){return hitName(w.af,x)}))return;
    if(ty&&ty.in[w[11]])return;                   // For you: what is on the list already is not news
    var s=0;q.words.forEach(function(x,i){s+=(wt[i]||.3)*(w.m[x]||0)});
    if(tr.length&&tr.some(function(r){return r.test(w[0])}))s+=20;     // the subject the visitor named, in the title: first
    if(!q.words.length&&!tr.length)s=ty?ty.s[w.i]:.6*hash(w[11]+DAY)+(w[8]?.25:0)+.35*D.fame[w[1]]+(w[14]&8?.3:0);   // nothing named: the day's selection, paintings first
    else if(s<=0&&!who.length)return;
    if(ty&&(q.words.length||tr.length))s+=1.5*ty.s[w.i];   // For you with words: the words admit, the list orders
    if(q.size!=='any'&&w[6]&&w[6]!==q.size)return;
    if(q.size!=='any'&&!w[6])s-=50;             // size unknown: only after every one that fits
    out.push([s,w])});
  out.sort(function(a,b){return b[0]-a[0]});
  // one work per artist in each page, as far as the list allows
  var picked=[],per={},rest=[];
  out.forEach(function(p){var a=p[1][1];if(per[a]>=Math.floor(picked.length/PG)+1){rest.push(p[1]);return}per[a]=(per[a]||0)+1;picked.push(p[1])});
  return picked.concat(rest)}
function count(n){return n===1?T.count1:T.count.replace('{n}',String(n).replace(/\B(?=(\d{3})+(?!\d))/g,' '))}
function priceText(lo,hi){return lo&&hi?eur(lo)+' – '+eur(hi):hi?T.upto+' '+eur(hi):lo?T.from_+' '+eur(lo):T.anyprice}
// ---- For you: the works for sale ranked by My List (data/taste.py) ----
// The list is the only taste the page knows: read from this browser, never sent. A work for sale scores by its picture's
// nearness to the nearest picture on the list (and a little to the next), 48 bytes a picture in one space for museum
// and stock, and by its artist being on the list; its card says which. The stock's bytes are one file, fetched the
// first time For you is on; the list's other works come from a shard each, by key (build_ask.py taste_files).
var TS=page.dataset.taste, TSH=page.dataset.tshard, TSV=page.dataset.tver, NV=48, SV=null, TASTE=null, tasteP=null, SHARDS={};
var fyb=document.getElementById('foryou'), fyh=document.getElementById('fyhint');
function listNow(){return slGet().slice(-60)}       // the latest sixty
// the artists on My List (museaal.artists: their pages' slugs, which the stock's artists carry): their works lead For you
function artsNow(){try{var a=JSON.parse(localStorage.getItem('museaal.artists')||'[]');return Array.isArray(a)?a.filter(function(k){return typeof k==='string'}):[]}catch(e){return []}}
function mineN(){return slGet().length+artsNow().length}
function tasteSig(){return listNow().join(',')+'|'+artsNow().join(',')}
function tasteFresh(){return !!TASTE&&TASTE.sig===tasteSig()}
function shardOf(k){var h=0;for(var i=0;i<k.length;i++)h=(h*31+k.charCodeAt(i))|0;return ('0'+(h&255).toString(16)).slice(-2)}
function unit(b){var v=new Float32Array(b.length),n=0,i;for(i=0;i<b.length;i++){v[i]=b[i];n+=b[i]*b[i]}if(!n)return null;n=Math.sqrt(n);for(i=0;i<v.length;i++)v[i]/=n;return v}
function unb64(s){if(!s)return null;var t=atob(s),b=new Int8Array(t.length);for(var i=0;i<t.length;i++)b[i]=t.charCodeAt(i)<<24>>24;return unit(b)}
function getJSON(u){return fetch(u).then(function(r){if(!r.ok)throw 0;return r.json()})}
function buildTaste(){var keys=listNow(), need={};
  keys.forEach(function(k){if(!D.byKey[k]&&!SHARDS[shardOf(k)])need[shardOf(k)]=1});
  return Promise.all([SV||tasteBin().then(function(b){var a=new Int8Array(b);
      SV=D.works.map(function(w,i){return unit(a.subarray(i*NV,i*NV+NV))});return SV})]
    .concat(Object.keys(need).map(function(h){return getJSON(TSH+h+'.json?v='+TSV).then(function(x){SHARDS[h]=x})}))).then(function(){
    var items=[], inl={}, arts={};
    keys.forEach(function(k){inl[k]=1;var w=D.byKey[k],x;
      if(w)items.push({v:SV[w.i],a:w[1],t:w[0],an:D.artists[w[1]][0]});
      else if((x=(SHARDS[shardOf(k)]||{})[k]))items.push({v:unb64(x[1]),a:x[0],t:x[2],an:x[3]})});
    items.forEach(function(it){if(it.a>=0)arts[it.a]=1});
    var saved={}, nSaved=0, sl=artsNow();
    D.artists.forEach(function(a,i){if(sl.indexOf(a[1])>=0){saved[i]=1;nSaved++}});
    var vs=items.filter(function(it){return it.v}), n=D.works.length, s=new Float32Array(n), max=0;
    // each kept picture ranks every work for sale by nearness, and a work scores by its place, 1/(10 + place): the
    // kept works take turns at the top. By nearness itself one gallery photograph on the list outweighed two museum
    // scans (photographs are nearer photographs), and as z-scores the scans outweighed it
    vs.forEach(function(it){var c=new Float32Array(n),o=[],r=it.r=new Float32Array(n),i,d,x;
      for(i=0;i<n;i++){o.push(i);if(!SV[i]){c[i]=-9;continue}x=0;for(d=0;d<NV;d++)x+=SV[i][d]*it.v[d];c[i]=x}
      o.sort(function(a,b){return c[b]-c[a]});for(i=0;i<n;i++)r[o[i]]=SV[o[i]]?1/(10+i):0});
    D.works.forEach(function(w,i){if(inl[w[11]])return;var b1=0,b2=0,sc;
      vs.forEach(function(it){var c=it.r[i];if(c>b1){b2=b1;b1=c}else if(c>b2)b2=c});
      // with no pictures on the list, the rest come in the day's order
      sc=vs.length?b1+.3*b2:.01*hash(w[11]+DAY)+.01*D.fame[w[1]];
      if(arts[w[1]]||saved[w[1]])sc+=.055;   // as a kept work's fourth nearest
      s[i]=sc});
    // a saved artist's three nearest works for sale go to the top, as a kept work's nearest would; the rest of
    // theirs keep the lift above, so one artist with forty works does not fill every page
    var by={};D.works.forEach(function(w,i){if(saved[w[1]]&&!inl[w[11]])(by[w[1]]=by[w[1]]||[]).push(i)});
    Object.keys(by).forEach(function(a){by[a].sort(function(x,y){return s[y]-s[x]}).slice(0,3).forEach(function(i){s[i]+=.13})});
    for(var j=0;j<n;j++)if(s[j]>max)max=s[j];
    if(max)for(var i=0;i<n;i++)s[i]/=max;
    TASTE={sig:tasteSig(),s:s,in:inl,n:max?items.length+nSaved:0};tasteSave(TASTE);return TASTE})}
// the home page's Buy Art row leads with two of these (tpl_head.html): For you's twelve best, an artist each, with a
// picture, kept in this browser (museaal.foryou) and read there for three days; an empty list takes them away
function tasteSave(t){try{if(!t.n)return localStorage.removeItem('museaal.foryou');
  var ix=[],o=[],seen={},i,w;for(i=0;i<t.s.length;i++)if(t.s[i]>0&&!t.in[D.works[i][11]]&&D.works[i][3])ix.push(i);
  ix.sort(function(a,b){return t.s[b]-t.s[a]});
  for(i=0;i<ix.length&&o.length<12;i++){w=D.works[ix[i]];if(seen[w[1]])continue;seen[w[1]]=1;o.push([w[10],w[3],w[0],D.artists[w[1]][0],w[8]||0])}
  localStorage.setItem('museaal.foryou',JSON.stringify({at:Date.now(),w:o}))}catch(e){}}
// On by default from three works on the list, unless this browser turned it off (find-fy: off); the stock's bytes
// are fetched at once, beside stock.json, so the first ten wait for little more than the ranking. Default use counts
// apart from chosen: find-foryou-auto, find-foryou, find-foryou-off.
var TSB=null, fyAuto=false;
function tasteBin(){return TSB=TSB||fetch(TS).then(function(r){if(!r.ok)throw 0;return r.arrayBuffer()}).catch(function(e){TSB=null;throw e})}
function fyOff(){try{return localStorage.getItem('find-fy')==='off'}catch(e){return false}}
function fyKeep(on){try{if(on)localStorage.removeItem('find-fy');else localStorage.setItem('find-fy','off')}catch(e){}}
function fyReady(){return slGet().length>=3||artsNow().length>0}     // three works, or one artist
function fyDefault(){return fyReady()&&!fyOff()}
if(fyDefault()){Q.you=fyAuto=true;tasteBin().catch(function(){})}
// the control: how many are on the list, on from three; under three, how to begin; and the way to the list itself
function syncYou(){var n=mineN();fyb.textContent=T.fybtn.replace('{n}',n);fyb.disabled=!fyReady()&&!Q.you;fyb.setAttribute('aria-pressed',String(!!Q.you));
  fyh.textContent=!fyReady()?T.fyhint+' ':'';if(n){var a=el('a',null,T.fysee);a.href='./#'+T.hash+'list=mine';fyh.appendChild(a)}fyh.hidden=!fyh.firstChild}
// ---- the assistant's tools: Claude asks (through the Worker), the page answers from the stock it has ----
function wid(w){return 'w'+w.i}
// My List for the assistant: the latest twelve works it can name -- a work for sale from the stock (with its id, for
// similar), another from For you's shards where they are loaded. Sent with a message, kept nowhere
function myList(){var o=[];listNow().slice(-12).forEach(function(k){var w=D.byKey&&D.byKey[k],x;
  if(w)o.push({t:w[0],a:D.artists[w[1]][0],id:wid(w)});else if((x=(SHARDS[shardOf(k)]||{})[k]))o.push({t:x[2],a:x[3]})});return o}
function byId(id){var w=D.works[+String(id||'').slice(1)];return w&&wid(w)===id?w:null}
function tech(w){return EN&&w[15]||w[4]||''}     // the technique: the gallery's Estonian, its English on the English page
function row(w){var a=D.artists[w[1]];return {id:wid(w),title:w[0],artist:a[0],year:w[2]||'',technique:tech(w),size:w[13]?cm(w[13]):(w[5]||''),
  price:w[8]||null,gallery:D.galleries[w[9]],moods:Object.keys(w.m).sort(function(x,y){return w.m[y]-w.m[x]}).slice(0,3)}}
function fresh(list){return list.filter(function(w){return !shownKeys[w[11]]}).slice(0,10).map(row)}
function asQ(i){var a=function(v){return Array.isArray(v)?v.map(String):[]};
  return {words:a(i.words).filter(function(x){return labels[x]}).slice(0,5),terms:a(i.terms).map(function(t){return t.toLowerCase()}).filter(function(t){return t.length>=3}).slice(0,8),
    media:a(i.media).filter(function(x){return MB[x]}),min:Math.max(0,+i.budget_min||0),max:Math.max(0,+i.budget_max||0),
    size:/^(small|medium|large)$/.test(i.size)?i.size:'any',artist:String(i.artist||'').slice(0,60)}}
function norm(m){var s=0;for(var k in m)s+=m[k]*m[k];return Math.sqrt(s)||1}
var TOOL={
  search:function(i){var q=asQ(i),all=rank(q),r={matched:all.length,works:fresh(all)};
    if(!all.length&&q.artist){var s=blank();s.artist=q.artist;r.by_artist_any_settings=rank(s).length}
    return r},
  artist:function(i){var f=fold(String(i.name||'')).split(/[\s.,-]+/).filter(function(x){return x.length>1}),hits=[];
    if(f.length)D.artists.forEach(function(a,k){if(f.every(function(x){return hitName(D.af[k],x)}))hits.push(k)});
    var exact=hits.filter(function(k){return D.af[k]===f.join(' ')});if(exact.length)hits=exact;
    if(!hits.length)return {found:false,note:'No artist of that name has works for sale here.'};
    if(hits.length>1)return {found:false,did_you_mean:hits.slice(0,8).map(function(k){return D.artists[k][0]})};
    var k=hits[0],a=D.artists[k],ws=D.works.filter(function(w){return w[1]===k}),ps=ws.map(function(w){return w[8]}).filter(Boolean).sort(function(x,y){return x-y});
    var s=blank();s.artist=a[0];
    return {name:a[0],for_sale:ws.length,asking_prices:ps.length?[ps[0],ps[ps.length-1]]:null,museum_works:a[2],
      auction:{lots:a[3],sold:a[4],hammer:a[5]?[a[5],a[6]]:null,hammer_is:a[7]?'middle half of hammer prices':'lowest and highest'},
      works:fresh(rank(s).filter(function(w){return w[1]===k}))}},
  similar:function(i){var w=byId(i.id);if(!w)return {error:'No work with that id.'};
    var max=Math.max(0,+i.budget_max||0),n=norm(w.m);
    var out=D.works.filter(function(x){return x!==w&&(!max||x[8]&&x[8]<=max)}).map(function(x){var s=0;
      for(var k in w.m)if(x.m[k])s+=w.m[k]*x.m[k];s=s/(n*norm(x.m));if(x[14]&w[14])s+=.3;if(x[1]===w[1])s+=.1;return [s,x]});
    out.sort(function(a,b){return b[0]-a[0]});
    return {of:row(w),works:fresh(out.map(function(p){return p[1]}))}}};
function describe(q){var b=q.media.map(function(m){return T.media[m]});if(q.size!=='any')b.push(T.sizes[q.size]);
  if(q.min||q.max)b.push(priceText(q.min,q.max));b=b.concat(q.words.map(function(x){return labels[x]||x}));
  if(q.terms.length)b.push(T.titlew+': '+q.terms.join(', '));if(q.artist)b.push(q.artist);return b.join(' · ')||T.daily}
// one line of "How it searched" for a tool call and its result
function step(c,r){var i=c.input||{};
  if(c.name==='search')return describe(asQ(i))+' → '+count(r.matched||0);
  if(c.name==='artist')return T.artist+': '+(r.name||String(i.name||''))+(r.for_sale?' → '+count(r.for_sale):'');
  return T.like+' '+(r.of?r.of.title+' — '+r.of.artist:'')}
function card(w,why){
  var a=D.artists[w[1]], g=D.galleries[w[9]], c=el('article','card');
  // the picture and title, and the price, go to the gallery; the artist's name to the work in the catalogue
  function out(){var o=el('a','out');o.href=w[10];o.target='_blank';o.rel='noopener';
    // every click out by gallery; and per version: conversations that led to a click out, and clicks on a pick
    o.addEventListener('click',function(){gc('find-out',g);if(g)gc('gallery-'+g.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,''),g);if(talked&&!wentOut){wentOut=true;gc('find-conv-out-'+V)}if(why)gc('find-pick-'+V);if(Q.you)gc('find-foryou-out')});return o}
  var top=out(), img=el('img');img.src=w[3];img.alt=w[0]+', '+a[0];img.loading='lazy';img.decoding='async';img.referrerPolicy='no-referrer-when-downgrade';top.appendChild(img);
  var cap=el('span','cap');cap.appendChild(el('i',null,w[0]));top.appendChild(cap);c.appendChild(top);
  var by=el('span','by'), an=el('a',null,a[0]);an.href='./#'+T.hash+'artist='+a[1]+'&open='+encodeURIComponent(w[11]);an.title=T.record;
  by.appendChild(an);if(w[2])by.appendChild(document.createTextNode(', '+w[2]));c.appendChild(by);
  var low=out(), meta=[tech(w),EN?w[5]:w[5].replace(/(\d)\.(\d)/g,'$1,$2')].filter(Boolean).join(' · ');if(meta)low.appendChild(el('span','meta',meta));
  var pr=el('span','price');pr.appendChild(el('b',null,w[8]?eur(w[8]):T.noprice));pr.appendChild(document.createTextNode(' '+(T.at?T.at+' ':'')+g+' ↗'));low.appendChild(pr);
  c.appendChild(low);
  if(why)c.appendChild(el('p','why',why));
  c.appendChild(slBtn(w[11],T,'list-add-find',syncYou));
  return c}
// a search's settings as chips over its results, each with a way to drop it (the controls may be folded away or far up)
function drop(k,v){if(k==='media'||k==='words'){var i=Q[k].indexOf(v);if(i>=0)Q[k].splice(i,1)}else if(k==='price')Q.min=Q.max=0;else if(k==='size')Q.size='any';else if(k==='terms')Q.terms=[];else if(k==='artist')Q.artist='';changed()}
function chips(q){var box=el('div','bits'),add=function(label,k,v){var p=el('span','bit',label),x=el('button','x','×');x.type='button';x.setAttribute('aria-label',T.clear+': '+label);
    x.addEventListener('click',function(){drop(k,v)});p.appendChild(x);box.appendChild(p)};
  q.media.forEach(function(m){add(T.media[m],'media',m)});
  if(q.size!=='any')add(T.sizes[q.size],'size');
  if(q.min||q.max)add(priceText(q.min,q.max),'price');
  q.words.forEach(function(x){add(labels[x]||x,'words',x)});
  if(q.terms.length)add(T.titlew+': '+q.terms.join(', '),'terms');
  if(q.artist)add(q.artist,'artist');
  return box.firstChild?box:null}
// the search's results into box: how many answer to it, its settings, the sort, and a page at a time, leaving out works
// an earlier turn showed
function show(box,q,picks){
  var ty=q.you&&TASTE&&TASTE.n?TASTE:null, why={}, pk=(picks||[]).map(function(p){var w=byId(p.id);if(w)why[w.i]=p.why;return w}).filter(Boolean);
  var all=rank(q), list=pk.concat(all.filter(function(w){return !shownKeys[w[11]]&&!(w.i in why)})), n=0, keys=[], grid=el('div','grid'), more=el('button','btn more',T.more);more.type='button';
  var bits=[count(all.length)], set=chips(q), head=el('div','shead'), line=el('p','search');
  if(ty)bits.push(T.fybit);
  var daily=bits.length===1&&!set;
  function say(){line.textContent=bits.concat(daily&&!SORT?[T.daily]:[]).join(' · ')}
  say();head.appendChild(line);box.appendChild(head);if(set)box.appendChild(set);
  if(!list.length){box.appendChild(el('p','none',T.none));
    // an artist with works for sale outside the other settings: say how many, and offer them
    var solo=blank();solo.artist=q.artist;var k=q.artist&&(q.media.length||q.min||q.max||q.size!=='any'||q.words.length||q.terms.length)?rank(solo).length:0;
    if(k){var p=el('p','none',T.artistonly.replace('{who}',q.artist).replace('{n}',count(k))+' '),go=el('button','linkbtn',T.showthem);go.type='button';
      go.addEventListener('click',function(){Q=solo;changed()});p.appendChild(go);box.appendChild(p)}
    return {note:k?T.artistonly.replace('{who}',q.artist).replace('{n}',count(k)):'',list:list,keys:keys}}
  var view=sorted(list);
  function page(){view.slice(n,n+PG).forEach(function(w){grid.appendChild(card(w,why[w.i]));shownKeys[w[11]]=1;keys.push(w[11])});n+=PG;more.hidden=n>=view.length}
  if(list.length>1){var so=el('select','sort');so.setAttribute('aria-label',T.sortby);
    [['','best'],['up','up'],['down','down'],['new','new']].forEach(function(x){var o=el('option',null,T.sorts[x[1]]);o.value=x[0];so.appendChild(o)});so.value=SORT;
    so.addEventListener('change',function(){SORT=so.value;gc('find-sort-'+(SORT||'best'));keys.forEach(function(k){delete shownKeys[k]});keys.length=0;grid.textContent='';n=0;view=sorted(list);page();say()});
    head.appendChild(so)}
  page();box.appendChild(grid);box.appendChild(more);more.addEventListener('click',page);
  return {list:list,keys:keys,note:T.shown+' '+Math.min(PG,list.length)+' / '+all.length+': '+view.slice(0,PG).map(function(w){return w[0]+' — '+D.artists[w[1]][0]+(w[8]?', '+eur(w[8]):'')+(w[13]?', '+cm(w[13]):'')+' ['+wid(w)+']'}).join('; ')}}

// ---- the controls: price range, medium, size, mood words ----
var F=document.getElementById('filters'), plo=document.getElementById('plo'), phi=document.getElementById('phi'), pout=document.getElementById('pout');
var dual=F.querySelector('.dual'), moods=document.getElementById('moods'), fcount=document.getElementById('fcount'), chatset=document.getElementById('chatset');
MB=JSON.parse(F.dataset.bits);
var PR=JSON.parse(plo.dataset.stops), N=PR.length-1, WIDE=window.matchMedia('(min-width:980px)');   // PR's last stop: no limit
function lowAt(v){var i=0;while(v>0&&i<N-1&&PR[i+1]<=v)i++;return i}
function highAt(v){var i=1;if(!v)return N;while(i<N&&PR[i]<v)i++;return i}
function rail(){dual.style.setProperty('--a',plo.value/N);dual.style.setProperty('--b',phi.value/N);
  plo.setAttribute('aria-valuetext',Q.min?eur(Q.min):T.anyprice);phi.setAttribute('aria-valuetext',Q.max?eur(Q.max):T.anyprice);tags()}
// a figure under each handle, centred on it, kept inside the rail and pushed apart where the handles meet
var tlo=dual.querySelector('.tlo'), thi=dual.querySelector('.thi');
function tags(){var a=+plo.value,b=+phi.value,W=dual.clientWidth;if(!W)return;
  tlo.textContent=eur(PR[a]);thi.textContent=b===N?eur(PR[N-1])+'+':eur(PR[b]);
  tlo.classList.toggle('set',a>0);thi.classList.toggle('set',b<N);
  var wl=tlo.offsetWidth,wh=thi.offsetWidth,cl=9+(W-18)*a/N,ch=9+(W-18)*b/N,
      l=Math.max(0,Math.min(W-wl,cl-wl/2)),h=Math.max(0,Math.min(W-wh,ch-wh/2)),gap=l+wl+8-h;
  if(gap>0){l=Math.max(0,l-gap/2);h=Math.min(W-wh,l+wl+8)}
  tlo.style.left=l+'px';thi.style.left=h+'px'}
window.addEventListener('resize',tags)
function tally(){fcount.textContent=D?T.show.replace('{c}',count(rank(Q).length))+(WIDE.matches?'':' ↓'):''}
// the panel's foot and, on a phone, its folded line: how many settings are on; Clear only when there is something to clear
function setN(){return Q.media.length+Q.words.length+(Q.size!=='any'?1:0)+(Q.min||Q.max?1:0)+(Q.artist?1:0)+(Q.terms.length?1:0)}
function footing(){var c=setN();document.getElementById('fclear').hidden=!c;document.getElementById('fsum').textContent=c?String(c):''}
// the controls as the search is
function sync(){
  plo.value=lowAt(Q.min);phi.value=highAt(Q.max);pout.textContent=priceText(Q.min,Q.max);rail();
  Array.prototype.forEach.call(F.querySelectorAll('[data-m]'),function(b){b.setAttribute('aria-pressed',String(Q.media.indexOf(b.dataset.m)>=0))});
  Array.prototype.forEach.call(F.querySelectorAll('[data-s]'),function(b){b.setAttribute('aria-pressed',String(b.dataset.s===Q.size))});
  Array.prototype.forEach.call(F.querySelectorAll('[data-w]'),function(b){b.setAttribute('aria-pressed',String(Q.words.indexOf(b.dataset.w)>=0))});
  Array.prototype.forEach.call(F.querySelectorAll('[data-a]'),function(b){b.setAttribute('aria-pressed',String(b.dataset.a===Q.artist))});
  if(document.activeElement!==ain)ain.value=Q.artist;aclr.hidden=!Q.artist;
  var cs=chatset.querySelector('.bits');cs.textContent='';
  if(Q.terms.length){var p=el('span','bit',T.titlew+': '+Q.terms.join(', ')),b=el('button','x','×');b.type='button';b.dataset.clear='terms';b.setAttribute('aria-label',T.clear);p.appendChild(b);cs.appendChild(p)}
  chatset.hidden=!cs.firstChild;
  document.getElementById('ps').textContent=Q.size&&Q.size!=='any'?T.sizes[Q.size].replace(/^./,function(c){return c.toUpperCase()}):'';
  document.getElementById('pm').textContent=Q.media.map(function(m){return T.media[m]}).join(', ');
  document.getElementById('pa').textContent=Q.artist;apage();
  document.getElementById('pw').textContent=Q.words.map(function(w){return labels[w]}).join(', ');syncYou();tally();footing()}
// the way to the chosen artist's own for-sale page (build_ask.py artist_sale_pages: the same count, the same slugs left out)
function apage(){var p=document.getElementById('apage'),a=p.firstChild,i=-1,n=0,f=Q.artist&&fold(Q.artist);
  if(D&&f){i=D.af.indexOf(f);if(i>=0)D.works.forEach(function(w){if(w[1]===i)n++})}
  var ok=i>=0&&n>=T.apmin&&T.apskip.indexOf(D.artists[i][1])<0;p.hidden=!ok;
  if(ok){a.href='/'+T.apdir+'/'+D.artists[i][1];a.textContent=T.apage.replace('{n}',n).replace('{name}',D.artists[i][0])}}
// ---- the artist: a name typed, and chosen from those with work for sale (with how many) ----
var ain=document.getElementById('artist'), alist=document.getElementById('artists'), aclr=document.getElementById('aclear'), act=-1;
function names(s){var f=fold(s.trim());if(!D||f.length<2)return [];
  if(!D.n){D.n=D.artists.map(function(){return 0});D.works.forEach(function(w){D.n[w[1]]++})}
  var out=[];D.af.forEach(function(n,i){var k=n.indexOf(f);if(k<0||k>0&&!/[\s-]/.test(n[k-1]))return;   // from the start of a name's part
    out.push([k?1:0,D.artists[i][0],D.n[i]])});
  out.sort(function(a,b){return a[0]-b[0]||b[2]-a[2]||a[1].localeCompare(b[1])});return out.slice(0,8)}
function suggest(){var m=names(ain.value);alist.textContent='';act=-1;ain.removeAttribute('aria-activedescendant');
  m.forEach(function(x,i){var li=el('li',null,x[1]);li.id='an'+i;li.setAttribute('role','option');li.appendChild(el('span',null,String(x[2])));
    li.addEventListener('mousedown',function(e){e.preventDefault();pick(x[1])});alist.appendChild(li)});
  alist.hidden=!m.length;ain.setAttribute('aria-expanded',String(!!m.length))}
function pick(n){Q.artist=n;alist.hidden=true;ain.setAttribute('aria-expanded','false');ain.value=n;changed()}
ain.addEventListener('input',function(){if(!ain.value.trim()&&Q.artist){Q.artist='';changed()}if(D)suggest();else stock().then(suggest,function(){})});
ain.addEventListener('keydown',function(e){var it=alist.children;
  if((e.key==='ArrowDown'||e.key==='ArrowUp')&&!alist.hidden&&it.length){e.preventDefault();act=(act+(e.key==='ArrowDown'?1:it.length-1))%it.length;
    Array.prototype.forEach.call(it,function(li,i){li.setAttribute('aria-selected',String(i===act))});ain.setAttribute('aria-activedescendant','an'+act)}
  else if(e.key==='Enter'){e.preventDefault();var m=names(ain.value);if(m.length)pick(m[act>=0?act:0][1])}
  else if(e.key==='Escape'){alist.hidden=true;ain.setAttribute('aria-expanded','false')}});
ain.addEventListener('blur',function(){alist.hidden=true;ain.setAttribute('aria-expanded','false');ain.value=Q.artist});
// the block that changes made by hand redraw in place; after the assistant's turn the next change opens one of its own
var live=null;
function refresh(quiet){
  if(!D){stock().then(refresh,function(){});return}
  if(Q.you&&!tasteFresh()){if(!tasteP)tasteP=buildTaste().then(function(){tasteP=null;if(fyAuto){fyAuto=false;gc('find-foryou-auto')}refresh(quiet)},function(){tasteP=null;Q.you=false;sync();refresh(quiet)});return}
  if(Q.you&&TASTE&&!TASTE.n){Q.you=false;sync()}     // the list holds nothing the page can read (works long gone): the switch says so by being off
  if(!live||live.turn){var b=el('div','msg them');log.appendChild(b);live={b:b,box:el('div')};b.appendChild(live.box)}
  else live.keys.forEach(function(k){delete shownKeys[k]});
  live.box.textContent='';var s=show(live.box,Q);live.keys=s.keys;
  if(quiet!==true&&WIDE.matches)live.b.scrollIntoView({block:'nearest',behavior:'smooth'})}
function changed(){sync();refresh()}
function slid(e){var a=+plo.value,b=+phi.value;
  if(a>=b){if(e.target===plo)plo.value=a=b-1;else phi.value=b=a+1}
  Q.min=PR[a];Q.max=b===N?0:PR[b];pout.textContent=priceText(Q.min,Q.max);rail();tally()}
[plo,phi].forEach(function(x){x.addEventListener('input',slid);x.addEventListener('change',changed)});
function toggle(a,x){var i=a.indexOf(x);if(i>=0)a.splice(i,1);else a.push(x)}
F.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
  if(b.id==='ftoggle'){var o=F.classList.toggle('open');b.setAttribute('aria-expanded',String(o));if(o)tags();return}
  if(b.dataset.m)toggle(Q.media,b.dataset.m);
  else if(b.dataset.w)toggle(Q.words,b.dataset.w);          // in the order chosen: the first weighs most
  else if(b.dataset.s)Q.size=b.dataset.s;
  else if(b.dataset.a)Q.artist=Q.artist===b.dataset.a?'':b.dataset.a;
  else if(b.dataset.clear==='artist')Q.artist='';
  else if(b.dataset.clear==='terms')Q.terms=[];
  else if(b.id==='foryou'){Q.you=!Q.you;fyAuto=false;fyKeep(Q.you);gc(Q.you?'find-foryou':'find-foryou-off')}
  else if(b.id==='fclear'){Q=blank();Q.you=fyDefault()}      // the filters cleared; For you as this browser has it
  else if(b.id==='moremoods'){var o=moods.classList.toggle('open');b.textContent=o?T.fewer:T.moremoods;b.setAttribute('aria-expanded',String(o));return}
  else if(b===fcount){if(!WIDE.matches){F.classList.remove('open');document.getElementById('ftoggle').setAttribute('aria-expanded','false')}if(live)live.b.scrollIntoView({block:'start',behavior:'smooth'});else refresh();return}
  else return;
  changed()});
// the assistant's search, into the controls (a Worker from before the controls answers with one kind)
function take(q){var m=q.media||({paint:['painting'],paper:['print','drawing'],sculpture:['sculpture'],photo:['photo']}[q.kind]||[]);
  Q={words:(q.words||[]).slice(),terms:(q.terms||[]).slice(),media:m.filter(function(x){return MB[x]}),min:q.budget_min||0,max:q.budget_max||0,size:q.size||'any',artist:q.artist||'',you:Q.you};sync()}

function send(text){
  text=text.replace(/\s+/g,' ').trim(); if(!text||busy)return; busy=true;
  var ub=bubble('you',text);
  msgs.push({role:'user',content:text}); input.value='';
  var b=bubble('them',T.thinking); b.classList.add('wait');
  // the controls as they were when the message was sent, the same for each of its rounds
  var body={messages:msgs.slice(-12),lang:document.documentElement.lang,filters:JSON.parse(JSON.stringify(Q))}, steps=[];
  // the first search's works, shown as soon as Claude asks for it (as fast as one call) while it chooses; its answer replaces them
  var early=null;
  if(!talked){talked=true;gc('find-conv-'+V)}
  if(V==='a'){body.tools=1;body.trail=[]}
  var ml=myList();if(ml.length)body.mylist=ml;
  // a round: the Worker answers, or asks for searches, which run here on the stock and go back with the next round
  function round(){return Promise.all([HUMAN.post(api,body).then(function(r){return r.json().then(function(j){if(!r.ok)throw j;return j})}),stock()])
    .then(function(res){var q=res[0];
      if(!q.calls||!q.calls.length||!body.trail||body.trail.length>=8)return res;
      var out=q.calls.map(function(c){var r;try{r=TOOL.hasOwnProperty(c.name)?TOOL[c.name](c.input||{}):{error:'No such tool.'}}catch(e){r={error:'The search failed.'}}
        steps.push(step(c,r));return {type:'tool_result',tool_use_id:c.id,content:JSON.stringify(r)}});
      body.trail.push({role:'assistant',content:q.content},{role:'user',content:out});
      var first=!early&&q.calls.filter(function(c){return c.name==='search'})[0];
      if(first){var eb=el('div');b.appendChild(eb);var es=show(eb,asQ(first.input||{}));
        es.keys.forEach(function(k){delete shownKeys[k]});early={box:eb,s:es}}     // not yet "shown": later searches still see them
      b.firstChild.textContent=(first?T.choosing:steps[steps.length-1])+'…';
      return round()})}
  round().then(function(res){var q=res[0], s={note:'',list:[]};
    b.classList.remove('wait'); b.firstChild.textContent=q.reply||'…';
    if(steps.length){var how=el('details','steps');how.appendChild(el('summary',null,T.how));steps.forEach(function(x){how.appendChild(el('p',null,x))});b.insertBefore(how,b.firstChild.nextSibling)}
    if(early){early.s.keys.forEach(function(k){delete shownKeys[k]});
      if(q.show)early.box.remove();else{early.s.keys.forEach(function(k){shownKeys[k]=1});live={b:b,box:early.box,keys:early.s.keys,turn:true}}}
    if(q.show){take(q);var box=el('div');b.appendChild(box);s=show(box,Q,q.picks);live={b:b,box:box,keys:s.keys,turn:true}}
    else if(live)live.turn=true;
    msgs.push({role:'assistant',content:(q.reply||'')+(s.note?' ('+s.note+')':'')});
    gc('find-turn-'+V,q.show?'search':'talk');
  // what went wrong goes to the console; a browser the robot check refuses (the Worker's 401) is told so, it would fail for good
  }).catch(function(e){console.warn('Buy Art assistant:',e&&e.error||e);b.classList.remove('wait');b.firstChild.textContent=e&&e.human?T.robot:T.failed;msgs.pop()})
  .then(function(){busy=false})}
form.addEventListener('submit',function(ev){ev.preventDefault();send(input.value)});
if(!api){form.hidden=true}
// the stock (2 MB) as the visitor first reaches for a control or the message box
['pointerdown','focusin'].forEach(function(t){page.addEventListener(t,function(){stock().catch(function(){})},{once:true})});
sync();
// a search handed over in the address, from the home page's box and chips: #q=a sentence for the assistant, or the
// controls -- m=oil,print  min=  max=  s=large  w=serene,misty  a=an artist
function handoff(){var h;try{h=new URLSearchParams(location.hash.slice(1))}catch(e){return}if(!location.hash)return;
  var list=function(k){return (h.get(k)||'').split(',').filter(Boolean)}, set=false;
  if(h.get('m')){Q.media=list('m').filter(function(x){return MB[x]});set=true}
  if(h.get('w')){Q.words=list('w').filter(function(x){return labels[x]});set=true}
  if(h.get('min')){Q.min=Math.max(0,parseInt(h.get('min'),10)||0);set=true}
  if(h.get('max')){Q.max=Math.max(0,parseInt(h.get('max'),10)||0);set=true}
  if(/^(small|medium|large)$/.test(h.get('s')||'')){Q.size=h.get('s');set=true}
  if(h.get('a')){Q.artist=h.get('a').slice(0,60);set=true}
  try{history.replaceState(null,'',location.pathname+location.search)}catch(e){}
  if(set){sync();refresh()}
  var q=(h.get('q')||'').slice(0,400);if(q&&api)send(q)}
var arrived=!!location.hash&&/(^|[#&])(q|m|w|min|max|s|a)=/.test(location.hash);
handoff();window.addEventListener('hashchange',handoff);
// ten works on arrival, before any click (YC: the shortest way to the moment it pays off)
if(!arrived)stock().then(function(){if(!live)refresh(true)},function(){});
})();
"""

CSS = BM.CSS + """
.seo{margin:34px 0 0}.seo h2{font-weight:500;font-size:1.15rem;margin:0 0 6px}.seo p{max-width:66ch;color:var(--grey);margin:0 0 10px}
.browse{margin:0;font-size:.9rem;line-height:1.9;color:var(--grey)}.browse .eyebrow{margin-right:8px}.browse b{color:var(--ink);font-weight:500}
.chat{display:grid;gap:18px 32px}
@media (min-width:980px){.chat{grid-template-columns:270px minmax(0,1fr);align-items:start}
  .filters{grid-row:1 / span 2;position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto}.log,form.ask{grid-column:2}}
.filters{display:grid;gap:18px;align-content:start;border:1px solid var(--rule);background:var(--raise);padding:16px}
.f-name{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:9px;font:500 .68rem/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}
.f-name output{font:500 .8rem/1 var(--mono);letter-spacing:.02em;text-transform:none;color:var(--ink);font-variant-numeric:tabular-nums}
.filters .chips{flex-wrap:wrap;gap:6px;overflow-x:visible;padding:0;-webkit-mask-image:none;mask-image:none}
.fold>summary{cursor:pointer;list-style:none;margin-bottom:0}.fold>summary::-webkit-details-marker{display:none}
.fold>summary::after{content:"+";font-size:.9rem;letter-spacing:0}.fold[open]>summary::after{content:"−"}.fold[open]>summary{margin-bottom:9px}
.fold .picked{flex:1;text-align:left;font:500 .8rem/1.2 var(--mono);letter-spacing:.02em;text-transform:none;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.filters .chips.scroll{max-height:168px;overflow-y:auto;align-content:flex-start;padding-right:4px}
.about summary{cursor:pointer;display:inline}.about p{margin:8px 0 0}
/* the panel in two faces: mono for its headings, figures and buttons, the sans for every option and line of text */
.filters .chip{font:400 .86rem/1 var(--sans);padding:7px 11px}
#akeys{margin-top:10px}
#akeys .n{font:400 .7rem/1 var(--mono);color:var(--grey)}
#akeys [aria-pressed=true] .n{color:inherit}
#media .x:not([aria-pressed=true]),#moods:not(.open) .x:not([aria-pressed=true]),#moods:not(.open) .gname{display:none}
.gname{flex-basis:100%;margin-top:8px;font:500 .62rem/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}
.linkbtn{background:none;border:0;padding:6px 2px;font:500 .68rem/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--grey);text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.linkbtn:hover{color:var(--ink)}
.apage{margin:-6px 0 14px;font-size:.85rem;line-height:1.4}.apage a{color:var(--ink);text-underline-offset:3px}
.filters .seg .btn{flex:1;padding:9px 4px;font-size:.66rem}
.dual{position:relative;height:46px;margin:0 2px}
.dual .tag{position:absolute;top:30px;left:0;white-space:nowrap;font:500 .7rem/1 var(--mono);color:var(--grey);font-variant-numeric:tabular-nums;pointer-events:none}.dual .tag.set{color:var(--ink)}
.dual .track,.dual .fill{position:absolute;top:13px;height:2px;pointer-events:none}
.dual .track{left:0;right:0;background:var(--rule)}
.dual .fill{left:calc(9px + (100% - 18px) * var(--a));right:calc(9px + (100% - 18px) * (1 - var(--b)));background:var(--ink)}
.dual input{position:absolute;left:0;top:0;width:100%;height:28px;margin:0;background:none;pointer-events:none;-webkit-appearance:none;appearance:none}
.dual input::-webkit-slider-runnable-track{height:2px;background:none}
.dual input::-moz-range-track{height:2px;background:none}
.dual input::-webkit-slider-thumb{pointer-events:auto;-webkit-appearance:none;appearance:none;width:18px;height:18px;margin-top:-8px;border-radius:50%;background:var(--on);border:3px solid var(--raise);box-shadow:0 0 0 1px var(--grey);cursor:pointer}
.dual input::-moz-range-thumb{pointer-events:auto;width:12px;height:12px;border-radius:50%;background:var(--on);border:3px solid var(--raise);box-shadow:0 0 0 1px var(--grey);cursor:pointer}
.dual input:focus-visible{outline:none}.dual input:focus-visible::-webkit-slider-thumb{box-shadow:0 0 0 2px var(--ink)}.dual input:focus-visible::-moz-range-thumb{box-shadow:0 0 0 2px var(--ink)}
.acomp{position:relative}
.acomp input{width:100%;font:400 .9rem/1.2 var(--sans);color:var(--ink);background:var(--paper);border:1px solid var(--rule);border-radius:0;padding:8px 30px 8px 10px;-webkit-appearance:none;appearance:none}
.acomp input::-webkit-search-cancel-button{display:none}
.acomp input:focus{outline:2px solid var(--ink);outline-offset:1px}
.acomp .x{position:absolute;right:2px;top:50%;transform:translateY(-50%);background:none;border:0;color:var(--grey);font-size:1.1rem;line-height:1;padding:4px 7px;cursor:pointer}.acomp .x:hover{color:var(--ink)}
.acomp ul{position:absolute;left:0;right:0;top:100%;z-index:5;margin:3px 0 0;padding:4px 0;list-style:none;background:var(--raise);border:1px solid var(--grey);max-height:264px;overflow:auto}
.acomp li{display:flex;justify-content:space-between;gap:10px;padding:7px 10px;cursor:pointer;font:400 .86rem/1.3 var(--sans)}
.acomp li span{font:500 .72rem/1.6 var(--mono);color:var(--grey);font-variant-numeric:tabular-nums}
.acomp li:hover,.acomp li[aria-selected=true]{background:var(--field)}
#chatset .bits{display:flex;flex-wrap:wrap;gap:6px}
#chatset .bit{display:inline-flex;align-items:center;gap:4px;font-size:.85rem;border:1px solid var(--rule);padding:3px 4px 3px 9px}
#chatset .x{background:none;border:0;color:var(--grey);font-size:1rem;line-height:1;padding:2px 5px;cursor:pointer}#chatset .x:hover{color:var(--ink)}
.f-foot{display:flex;justify-content:space-between;align-items:center;gap:8px;border-top:1px solid var(--rule);padding-top:12px}
.count{background:var(--ink);border:0;padding:9px 12px;font:500 .8rem/1 var(--mono);color:var(--paper);font-variant-numeric:tabular-nums;white-space:nowrap;cursor:pointer}.count:empty{visibility:hidden}
/* the panel on a phone: one line until asked for, so the works come first */
.f-toggle{display:none}
@media (max-width:979px){.f-toggle{display:flex;width:100%;margin:0;background:none;border:0;padding:0;cursor:pointer;align-items:center}
  .f-toggle::after{content:"+";font-size:.9rem;letter-spacing:0}.filters.open .f-toggle::after{content:"−"}
  .f-toggle .picked{flex:1;text-align:left;font:500 .8rem/1 var(--mono);letter-spacing:0;color:var(--ink)}
  .filters:not(.open)>:not(.f-toggle){display:none}}
.shead{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:6px 12px;margin-top:10px}.shead .search{margin:0!important}
.sort{font:500 .72rem/1.2 var(--mono);color:var(--ink);background:var(--raise);border:1px solid var(--rule);border-radius:0;padding:6px 8px;cursor:pointer}
.log>.msg .bits{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.log>.msg .bit{display:inline-flex;align-items:center;gap:4px;font-size:.82rem;color:var(--ink);border:1px solid var(--rule);padding:2px 3px 2px 8px}
.log>.msg .bit .x{background:none;border:0;color:var(--grey);font-size:1rem;line-height:1;padding:2px 5px;cursor:pointer}.log>.msg .bit .x:hover{color:var(--ink)}
.log{display:grid;gap:16px}
.msg p{margin:0}
.msg.you{justify-self:end;max-width:min(560px,90%);background:var(--raise);border:1px solid var(--rule);padding:10px 14px;font:400 1.05rem/1.4 var(--serif)}
.msg.them>p:first-child{font:400 1.18rem/1.45 var(--serif);max-width:62ch}
.msg.wait>p:first-child{color:var(--grey)}
.search{margin:10px 0 0!important;font:500 .72rem/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--grey)}
.none{margin-top:10px!important;color:var(--grey)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:18px 14px;margin-top:14px}
@media (min-width:980px){.log .grid{grid-template-columns:repeat(auto-fill,minmax(205px,1fr));gap:24px 18px}}
.card{display:grid;align-content:start;gap:4px}
.card .out{display:grid;gap:3px;text-decoration:none}
.card img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:var(--field)}
.card .sl{top:2px;right:2px}
.card .cap{padding-top:5px;font-size:.78rem;line-height:1.3;color:var(--grey)}
.card .cap i{display:block;font:italic 400 1rem/1.2 var(--serif);color:var(--ink)}
.card .out:hover .cap i{text-decoration:underline}
.card .meta{font-size:.74rem;color:var(--grey);line-height:1.3}
.card .price{font-size:.78rem;color:var(--grey)}.card .price b{font:500 .86rem/1.3 var(--mono);color:var(--ink);margin-right:4px}
.filters .chip:disabled,.switch:disabled{opacity:.45;cursor:default}
/* For you: an on/off switch, not a chip, so it reads as a setting rather than a tag */
.switch{position:relative;display:flex;align-items:center;gap:10px;width:100%;background:none;border:0;padding:2px 0;color:var(--ink);font:400 .86rem/1.3 var(--sans);text-align:left;cursor:pointer}
.switch::before{content:"";flex:none;width:34px;height:20px;border-radius:10px;background:var(--rule);transition:background .15s}
.switch::after{content:"";position:absolute;left:3px;top:50%;width:14px;height:14px;margin-top:-7px;border-radius:50%;background:var(--grey);transition:transform .15s,background .15s}
.switch[aria-pressed=true]::before{background:var(--ink)}.switch[aria-pressed=true]::after{transform:translateX(14px);background:var(--paper)}
.f-hint{margin:8px 0 0;font:400 .8rem/1.4 var(--sans);color:var(--grey)}.f-hint a{color:var(--ink)}
.card .by{font-size:.78rem;line-height:1.3;color:var(--grey)}
.card .by a{color:inherit;text-decoration:none}.card .by a:hover{color:var(--ink);text-decoration:underline}
.card .why{margin:2px 0 0;font-size:.78rem;line-height:1.35;color:var(--ink)}
.steps{margin:6px 0 0;font-size:.74rem;color:var(--grey)}.steps summary{cursor:pointer}.msg .steps p{margin:3px 0 0 1em}
.more{justify-self:start;margin-top:12px}
form.ask{position:sticky;bottom:0;background:var(--paper);padding:12px 0 6px;border-top:1px solid var(--rule);display:flex;gap:8px;flex-wrap:wrap}
form.ask label[for=q]{position:absolute;left:-9999px}
form.ask input{flex:1 1 260px;min-width:0;font:400 1.1rem/1.2 var(--serif);color:var(--ink);background:var(--raise);border:1px solid var(--rule);padding:11px 12px}
form.ask .human{flex-basis:100%}
form.ask input:focus{outline:2px solid var(--ink);outline-offset:1px}
"""

PRICE_STOPS = [0, 50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1250, 1500, 1750, 2000, 2500, 3000, 3500,
               4000, 5000, 6000, 7500, 10000, 12500, 15000, 20000, 30000, 50000, 0]     # the last: no limit
TOP_MOODS = ["serene", "contemplative", "melancholy", "nostalgic", "joyful", "playful", "romantic", "dreamy", "mysterious",
             "dramatic", "bright", "dark"]

# "Start with a name", under the artist field: sixteen artists a museum holds ten works or more of, the most works for
# sale first, with an editor's hand on top -- DOOR_KEEP are in whenever a gallery has anything of theirs, DOOR_SKIP
# never. The home page's names are the canon (tpl_app.html CANON), not this
DOOR_KEEP = ["Malle Leis", "Mare Vint", "Tõnis Vint", "Eduard Wiiralt"]
DOOR_SKIP = ["Reti Saks", "Maret Olvet", "Tõnis Saadoja", "Uno Roosvalt"]

def door_names(d):
    n = collections.Counter(w[1] for w in d["works"])
    order = lambda x: (-x[1], x[0])
    kept = [(a[0], n[i]) for i, a in enumerate(d["artists"]) if n[i] and a[0] in DOOR_KEEP]
    rest = sorted(((a[0], n[i]) for i, a in enumerate(d["artists"]) if n[i] and a[2] >= 10 and a[0] not in DOOR_KEEP and a[0] not in DOOR_SKIP), key=order)
    return sorted(kept + rest[:16 - len(kept)], key=order)

def panel(t, labels, M, names=()):
    """the controls, written out; the script keeps them and the search in step. Media past the three asked
    for, and mood words past the first twelve, show when chosen (by hand or by the assistant)"""
    chip = lambda attr, v, label, x="": f'<button type="button" class="chip{x}" data-{attr}="{v}" aria-pressed="false">{e(label)}</button>'
    media = "".join(chip("m", m, t["media"][m], "" if i < 8 else " x") for i, m in enumerate(MEDIA))
    sizes = "".join(f'<button type="button" class="chip" data-s="{k}" aria-pressed="{str(k == "any").lower()}"'
                    + (f' title="{e(t["sizehint"][k])}"' if k != "any" else "") + f'>{e(t["sizeany"] if k == "any" else t["sizes"][k].capitalize())}</button>'
                    for k in ("any", "small", "medium", "large"))
    grp = {w["en"]: ("feeling" if w["g"] == "more" else w["g"]) for w in M}
    moods = "".join(chip("w", w, labels[w]) for w in TOP_MOODS)
    for g in t["groups"]:
        rest = [w["en"] for w in M if grp[w["en"]] == g and w["en"] not in TOP_MOODS]
        if rest: moods += f'<span class="gname">{e(t["groups"][g])}</span>' + "".join(chip("w", w, labels[w], " x") for w in rest)
    moods += f'<button type="button" class="linkbtn" id="moremoods" aria-expanded="false" aria-controls="moods">{e(t["moremoods"])}</button>'
    n = len(PRICE_STOPS) - 1
    return (f'<div class="filters" id="filters" role="group" aria-label="{e(t["filters"])}" data-bits="{e(json.dumps(BIT))}">'
            f'<button type="button" class="f-name f-toggle" id="ftoggle" aria-expanded="false" aria-controls="filters">{e(t["filters"])} <span class="picked" id="fsum"></span></button>'
            f'<div class="f-row" id="fyou"><div class="f-name">{e(t["fy"])}</div><button type="button" class="switch" id="foryou" aria-pressed="false" disabled>{e(t["fybtn"].format(n=0))}</button>'
            f'<p class="f-hint" id="fyhint" hidden></p></div>'
            f'<div class="f-row"><div class="f-name">{e(t["price"])} <output id="pout">{e(t["anyprice"])}</output></div>'
            f'<div class="dual" style="--a:0;--b:1"><span class="track"></span><span class="fill"></span>'
            f'<input type="range" id="plo" min="0" max="{n}" step="1" value="0" aria-label="{e(t["lowest"])}" data-stops="{json.dumps(PRICE_STOPS)}">'
            f'<input type="range" id="phi" min="0" max="{n}" step="1" value="{n}" aria-label="{e(t["highest"])}">'
            '<span class="tag tlo" aria-hidden="true"></span><span class="tag thi" aria-hidden="true"></span></div></div>'
            f'<details class="f-row fold"><summary class="f-name">{e(t["medium"])} <span class="picked" id="pm"></span></summary><div class="chips scroll" id="media">{media}</div></details>'
            f'<details class="f-row fold"><summary class="f-name">{e(t["size"])} <span class="picked" id="ps"></span></summary><div class="chips">{sizes}</div></details>'
            f'<details class="f-row fold"><summary class="f-name">{e(t["artist"])} <span class="picked" id="pa"></span></summary><div class="acomp">'
            f'<input id="artist" type="search" autocomplete="off" spellcheck="false" placeholder="{e(t["artistph"])}" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="artists">'
            f'<button type="button" class="x" id="aclear" data-clear="artist" aria-label="{e(t["clear"])}" hidden>×</button>'
            f'<ul id="artists" role="listbox" aria-label="{e(t["artistlist"])}" hidden></ul></div>'
            f'<div class="chips scroll" id="akeys" role="group" aria-label="{e(t["names"])}">'
            + "".join(f'<button type="button" class="chip" data-a="{e(a)}" aria-pressed="false">{e(a)} <span class="n">{c}</span></button>' for a, c in names)
            + '</div></details>'
            '<p class="apage" id="apage" hidden><a></a></p>'       # the chosen artist's own for-sale page, when there is one
            f'<details class="f-row fold"><summary class="f-name">{e(t["mood"])} <span class="picked" id="pw"></span></summary><div class="chips scroll" id="moods">{moods}</div></details>'
            f'<div class="f-row" id="chatset" hidden><div class="f-name">{e(t["fromchat"])}</div><div class="bits"></div></div>'
            f'<div class="f-foot"><button type="button" class="count" id="fcount"></button><button type="button" class="linkbtn" id="fclear">{e(t["clear"])}</button></div>'
            '</div>')

def page(lang, ver, api, labels, M, n=0, tver="", names=()):
    t = T[lang]
    me, other = f"{BASE}/{t['file']}", f"{BASE}/{t['other']}"
    tj = json.dumps({k: t[k] for k in ("more", "at", "noprice", "none", "thinking", "how", "like", "choosing", "failed", "robot", "record", "sizes", "shown", "hash",
                                       "media", "anyprice", "upto", "from_", "count", "count1", "show", "moremoods", "fewer", "clear", "artist", "titlew", "artistonly", "showthem", "daily",
                                       "sl_add", "sl_remove", "fybtn", "fyhint", "fysee", "fybit", "sortby", "sorts", "apage")}
                    | {"apdir": SALE_DIR[lang], "apmin": ARTIST_MIN, "apskip": [x for s in SALE for x in (s[2], s[4])]}, ensure_ascii=False).replace("</", "<\\/")
    lj = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")
    ask = (api.rstrip("/") + "/ask") if api else ""
    ts = f' data-ts="{e(BM.TS)}"' if ask and BM.TS else ""       # the Worker's Turnstile site key
    N = f"{n:,}".replace(",", " " if lang == "et" else ",")
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(t["title"].format(n=f"{n:,}".replace(",", " " if lang == "et" else ",")))} · museaal.ee</title><meta name="description" content="{e(t["desc"].format(n=N))}">'
            f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
            f'<link rel="alternate" type="application/rss+xml" title="New for sale" href="{BASE}/feed.xml">'
            '<link rel="stylesheet" href="/fonts/fonts.css">'
            f'<style>{CSS}</style>{H.GC}{LS.TAG}</head><body><div class="wrap">'
            f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{e(t["site"])}</a> › {e(t["h"])} · <a href="{other}" hreflang="{"et" if lang == "en" else "en"}">{e(t["other_l"])}</a></nav>'
            f'<header><h1>{e(t["h"])}</h1><p class="lede">{e(t["lede"])}</p></header>'
            f'<section class="chat" id="chat" data-api="{e(ask)}" data-src="data/stock.json?v={ver}" data-taste="data/taste-stock.bin?v={tver}" data-tshard="data/taste/" data-tver="{tver}"{ts}>'
            f'{panel(t, labels, M, names)}<div class="log" id="log" aria-live="polite"><div class="msg them"><p>{e(t["hello"])}</p></div></div>'
            f'<form class="ask" id="ask"><label for="q">{e(t["label"])}</label><input id="q" type="text" maxlength="400" autocomplete="off" placeholder="{e(t["ph"])}">'
            f'<button class="btn solid" type="submit">{e(t["send"])}</button>'
            + '<div class="human" id="human"></div></form></section>'
            # in words a search engine reads ("osta kunsti", "maalide müük"): the panel above is drawn in the browser
            + f'<section class="seo"><h2>{e(t["sh"])}</h2><p>{e(t["sp"].format(n=N))}</p>{browse_links(lang)}</section>'
            + f'<footer><details class="about"><summary>{e(t["about"])}</summary><p>{e(t["note"])} {H.CONTACT[lang]}</p></details></footer></div>'
            f'<script type="application/json" id="t">{tj}</script><script type="application/json" id="labels">{lj}</script>{SM.OPEN}{BM.SL_JS}{BM.HUMAN_JS}{JS}</script></body></html>')

# Pages a search engine can read: the works for sale by medium and by price, in both languages. Buy art for your
# home draws its works in the browser, so a search for "oil paintings for sale" found nothing of them; these list
# them as plain HTML, each work linking to the gallery and to its artist's page, and the controls a link away.
SALE = [  # key, the controls' address, English slug and heading, Estonian slug and heading
    ("oil", "m=oil", "oil-paintings", "Oil paintings for sale", "olimaalid", "Õlimaalid müügil"),
    ("acrylic", "m=acrylic", "acrylic-paintings", "Acrylic paintings for sale", "akryylmaalid", "Akrüülmaalid müügil"),
    ("watercolour", "m=watercolour", "watercolours", "Watercolours for sale", "akvarellid", "Akvarellid müügil"),
    ("mixed", "m=mixed", "mixed-media", "Mixed media works for sale", "segatehnika", "Segatehnikas teosed müügil"),
    ("print", "m=print", "prints", "Prints for sale", "graafika", "Graafika müügil"),
    ("drawing", "m=drawing", "drawings", "Drawings for sale", "joonistused", "Joonistused müügil"),
    ("sculpture", "m=sculpture", "sculpture", "Sculpture for sale", "skulptuur", "Skulptuurid müügil"),
    ("photo", "m=photo", "photography", "Photographs for sale", "fotod", "Fotod müügil"),
    ((0, 300), "max=300", "under-300", "Art for sale under €300", "alla-300", "Kunst müügil alla 300 €"),
    ((300, 1000), "min=300&max=1000", "300-1000", "Art for sale, €300–1,000", "300-1000", "Kunst müügil 300–1000 €"),
    ((1000, 3000), "min=1000&max=3000", "1000-3000", "Art for sale, €1,000–3,000", "1000-3000", "Kunst müügil 1000–3000 €"),
    ((3000, 0), "min=3000", "over-3000", "Art for sale over €3,000", "ule-3000", "Kunst müügil üle 3000 €"),
]
SALE_DIR = {"en": "for-sale", "et": "muugil"}
ST = {"en": dict(lede="{n} works at {g} Estonian galleries, with their asking prices. Each links to the gallery that sells it.",
                 lede1="1 work at an Estonian gallery, with its asking price.", more="Filter these in Buy Art →",
                 browse="Browse what is for sale", first="The first {k} of {n} here; all of them in Buy Art.", artist="Artist's page"),
      "et": dict(lede="{n} teost {g} Eesti galeriis koos hindadega. Iga teos viib seda müüva galerii lehele.",
                 lede1="1 teos Eesti galeriis koos hinnaga.", more="Vali neist lehel Osta kunsti →",
                 browse="Sirvi müügil olevat", first="Siin esimesed {k} teost {n}-st; kõik lehel Osta kunsti.", artist="Kunstniku leht")}

def browse_links(lang, here=None):
    i = 3 if lang == "en" else 5
    return (f'<p class="browse"><span class="eyebrow">{e(ST[lang]["browse"])}</span> ' + " · ".join(
        (f'<b>{e(s[i])}</b>' if s[2 if lang == "en" else 4] == here else
         f'<a href="{BASE}/{SALE_DIR[lang]}/{s[2] if lang == "en" else s[4]}">{e(s[i])}</a>') for s in SALE) + "</p>")

def sale_pages(d):
    eur = lambda n, lang: ("€" + f"{n:,}".replace(",", " ")) if lang == "en" else (f"{n:,}".replace(",", " ") + " €")
    arts, gals, W_ = d["artists"], d["galleries"], d["works"]
    urls = []
    for key, hashq, sl_en, h_en, sl_et, h_et in SALE:
        if isinstance(key, tuple): lo, hi = key; pick = [w for w in W_ if w[8] and w[8] >= lo and (not hi or w[8] < hi)]
        else: bit = BIT[key]; pick = [w for w in W_ if w[14] & bit]
        # priced first, then the names the museums hold most of, one an artist in turn
        pick.sort(key=lambda w: (not w[8], -arts[w[1]][2], w[8] or 0))
        rows, per = [], collections.Counter()
        for r in range(4):
            for w in pick:
                if per[w[1]] == r and len(rows) < 72 and w not in rows: rows.append(w); per[w[1]] += 1
        rows += [w for w in pick if w not in rows][:max(0, 72 - len(rows))]
        g = len({w[9] for w in pick})
        for lang, sl, h in (("en", sl_en, h_en), ("et", sl_et, h_et)):
            t, st = T[lang], ST[lang]
            me = f"{BASE}/{SALE_DIR[lang]}/{sl}"; other = f"{BASE}/{SALE_DIR['et' if lang == 'en' else 'en']}/{sl_et if lang == 'en' else sl_en}"
            lede = st["lede1"] if len(pick) == 1 else st["lede"].format(n=f"{len(pick):,}".replace(",", " " if lang == "et" else ","), g=g)
            cards = "".join(
                f'<article class="card"><a class="out" href="{e(w[10])}" target="_blank" rel="noopener" data-out="{e(gals[w[9]])}">'
                f'<img src="{e(w[3])}" alt="{e(w[0])}, {e(arts[w[1]][0])}" loading="lazy" decoding="async" referrerpolicy="no-referrer-when-downgrade">'
                f'<span class="cap"><i>{e(w[0])}</i>{e(arts[w[1]][0])}{", " + e(str(w[2])) if w[2] else ""}</span>'
                + (f'<span class="meta">{e(" · ".join(x for x in ((lang == "en" and w[15]) or w[4], w[5] if lang == "en" else re.sub(r"(?<=[0-9])[.](?=[0-9])", ",", w[5])) if x))}</span>' if (w[4] or w[5]) else "")
                + f'<span class="price"><b>{eur(w[8], lang) if w[8] else e(t["noprice"])}</b> {e((t["at"] + " ") if t["at"] else "")}{e(gals[w[9]])} ↗</span></a>'
                f'<a class="rec" href="{BASE}/{"a" if lang == "en" else "k"}/{arts[w[1]][1]}">{e(st["artist"])}</a></article>' for w in rows)
            find = f'{BASE}/{t["file"]}#{hashq}'
            ld = H.ldjson({"@context": "https://schema.org", "@type": "CollectionPage", "name": h, "url": me, "inLanguage": lang,
                           "mainEntity": {"@type": "ItemList", "numberOfItems": len(pick), "itemListElement": [
                               {"@type": "ListItem", "position": k + 1, "item": H.offer_item(
                                   w[0], arts[w[1]][0], w[2], (lang == "en" and w[15]) or w[4], w[3], w[8], gals[w[9]], w[10])}
                               for k, w in enumerate(rows)]}})
            html_ = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                     f'<title>{e(h)} · museaal.ee</title><meta name="description" content="{e(lede[:290])}">'
                     f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
                     f'<link rel="alternate" type="application/rss+xml" title="New for sale" href="{BASE}/feed.xml">'
                     f'<script type="application/ld+json">{ld}</script>'
                     '<link rel="stylesheet" href="/fonts/fonts.css">'
                     f'<style>{CSS}</style>{H.GC}</head><body><div class="wrap">'
                     f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{e(t["site"])}</a> › <a href="{BASE}/{t["file"]}">{e(t["h"])}</a> › {e(h)} · '
                     f'<a href="{other}" hreflang="{"et" if lang == "en" else "en"}">{e(t["other_l"])}</a></nav>'
                     f'<header><h1>{e(h)}</h1><p class="lede">{e(lede)}</p><p><a class="btn solid" href="{e(find)}">{e(st["more"])}</a></p></header>'
                     f'<div class="grid">{cards}</div>'
                     + (f'<p class="m">{e(st["first"].format(k=len(rows), n=len(pick)))}</p>' if len(pick) > len(rows) else "")
                     + browse_links(lang, sl)
                     + f'<footer>{e(t["note"].split(". ")[0])}. {H.CONTACT[lang]}</footer></div>{H.out_js("forsale")}</body></html>')
            os.makedirs(f"site/{SALE_DIR[lang]}", exist_ok=True)
            open(f"site/{SALE_DIR[lang]}/{sl}.html", "w", encoding="utf-8").write(html_); urls.append(me)
    return urls

# A for-sale page per artist with three or more works in stock: /for-sale/<artist>, /muugil/<artist>. The search
# "<name> paintings for sale" met only the artist page, whose title and most of whose words are the museum record;
# this page is the stock alone -- every work with its asking price and gallery -- then the record at auction, and
# its title says so first. Fewer than three works stay on the artist page: a page of one card is a doorway.
ARTIST_MIN, ARTIST_CAP = 3, 120
KINDS = [  # the word for most of an artist's stock: bits of field 14, English, Estonian
    (BIT["oil"] | BIT["acrylic"] | BIT["watercolour"] | BIT["painting"], "paintings", "maalid"),
    (BIT["print"], "prints", "graafika"), (BIT["drawing"], "drawings", "joonistused"),
    (BIT["sculpture"], "sculpture", "skulptuurid"), (BIT["photo"], "photographs", "fotod")]
AT = {"en": dict(title="{name} {kind} for sale – {n} works{rng}", h="{name}: {kind} for sale", art="art",
                 lede="{n} works by {name}{dates} for sale at {gals}{rng}. Prices are the galleries' asking prices; each work links to the gallery that sells it.",
                 rng=", {lo}–{hi}", rng1=", {lo}", first="The {k} lowest-priced of {n} here; all of them in Buy Art.",
                 more="Filter these in Buy Art →", page="{name}: all works, museums, biography →", feed="Follow new works for sale (RSS)",
                 auh="{name} at auction", au="{n} lots at Estonian auction houses, {y}; {s} sold{r}.", aur=", most for {lo}–{hi}", aur0=", for {lo}–{hi}",
                 unsold="unsold", sold="sold", link="All {n} works for sale, with prices →"),
      "et": dict(title="{name}: {kind} müügil – {n} teost{rng}", h="{name}: {kind} müügil", art="teosed",
                 lede="{name}{dates}: {n} teost müügil, {gals}{rng}. Hinnad on galeriide müügihinnad; iga teos viib seda müüva galerii lehele.",
                 rng=", {lo}–{hi}", rng1=", {lo}", first="Siin {k} soodsaimat teost {n}-st; kõik lehel Osta kunsti.",
                 more="Vali neist lehel Osta kunsti →", page="{name}: kõik teosed, muuseumid, elulugu →", feed="Jälgi uusi müügil olevaid teoseid (RSS)",
                 auh="{name} oksjonitel", au="{n} teost Eesti oksjonitel, {y}; müüdud {s}{r}.", aur=", enamik hinnaga {lo}–{hi}", aur0=", hinnaga {lo}–{hi}",
                 unsold="müümata", sold="müüdud", link="Kõik {n} müügil olevat teost koos hindadega →")}
MARK = "<!--for-sale-page-->"   # build_pages.py leaves it under an artist's "For sale now"; the link to this page goes there

def artist_sale_pages(d):
    arts, gals, W_ = d["artists"], d["galleries"], d["works"]
    money = lambda p, lang: f"€{p:,}" if lang == "en" else f"{p:,} €".replace(",", " ")
    by = collections.defaultdict(list)
    for w in W_: by[w[1]].append(w)
    who = {sl: i for i, sl in H.ARTIST_SLUG.items()}
    lots = collections.defaultdict(list)
    for w in W:
        if w.get("kind") == "auction" and not w.get("anr") and w.get("ad"): lots[w["a"]].append(w)
    taken = {s[2] for s in SALE} | {s[4] for s in SALE}
    urls, n_pages, made = [], 0, []
    for ai, ws in by.items():
        name, sl = arts[ai][0], arts[ai][1]
        if len(ws) < ARTIST_MIN or sl in taken or sl not in who:
            for p in (f"site/a/{sl}.html", f"site/k/{sl}.html"):          # no page of their own: the mark goes
                if os.path.exists(p):
                    s = open(p, encoding="utf-8").read()
                    if MARK in s: open(p, "w", encoding="utf-8").write(s.replace(MARK, ""))
            continue
        a = A[who[sl]]
        ws = sorted(ws, key=lambda w: (not w[8], w[8] or 0))
        rows = ws[:ARTIST_CAP]
        kc = [sum(1 for w in ws if w[14] & bits) for bits, _, _ in KINDS]
        k = max(range(len(KINDS)), key=lambda j: kc[j])
        pr = [w[8] for w in ws if w[8]]
        life = a.get("l") or ["", ""]
        dates = f" ({life[0]}–{life[1]})" if life[0] or life[1] else ""
        gs = sorted({gals[w[9]] for w in ws if gals[w[9]]})
        L = sorted(lots.get(who[sl], []), key=lambda w: w["ad"], reverse=True)
        for lang in ("en", "et"):
            t, st, at = T[lang], ST[lang], AT[lang]
            ol = "et" if lang == "en" else "en"
            me, other = f"{BASE}/{SALE_DIR[lang]}/{sl}", f"{BASE}/{SALE_DIR[ol]}/{sl}"
            apage = f'{BASE}/{"a" if lang == "en" else "k"}/{sl}'
            kind = KINDS[k][1 if lang == "en" else 2] if kc[k] * 2 >= len(ws) else at["art"]
            rng = ("" if not pr else at["rng1"].format(lo=money(pr[0], lang)) if pr[0] == pr[-1] else
                   at["rng"].format(lo=money(pr[0], lang) if lang == "en" else f"{pr[0]:,}".replace(",", " "), hi=money(pr[-1], lang)))
            title, h = at["title"].format(name=name, kind=kind, n=len(ws), rng=rng), at["h"].format(name=name, kind=kind)
            lede = at["lede"].format(n=len(ws), name=name, dates=dates, gals=", ".join(gs), rng=rng)
            cards = "".join(
                f'<article class="card"><a class="out" href="{e(w[10])}" target="_blank" rel="noopener" data-out="{e(gals[w[9]])}">'
                f'<img src="{e(w[3])}" alt="{e(w[0])}, {e(name)}" loading="lazy" decoding="async" referrerpolicy="no-referrer-when-downgrade">'
                f'<span class="cap"><i>{e(w[0])}</i>{e(str(w[2])) if w[2] else ""}</span>'
                + (f'<span class="meta">{e(" · ".join(x for x in ((lang == "en" and w[15]) or w[4], w[5] if lang == "en" else re.sub(r"(?<=[0-9])[.](?=[0-9])", ",", w[5])) if x))}</span>' if (w[4] or w[5]) else "")
                + f'<span class="price"><b>{money(w[8], lang) if w[8] else e(t["noprice"])}</b> {e((t["at"] + " ") if t["at"] else "")}{e(gals[w[9]])} ↗</span></a></article>'
                for w in rows)
            auction = ""
            if L:
                sold = sorted(w["ap"] for w in L if w.get("ao") and w.get("ap"))
                lo, hi, q = arts[ai][5], arts[ai][6], arts[ai][7]
                ys = sorted(w["ad"][:4] for w in L)
                r = (at["aur" if q else "aur0"].format(lo=money(lo, lang) if lang == "en" else f"{lo:,}".replace(",", " "), hi=money(hi, lang))
                     if sold and lo != hi else "")
                res = lambda w: money(w["ap"], lang) if w.get("ao") and w.get("ap") else at["sold"] if w.get("ao") else at["unsold"]
                auction = (f'<section class="seo"><h2>{e(at["auh"].format(name=name))}</h2>'
                           f'<p>{e(at["au"].format(n=len(L), y=ys[0] if ys[0] == ys[-1] else f"{ys[0]}–{ys[-1]}", s=sum(1 for w in L if w.get("ao")), r=r))}</p>'
                           + "".join(f'<p><i>{e(w.get("t") or "—")}</i>{", " + e(str(w["y"])) if w.get("y") else ""}: '
                                     f'{e(H.val(w, "mu") or "")} {w["ad"][:4]}, {e(res(w))}</p>' for w in L[:8]) + "<!--prices-page--></section>")   # build_prices.py: the link to every result
            ld = H.ldjson({"@context": "https://schema.org", "@type": "CollectionPage", "name": h, "url": me, "inLanguage": lang,
                           "about": {"@type": "Person", "name": name, "url": apage},
                           "mainEntity": {"@type": "ItemList", "numberOfItems": len(ws), "itemListElement": [
                               {"@type": "ListItem", "position": j + 1, "item": H.offer_item(
                                   w[0], name, w[2], (lang == "en" and w[15]) or w[4], w[3], w[8], gals[w[9]], w[10])}
                               for j, w in enumerate(rows)]}})
            find = f'{BASE}/{t["file"]}#a={urllib.parse.quote(name)}'
            html_ = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                     f'<title>{e(title)} · museaal.ee</title><meta name="description" content="{e(lede[:290])}">'
                     f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{ol}" href="{other}">'
                     f'<link rel="alternate" type="application/rss+xml" title="{e(name)} — for sale" href="{BASE}/a/{sl}.xml">'
                     f'<script type="application/ld+json">{ld}</script>'
                     '<link rel="stylesheet" href="/fonts/fonts.css">'
                     f'<style>{CSS}</style>{H.GC}</head><body><div class="wrap">'
                     f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{e(t["site"])}</a> › <a href="{BASE}/{t["file"]}">{e(t["h"])}</a> › '
                     f'<a href="{apage}">{e(name)}</a> · <a href="{other}" hreflang="{ol}">{e(t["other_l"])}</a></nav>'
                     f'<header><h1>{e(h)}</h1><p class="lede">{e(lede)}</p><p><a class="btn solid" href="{e(find)}">{e(at["more"])}</a></p></header>'
                     f'<div class="grid">{cards}</div>'
                     + (f'<p class="m">{e(at["first"].format(k=len(rows), n=len(ws)))}</p>' if len(ws) > len(rows) else "")
                     + auction
                     + f'<section class="seo"><p><a href="{apage}">{e(at["page"].format(name=name))}</a> · <a href="{BASE}/a/{sl}.xml">{e(at["feed"])}</a></p></section>'
                     + browse_links(lang)
                     + f'<footer>{e(t["note"].split(". ")[0])}. {H.CONTACT[lang]}</footer></div>{H.out_js("forsale-artist")}</body></html>')
            open(f"site/{SALE_DIR[lang]}/{sl}.html", "w", encoding="utf-8").write(html_); urls.append(me)
            # and the way here from the artist's own page
            p = f'site/{"a" if lang == "en" else "k"}/{sl}.html'
            if os.path.exists(p):
                s = open(p, encoding="utf-8").read()
                if MARK in s:
                    open(p, "w", encoding="utf-8").write(s.replace(MARK, f'<p><a class="cta" href="{me}">{e(at["link"].format(n=len(ws)))}</a></p>'))
        n_pages += 1; made.append(sl)
    # the slugs with such a page, for the home page's "By artist" view to link each to its own (tpl_app.html fsaBit)
    json.dump(sorted(made), open("site/data/for-sale-artists.json", "w", encoding="utf-8"), separators=(",", ":"))
    print(f"  for sale       {n_pages:,} artists with a for-sale page of their own ({ARTIST_MIN} works or more), both languages")
    return urls

# a cell a spreadsheet would take for a formula gets an apostrophe in front (OWASP's CSV injection rule)
csv_cell = lambda v: "'" + v if isinstance(v, str) and re.match(r"\s*(?:[=@\t\r]|[+-].*[|(!])", v) else v

def feed(d):
    """/data/for-sale.csv: the stock with every value named, a row a work -- for a spreadsheet, a search engine or an
    agent, none of which can read stock.json's numbered fields. The works and asking prices Buy Art shows"""
    arts, gals, words = d["artists"], d["galleries"], d["words"]
    with open("site/data/for-sale.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["title", "artist", "year", "technique", "technique_en", "medium", "dimensions", "size", "price_eur",
                     "gallery", "url", "image", "moods", "artist_page"])
        for w in d["works"]:
            wr.writerow([csv_cell(v) for v in [w[0], arts[w[1]][0], w[2], w[4], w[15] or w[4], "; ".join(m for m in MEDIA if w[14] & BIT[m]),
                         w[5], w[6], w[8] or "", gals[w[9]], w[10], w[3], "; ".join(words[j] for j in w[12][::2]),
                         f"{BASE}/a/{arts[w[1]][1]}"]])

def llms_txt(d):
    """/llms.txt (llmstxt.org): what the site is and where its data lives, in plain words for a language model that
    reads it -- above all that the prices are the galleries' asking prices and a work is bought from the gallery"""
    M, W_ = H.META, d["works"]
    n = lambda x: f"{x:,}"
    sale = "\n".join(f"- [{s[3]}]({BASE}/{SALE_DIR['en']}/{s[2]})" for s in SALE)
    txt = f"""# museaal.ee — Estonian Art Catalogue

> A catalogue of Estonian art: {n(M["records"])} records of works by {n(M["artists"])} artists, from the museums' collections \
(MuIS and the Art Museum of Estonia's digital collection), the auction houses' published results, and the stock of \
{len(d["galleries"])} Estonian galleries — the works they have for sale now, with their asking prices. In English and Estonian.

museaal.ee is not a shop: every work for sale links to the gallery that sells it, and is bought there. Prices are the \
galleries' asking prices in euros, as their own pages state them, and the stock is read again every week; a work sold \
since may still be listed, and the gallery's page is the one to trust. Pictures stay on the museums' and galleries' own \
servers. Data as of {M["built"]}.

## Works for sale

- [All works for sale, CSV]({BASE}/data/for-sale.csv): {n(len(W_))} works by {n(len(d["artists"]))} artists at \
{len(d["galleries"])} galleries, {n(sum(1 for w in W_ if w[8]))} with a price. A row a work: title, artist, year, technique \
as the gallery states it and in English, medium, dimensions, size, asking price in euros, gallery, the gallery's page for \
the work, its picture, mood words read off the picture, the artist's page on museaal.ee
- [New for sale, RSS]({BASE}/feed.xml): the newest hundred works; each artist has a feed of their own beside their page, \
{BASE}/a/<artist>.xml
- [Buy Art]({BASE}/{T["en"]["file"]}): the same works, searched by price, medium, size and mood, or by describing what you \
are after ([in Estonian]({BASE}/{T["et"]["file"]}))
{sale}
- By artist: {BASE}/{SALE_DIR["en"]}/<artist> for every artist with {ARTIST_MIN} or more works for sale — the works, their \
asking prices and galleries, and the artist's results at auction (the same <artist> as in {BASE}/a/<artist>)

Each of these is in Estonian too, under {BASE}/{SALE_DIR["et"]}/.

## Artists

- [Artists A–Z]({BASE}/a/): a page for each artist — dates, biography, the museums that hold their work, works for \
sale, record at auction; in Estonian under {BASE}/k/

- Prices by artist: {BASE}/prices/<artist> for every artist with four or more published results at the Estonian \
auction houses — every lot with its sale and hammer price, and the figures by medium and by year; in Estonian under \
{BASE}/hinnad/. A record of what was published, not a valuation

## Data

- [Every record, CSV, gzip]({BASE}/data/export/works.csv.gz): a row a record, every value written out
- [Artists, CSV, gzip]({BASE}/data/export/artists.csv.gz)
- [The catalogue in figures]({BASE}/stats)

## Optional

- [Art by mood]({BASE}/mood): museum pictures by the mood words a visitor picks
- Corrections and questions: info@museaal.ee
"""
    open("site/llms.txt", "w", encoding="utf-8").write(txt)

def rss(d):
    """The new works for sale as RSS: /feed.xml, the newest hundred at every gallery, and /a/<artist>.xml beside every
    artist page, that artist's works for sale -- so a collector can follow a name in any feed reader, with no account and
    nothing kept about them. A work is dated by the day the weekly run first saw it (data/gallery_seen.json; works seen
    before days were kept carry the first of their month). Each item links to the gallery's page, as the cards do."""
    from xml.sax.saxutils import escape as x
    import email.utils
    arts, gals = d["artists"], d["galleries"]
    seen = json.load(open("data/gallery_seen.json", encoding="utf-8")) if os.path.exists("data/gallery_seen.json") else {}
    day = {"G" + re.sub(r"[^A-Za-z0-9]", "", g): e_.get("day") or e_["first"] + "-01" for g, e_ in seen.items()}
    when = lambda w: day.get(w[11], "2026-09-01")
    rfc = lambda s: email.utils.format_datetime(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc))
    def item(w, whose):
        a = arts[w[1]]
        price = f"€{w[8]:,}" if w[8] else "price on request"
        line = " · ".join(filter(None, [w[15] or w[4], w[5], price, gals[w[9]]]))
        desc = (f'<p><img src="{x(w[3], {chr(34): "&quot;"})}" alt=""></p><p>{x(line)}</p>'
                f'<p><a href="{BASE}/a/{a[1]}">{x(a[0])} on museaal.ee</a></p>')
        return (f"<item><title>{x((a[0] + ': ' if whose else '') + (w[0] or '—') + (f', {w[2]}' if w[2] else '') + ' — ' + price)}</title>"
                f"<link>{x(w[10])}</link><guid isPermaLink=\"false\">museaal.ee:{x(w[11])}</guid><pubDate>{rfc(when(w))}</pubDate>"
                f"<description>{x(desc)}</description></item>")
    def channel(path, title, link, about, ws, whose, cap):
        ws = sorted(ws, key=lambda w: (when(w), w[11]), reverse=True)[:cap]
        top = rfc(when(ws[0])) if ws else rfc(H.META["built"][:10])
        open(path, "w", encoding="utf-8").write(
            '<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            f"<title>{x(title)}</title><link>{x(link)}</link><description>{x(about)}</description><language>en</language>"
            f'<atom:link href="{BASE}/{path[5:]}" rel="self" type="application/rss+xml"/><lastBuildDate>{top}</lastBuildDate>'
            + "".join(item(w, whose) for w in ws) + "</channel></rss>\n")
    channel("site/feed.xml", "New for sale — museaal.ee", f"{BASE}/{T['en']['file']}",
            "Works by Estonian artists newly for sale at Estonian galleries, with their asking prices. Each links to the gallery that sells it.",
            d["works"], True, 100)
    by = collections.defaultdict(list)
    for w in d["works"]: by[arts[w[1]][1]].append(w)
    name = {sl: A[i]["n"] for i, sl in H.ARTIST_SLUG.items()}
    n = 0
    for f in os.listdir("site/a"):
        sl = f[:-5]
        if not f.endswith(".html") or sl == "index" or sl not in name: continue
        channel(f"site/a/{sl}.xml", f"{name[sl]} — for sale · museaal.ee", f"{BASE}/a/{sl}",
                f"Works by {name[sl]} for sale at Estonian galleries, newest first, with their asking prices.", by.get(sl, []), False, 50)
        n += 1
    print(f"  feeds          feed.xml, {n:,} artist feeds ({len(by):,} with works for sale)")

def taste_files(d):
    """For you's data (data/taste.py): the stock's 48 bytes a work in stock.json's order (zeros: no picture read yet),
    and, in 256 shards by key, every other work the register can list that has a museum picture or an artist with work
    for sale: [that artist in stock.json or -1, the picture's bytes or "", title, artist]. A page fetches only the shards
    its list's keys fall in. Returns the files' version."""
    ims, aidx = d.pop("_ims"), d.pop("_aidx")
    rd = lambda f: json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    TV, ST = rd("data/taste_vecs.json"), rd("data/stock_taste.json")
    blob = b"".join(base64.b64decode(ST[im]) if im in ST else bytes(48) for im in ims)
    stock = {w[11] for w in d["works"]}
    shards = collections.defaultdict(dict)
    for w in W:
        k = H.key(w)
        if not k or k in stock: continue
        v, a = TV.get(w.get("im") or "", ""), aidx.get(w["a"], -1)
        if not v and a < 0: continue
        h = 0
        for c in k: h = (h * 31 + ord(c)) & 0xFFFFFFFF              # as the page's shardOf
        shards[f"{h & 255:02x}"].setdefault(k, [a, v, (w.get("t") or "")[:80], A[w["a"]]["n"]])
    shutil.rmtree("site/data/taste", ignore_errors=True); os.makedirs("site/data/taste")
    sha = hashlib.sha1(blob)
    open("site/data/taste-stock.bin", "wb").write(blob)
    for h, x in sorted(shards.items()):
        b = json.dumps(x, ensure_ascii=False, separators=(",", ":"))
        open(f"site/data/taste/{h}.json", "w", encoding="utf-8").write(b); sha.update(b.encode())
    n = sum(len(x) for x in shards.values())
    print(f"  for you        {sum(1 for im in ims if im in ST):,} of {len(ims):,} works for sale with a picture read; {n:,} other works in {len(shards)} shards "
          f"(~{sum(len(json.dumps(x)) for x in shards.values()) // max(1, len(shards)) // 1024} KB each)")
    return sha.hexdigest()[:8]

def main():
    d = data()
    tver = taste_files(d)
    blob = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    ver = hashlib.sha1(blob.encode()).hexdigest()[:8]
    open("site/data/stock.json", "w", encoding="utf-8").write(blob)
    M = json.load(open("data/moods.json", encoding="utf-8"))["words"]
    urls = []
    for lang in ("en", "et"):
        labels = {w["en"]: (w["et"] if lang == "et" else BM.LABEL_EN.get(w["en"], w["en"])) for w in M}
        open(f"site/{T[lang]['file']}.html", "w", encoding="utf-8").write(page(lang, ver, API, labels, M, len(d["works"]), tver, door_names(d))); urls.append(f"{BASE}/{T[lang]['file']}")
    urls += sale_pages(d) + artist_sale_pages(d)
    feed(d); llms_txt(d); rss(d)
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    W_ = d["works"]
    print(f"  find a work    {len(W_):,} works for sale, {sum(1 for w in W_ if w[8]):,} with a price, {sum(1 for w in W_ if w[12]):,} with moods; "
          f"stock.json {len(blob) // 1024} KB, for-sale.csv, llms.txt; assistant {'at the Worker' if API else 'not set up'}")

if __name__ == "__main__":
    main()
