# -*- coding: utf-8 -*-
"""Find a work: /find.html and /leia.html, and the stock they read, /data/stock.json.

A visitor sets the controls -- a price range, the medium, the size, mood words -- or says
what they are looking for, and the page shows ten works the galleries have for sale now.
The assistant is Claude Haiku behind the mood page's Worker (its /ask door,
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
import build_mood as BM

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

T = {"en": dict(file="find.html", other="leia.html", other_l="Eesti keeles", site="Estonian Art Catalogue",
                h="Buy Art", title="Buy Estonian art: {n} works for sale, with prices", lede="Art for your home from the catalogue's galleries, for sale now. Set the price, medium, size, mood and artist, or describe what you need. Each work links to the gallery that sells it.",
                hello="Set the filters, or describe what you need: the room, size, budget, subject or mood.",
                photo="Photo of your wall", yourroom="Your room", looking="Looking at your room…", photomsg="(a photo of my room)",
                wallw="Wall space, width", drag="Drag the room to look around it; scroll or pinch to step closer. Drag a work to move it along the wall, or onto another outlined space. If the sizes look wrong, set the wall's width.", reset="Reset view", ar="See it on your wall (AR)", arsafari="To see a work on your real wall in AR, open this page in Safari.", arwait="Making the model…", arfail="AR could not be opened", onwall="On my wall",
                choose="Tap a work to hang it", hangmore="Hang another", remove="Take it down", together="{n} works on the wall",
                frames=dict(none="No frame", black="Black", oak="Oak", white="White", gold="Gold"),
                fits="fits", roomnote="Room", nowall="I couldn't find a clear stretch of wall in that photo. Try one taken straight on, with the empty wall in view.",
                badphoto="That photo could not be read. Try a JPEG or PNG.",
                label="Your message", ph="e.g. a misty landscape above the sofa, up to €2,000", send="Send",
                more="Show more", at="at", noprice="Price on request", none="No work for sale matches this search. Widen the price range or clear a filter.",
                thinking="Thinking…", how="How it searched", like="Works like", choosing="Choosing from these", failed="The assistant could not be reached. Try again in a moment.", record="In the catalogue",
                kinds=dict(paint="paintings", paper="works on paper", sculpture="sculpture", photo="photographs"),
                sizes=dict(small="small", medium="medium", large="large"), under="under", over="over", shown="Shown",
                media=dict(oil="Oil", acrylic="Acrylic", watercolour="Watercolour", mixed="Mixed media", print="Print", drawing="Drawing",
                           sculpture="Sculpture", photo="Photography", painting="Paintings, any medium"),
                price="Price", anyprice="Any price", upto="up to", from_="from", lowest="Lowest price", highest="Highest price",
                medium="Medium", size="Size", sizeany="Any", sizehint=dict(small="up to 40 cm", medium="40–100 cm", large="over 100 cm"),
                mood="Mood", moremoods="More words", fewer="Fewer", clear="Clear", count="{n} works", count1="1 work",
                artistonly="{who}: {n} for sale outside these settings.", showthem="Show them",
                daily="today's selection", fromchat="From the chat", artist="Artist", artistph="Type a name", artistlist="Artists with works for sale", names="Start with a name", titlew="In the title", filters="Filters",
                groups=dict(feeling="Feeling", light="Light", colour="Colour", weather="Season and weather", subject="Subject"),
                note="The works are the galleries' current stock with their asking prices, read weekly from each gallery's own site; the gallery's page is the one to trust. Your messages are read by Claude, which runs the searches and picks the works it suggests; they are not stored. The auction figures under a work are its artist's record as the houses published it, hammer prices: a record, not a valuation. The moods are read from the gallery's photograph by CLIP, an image model: a guide, not a judgement of the work.",
                sl_add="Add to my list", sl_remove="Remove from my list", fy="For you", fybtn="Based on My list ({n})",
                fyhint="Bookmark three works, here, on the mood wall or in the catalogue, and this puts first what looks like them.",
                fysee="See My list", fybit="based on My list", fylike="Like “{t}”, {a}, in My list",
                fynone="nothing in My list to go by yet",
                hash=""),
     "et": dict(file="leia.html", other="find.html", other_l="In English", site="Eesti Kunstikataloog",
                h="Osta kunsti", title="Osta Eesti kunsti: müügil {n} teost koos hindadega", lede="Kunst sinu koju kataloogi galeriidest, praegu müügil. Sea hind, tehnika, suurus, meeleolu ja kunstnik või kirjelda, mida vajad. Iga teos viib seda müüva galerii lehele.",
                hello="Sea filtrid või kirjelda, mida vajad: tuba, suurus, eelarve, teema või meeleolu.",
                photo="Foto seinast", yourroom="Sinu tuba", looking="Vaatan su tuba…", photomsg="(foto minu toast)",
                wallw="Vaba seinaosa laius", drag="Lohista tuba, et ringi vaadata; keri või näpista, et lähemale astuda. Lohista teost, et seda seinal liigutada või teisele märgitud kohale viia. Kui suurused tunduvad valed, sea seina laius õigeks.", reset="Algvaade", ar="Vaata oma seinal (AR)", arsafari="Et näha teost AR-is oma päris seinal, ava see leht Safaris.", arwait="Teen mudelit…", arfail="AR-i ei õnnestunud avada", onwall="Minu seinale",
                choose="Puuduta teost, et see seinale riputada", hangmore="Riputa veel üks", remove="Võta maha", together="Seinal {n} teost",
                frames=dict(none="Raamita", black="Must", oak="Tamm", white="Valge", gold="Kuld"),
                fits="mahub", roomnote="Tuba", nowall="Ma ei leidnud sellelt fotolt vaba seinaosa. Proovi fotot, mis on tehtud otse seina poole ja kus tühi sein on näha.",
                badphoto="Seda fotot ei õnnestunud lugeda. Proovi JPEG- või PNG-faili.",
                label="Sinu sõnum", ph="nt udune maastik diivani kohale, kuni 2000 €", send="Saada",
                more="Näita rohkem", at="", noprice="Hind päringul", none="Müügil pole ühtki teost, mis sellele otsingule vastaks. Laienda hinnavahemikku või eemalda mõni filter.",
                thinking="Mõtlen…", how="Kuidas otsisin", like="Sarnased teosele", choosing="Valin nende seast", failed="Abilist ei õnnestunud kätte saada. Proovi hetke pärast uuesti.", record="Kataloogis",
                kinds=dict(paint="maalid", paper="tööd paberil", sculpture="skulptuur", photo="fotod"),
                sizes=dict(small="väike", medium="keskmine", large="suur"), under="alla", over="üle", shown="Näidatud",
                media=dict(oil="Õli", acrylic="Akrüül", watercolour="Akvarell", mixed="Segatehnika", print="Graafika", drawing="Joonistus",
                           sculpture="Skulptuur", photo="Foto", painting="Maalid, iga tehnika"),
                price="Hind", anyprice="Iga hind", upto="kuni", from_="alates", lowest="Madalaim hind", highest="Kõrgeim hind",
                medium="Tehnika", size="Suurus", sizeany="Kõik", sizehint=dict(small="kuni 40 cm", medium="40–100 cm", large="üle 100 cm"),
                mood="Meeleolu", moremoods="Rohkem sõnu", fewer="Vähem", clear="Tühjenda", count="{n} teost", count1="1 teos",
                artistonly="{who}: väljaspool neid seadeid müügil {n}.", showthem="Näita",
                daily="tänane valik", fromchat="Vestlusest", artist="Kunstnik", artistph="Kirjuta nimi", artistlist="Kunstnikud, kelle teoseid on müügil", names="Alusta nimest", titlew="Pealkirjas", filters="Filtrid",
                groups=dict(feeling="Tunne", light="Valgus", colour="Värv", weather="Aastaaeg ja ilm", subject="Aine"),
                note="Teosed on galeriide praegune müügivalik ja nende küsitud hinnad, loetud iga nädal galeriide endi lehtedelt; usaldusväärne on galerii leht. Sinu sõnumeid loeb Claude, kes teeb otsingud ja valib soovitatavad teosed; neid ei salvestata. Teose all olevad oksjoniandmed on kunstniku tulemused nii, nagu oksjonimajad need avaldasid (haamrihinnad): ülevaade, mitte hinnang. Meeleolu loeb galerii fotolt pildimudel CLIP: see on juhatus, mitte hinnang teosele.",
                sl_add="Lisa minu nimekirja", sl_remove="Eemalda minu nimekirjast", fy="Sulle", fybtn="Minu nimekirja põhjal ({n})",
                fyhint="Märgi järjehoidjaga kolm teost, siin, meeleolu seinal või kataloogis, ja ette tulevad nendega sarnased.",
                fysee="Vaata minu nimekirja", fybit="minu nimekirja põhjal", fylike="Sarnane: „{t}“, {a}, minu nimekirjas",
                fynone="minu nimekirjas pole veel millegi järgi minna",
                hash="lang=et&")}

def data():
    # how many works the museums hold by each artist: the daily selection leans to names a visitor may know
    held = collections.Counter(w["a"] for w in W if (w.get("kind") or "held") in ("held", "shown"))
    # and their record at auction, as the houses published it: lots, sold, the lowest and highest hammer price
    lots = collections.defaultdict(list)
    for w in W:
        if w.get("kind") == "auction": lots[w["a"]].append(w)
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
        works.append([w.get("t") or "", aidx[a], w.get("y") or "", u, tech[:60], w.get("dm") or "",
                      size_of(w.get("dm")), kind_of(w), w.get("pr") or 0, gals[g], w["url"], k,
                      [x for j, z in S.get(w["im"], [])[:8] if z >= 1.0 for x in (j, round(z * 10))],   # word, z x 10, flat
                      dims_of(w.get("dm")) or 0,
                      media_of(kind_of(w), " ".join(filter(None, (H.val(w, "tce"), H.val(w, "tc"))))),
                      tech_en[:60] if tech_en != tech else ""])
        ims.append(w["im"])
    return {"words": words, "artists": arts, "galleries": list(gals), "works": works, "_ims": ims, "_aidx": aidx}

JS = r"""
(function(){
var T=JSON.parse(document.getElementById('t').textContent), page=document.getElementById('chat');
var EN=document.documentElement.lang==='en', api=page.dataset.api, src=page.dataset.src, log=document.getElementById('log'), form=document.getElementById('ask'), input=document.getElementById('q'), file=document.getElementById('photo');
// the A/B test of the assistant: each browser gets one version and keeps it -- 'a' looks with its tools first, 'o' answers
// in one call -- and the counts carry it; ?v=a or ?v=o picks one (the side-by-side comparison)
var V=(/[?&]v=([ao])(&|$)/.exec(location.search)||[])[1];
if(!V){try{V=localStorage.getItem('find-v')}catch(e){}if(V!=='a'&&V!=='o'){V=Math.random()<.5?'a':'o';try{localStorage.setItem('find-v',V)}catch(e){}}}
var talked=false, wentOut=false;
function gc(p,t){if(window.goatcounter&&goatcounter.count)goatcounter.count({path:p,title:t||p,event:true})}
var D=null, P=null, msgs=[], shownKeys={}, busy=false, labels=JSON.parse(document.getElementById('labels').textContent);
var R=null, rooms=[];                              // the room on view (the latest photo), and every one shown
function stock(){ return P=P||fetch(src).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(d){
  var af=d.af=d.artists.map(function(a){return fold(a[0])});
  d.fame=d.artists.map(function(a){return Math.min(1,Math.log10(1+(a[2]||0))/3.3)});   // ~2,000 works in the museums: 1
  d.byKey={};d.works.forEach(function(w,k){var m={},f=w[12];for(var i=0;i<f.length;i+=2)m[d.words[f[i]]]=f[i+1]/10;w.m=m;w.af=af[w[1]];w.i=k;d.byKey[w[11]]=w}); D=d; tally(); return d}).catch(function(e){P=null;throw e})}
function el(tag,cls,text){var x=document.createElement(tag);if(cls)x.className=cls;if(text!=null)x.textContent=text;return x}
function eur(n){return '€'+String(n).replace(/\B(?=(\d{3})+(?!\d))/g,' ')}
function cm(d){return d?Math.round(d[0])+(d[1]!==d[0]?' × '+Math.round(d[1]):'')+' cm':''}
function hash(s){var h=0;for(var i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))|0;return (h>>>0)/4294967296}
function bubble(who,text){var b=el('div','msg '+who);b.appendChild(el('p',null,text));log.appendChild(b);b.scrollIntoView({block:'nearest',behavior:'smooth'});return b}

// ---- perspective: the projective map between four points and four points ----
function solve(A,b){var n=b.length,i,r,c,f,t;
  for(i=0;i<n;i++){var p=i;for(r=i+1;r<n;r++)if(Math.abs(A[r][i])>Math.abs(A[p][i]))p=r;
    t=A[i];A[i]=A[p];A[p]=t;t=b[i];b[i]=b[p];b[p]=t;
    for(r=i+1;r<n;r++){f=A[r][i]/A[i][i];for(c=i;c<n;c++)A[r][c]-=f*A[i][c];b[r]-=f*b[i]}}
  var x=[];for(i=n-1;i>=0;i--){var s=b[i];for(c=i+1;c<n;c++)s-=A[i][c]*x[c];x[i]=s/A[i][i]}return x}
function homography(s,d){var A=[],b=[];for(var k=0;k<4;k++){var x=s[k][0],y=s[k][1],X=d[k][0],Y=d[k][1];
  A.push([x,y,1,0,0,0,-x*X,-y*X]);b.push(X);A.push([0,0,0,x,y,1,-x*Y,-y*Y]);b.push(Y)}return solve(A,b)}
function apply(H,p){var w=H[6]*p[0]+H[7]*p[1]+1;return [(H[0]*p[0]+H[1]*p[1]+H[2])/w,(H[3]*p[0]+H[4]*p[1]+H[5])/w]}
var SQ=[[0,0],[1,0],[1,1],[0,1]];

// ---- the room: the visitor's photo, the wall spaces found in it, and the works hung on it ----
// A hung work is laid out at PX pixels a centimetre -- frame, mat and picture at their real sizes -- and
// that rectangle is mapped onto the wall in the photo, so everything follows the wall's perspective.
var PX=10, FRAMES={none:0,black:2.5,oak:3,white:2.5,gold:5};
function inside(p,q){var c=false;for(var i=0,j=3;i<4;j=i++)if((q[i][1]>p[1])!==(q[j][1]>p[1])&&p[0]<(q[j][0]-q[i][0])*(p[1]-q[i][1])/(q[j][1]-q[i][1])+q[i][0])c=!c;return c}
// The visitor's viewpoint: a camera turned in place sees the photo warped by K R K^-1 -- exact for
// everything in it, so looking round needs no depth. The view stays zoomed in so no edge shows.
function mul(A,B){var C=[];for(var i=0;i<3;i++)for(var j=0;j<3;j++){C[i*3+j]=0;for(var k=0;k<3;k++)C[i*3+j]+=A[i*3+k]*B[k*3+j]}return C}
function viewH(r){var V=r.view,f=.8*Math.max(r.W,r.H),cx=r.W/2,cy=r.H/2,a=V.yaw,b=V.pitch,z=V.zoom;
  var K=[f,0,cx,0,f,cy,0,0,1],Ki=[1/f,0,-cx/f,0,1/f,-cy/f,0,0,1];
  var Ry=[Math.cos(a),0,Math.sin(a),0,1,0,-Math.sin(a),0,Math.cos(a)],Rx=[1,0,0,0,Math.cos(b),-Math.sin(b),0,Math.sin(b),Math.cos(b)];
  var M=mul([z,0,cx*(1-z),0,z,cy*(1-z),0,0,1],mul(K,mul(mul(Ry,Rx),Ki)));
  return [M[0]/M[8],M[1]/M[8],M[2]/M[8],M[3]/M[8],M[4]/M[8],M[5]/M[8],M[6]/M[8],M[7]/M[8]]}
function covers(r,H){var q=[[0,0],[r.W,0],[r.W,r.H],[0,r.H]].map(function(p){return apply(H,p)}),m=.01*r.W;   // with a margin: no sliver of the edge
  return [[-m,-m],[r.W+m,-m],[r.W+m,r.H+m],[-m,r.H+m]].every(function(p){return inside(p,q)})}
// turn or zoom the view, unless that would show past the photo's edge
function look(r,yaw,pitch,zoom){var o=r.view;r.view={yaw:yaw,pitch:pitch,zoom:Math.max(1.05,Math.min(3,zoom))};
  var H=viewH(r);if(!covers(r,H)){r.view=o;return false}r.VH=H;r.VHi=homography([[0,0],[r.W,0],[r.W,r.H],[0,r.H]].map(function(p){return apply(H,p)}),[[0,0],[r.W,0],[r.W,r.H],[0,r.H]]);
  var M=H;r.scene.style.transform='scale('+(r.stage.clientWidth/r.W)+') matrix3d('+[M[0],M[3],0,M[6],M[1],M[4],0,M[7],0,0,1,0,M[2],M[5],0,1].join(',')+')';return true}
function wallCm(r,i){var w=r.walls[i];return [w.w_cm*r.scale,w.h_cm*r.scale]}
// the picture to hang: the gallery's full one (NOBA's "_thumb" is a square crop of the work)
function full(w){return w[3].replace(/_thumb(\.\w+)$/,'$1')}
// the work's shape: the picture's, unless it disagrees with the record by over a quarter -- a crop or a
// photograph with room round it -- when the record's sides win and the picture is cropped to them
function shape(w,n){var d=w[13],k=n.naturalHeight/n.naturalWidth,land=k<=1,rec=d[1]/d[0],img=land?k:1/k;
  var fit=Math.abs(Math.log(img/rec))<=Math.log(1.25);if(!fit)k=land?rec:1/rec;
  return {aw:land?d[0]:d[0]/k,ah:land?d[0]*k:d[0],crop:!fit}}
// outer size in cm: the work, then mat and frame
function size(it){var sh=shape(it.w,it.pic),aw=sh.aw,ah=sh.ah,f=FRAMES[it.frame], m=f&&it.w[7]==='paper'?Math.max(4,Math.min(9,Math.max(aw,ah)*.12)):0;
  return {f:f,m:m,W:aw+2*(m+f),H:ah+2*(m+f)}}
// the work's four corners in the photo; dx, dy move it on the wall, in cm (its shadow)
function quadOf(r,it,s,dx,dy){var c=wallCm(r,it.wall),H=r.walls[it.wall].H,fw=s.W/c[0],fh=s.H/c[1],u=it.u+(dx||0)/c[0],v=it.v+(dy||0)/c[1];
  return [[u-fw/2,v-fh/2],[u+fw/2,v-fh/2],[u+fw/2,v+fh/2],[u-fw/2,v+fh/2]].map(function(p){return apply(H,p)})}
function m3d(e,w,h,q){var M=homography([[0,0],[w,0],[w,h],[0,h]],q);e.style.width=w+'px';e.style.height=h+'px';
  e.style.transform='matrix3d('+[M[0],M[3],0,M[6],M[1],M[4],0,M[7],0,0,1,0,M[2],M[5],0,1].join(',')+')'}
function inPhoto(r,q){return q.every(function(p){return p[0]>=-4&&p[1]>=-4&&p[0]<=r.W+4&&p[1]<=r.H+4})}
function layout(r,it){if(!it.pic.naturalWidth)return;var s=size(it);
  it.el.className='hang f-'+it.frame+(it===r.sel&&r.items.length>1?' sel':'')+(shape(it.w,it.pic).crop?' crop':'');
  it.el.style.setProperty('--f',s.f*PX+'px');it.el.style.setProperty('--m',s.m*PX+'px');
  m3d(it.el,s.W*PX,s.H*PX,quadOf(r,it,s));m3d(it.shade,s.W*PX,s.H*PX,quadOf(r,it,s,1.2,2.5));
  it.el.hidden=it.shade.hidden=false}
function draw(r){
  look(r,r.view.yaw,r.view.pitch,r.view.zoom);
  r.polys.forEach(function(p,i){p.setAttribute('points',r.walls[i].q.map(function(x){return x.join(',')}).join(' '))});
  var cur=r.sel?r.sel.wall:0;r.range.value=Math.round(wallCm(r,cur)[0]);r.out.textContent=r.range.value+' cm';
  r.items.forEach(function(it){layout(r,it)});caption(r)}
function caption(r){
  var c=r.cap,it=r.sel;c.textContent='';
  r.strip&&Array.prototype.forEach.call(r.strip.children,function(b){if(b.w){b.setAttribute('aria-pressed',String(!!it&&b.w===it.w));b.classList.toggle('hung',r.items.some(function(x){return x.w===b.w}))}});
  Array.prototype.forEach.call(r.frames.children,function(b){b.setAttribute('aria-pressed',String(!!it&&b.dataset.f===it.frame))});
  if(!it)return;var w=it.w,g=D.galleries[w[9]],p=el('p','placed');
  p.appendChild(el('i',null,w[0]));p.appendChild(document.createTextNode(', '+D.artists[w[1]][0]+' · '+cm(w[13])+' · '));
  var l=el('a',null,(w[8]?eur(w[8]):T.noprice)+' '+(T.at?T.at+' ':'')+g+' ↗');l.href=w[10];l.target='_blank';l.rel='noopener';
  l.addEventListener('click',function(){if(window.goatcounter&&goatcounter.count)goatcounter.count({path:'find-out',title:g,event:true})});
  p.appendChild(l);c.appendChild(p);
  r.arSlot.textContent='';
  if(AR&&w[13]){var ab=arButton(w,function(){return it.frame});ab.classList.add('arbig');r.arSlot.appendChild(ab)}
  else if(IOS&&page.dataset.img)r.arSlot.appendChild(el('p','arhint',T.arsafari));
  if(r.items.length>1){
    var sum=r.items.reduce(function(a,x){return a+(x.w[8]||0)},0),all=r.items.every(function(x){return x.w[8]});
    c.appendChild(el('p','total',T.together.replace('{n}',r.items.length)+(all?' · '+eur(sum):'')));
    var x=el('button','btn',T.remove);x.type='button';x.addEventListener('click',function(){takeDown(r,it)});c.appendChild(x)}}
function select(r,it){r.sel=it;draw(r)}
function takeDown(r,it){r.items.splice(r.items.indexOf(it),1);it.el.remove();it.shade.remove();r.sel=r.items[r.items.length-1]||null;draw(r)}
function photoPt(r,e){var b=r.stage.getBoundingClientRect(),k=b.width/r.W;return apply(r.VHi,[(e.clientX-b.left)/k,(e.clientY-b.top)/k])}
// hang a work: in place of the selected one, or (add) as another, beside those already on the wall
function hang(r,w,add){
  if(!w||!w[13])return;
  var it=!add&&r.sel, fresh=!it;
  if(fresh){
    it={wall:r.sel?r.sel.wall:0,u:.5,v:.5,frame:r.sel?r.sel.frame:'black'};
    it.el=el('div','hang');var fr=el('div','fr'),mat=el('div','mat');it.pic=el('img');it.pic.draggable=false;it.pic.referrerPolicy='no-referrer-when-downgrade';
    mat.appendChild(it.pic);fr.appendChild(mat);it.el.appendChild(fr);it.shade=el('div','shade');it.el.hidden=it.shade.hidden=true;
    r.shades.appendChild(it.shade);r.hangs.appendChild(it.el);r.items.push(it);
    // dragged, it slides along the wall in perspective, and onto another wall area when the pointer reaches one
    it.el.addEventListener('pointerdown',function(e){e.preventDefault();e.stopPropagation();try{it.el.setPointerCapture(e.pointerId)}catch(x){}
      var uv=apply(r.walls[it.wall].Hi,photoPt(r,e));it.drag=[it.u-uv[0],it.v-uv[1]];if(r.sel!==it)select(r,it)});
    it.el.addEventListener('pointermove',function(e){if(!it.drag)return;var p=photoPt(r,e);
      for(var i=0;i<r.walls.length;i++)if(i!==it.wall&&inside(p,r.walls[i].q)){it.wall=i;it.drag=[0,0];break}
      var uv=apply(r.walls[it.wall].Hi,p),u=it.u,v=it.v;it.u=uv[0]+it.drag[0];it.v=uv[1]+it.drag[1];
      if(!inPhoto(r,quadOf(r,it,size(it)))){it.u=u;it.v=v}layout(r,it)});
    it.el.addEventListener('pointerup',function(){it.drag=null;draw(r)});it.el.addEventListener('pointercancel',function(){it.drag=null});
  }
  it.w=w;it.pic.alt=w[0]+', '+D.artists[w[1]][0];r.sel=it;
  it.pic.onload=function(){
    if(fresh&&r.items.length>1){
      // a row, centred in the empty area, when the works fit in it side by side
      var c=wallCm(r,it.wall),row=r.items.filter(function(x){return x.wall===it.wall&&x.pic.naturalWidth}).sort(function(a,b){return a===it?1:b===it?-1:a.u-b.u});
      var ws=row.map(function(x){return size(x).W/c[0]}),g=12/c[0],tot=ws.reduce(function(a,b){return a+b},0)+g*(row.length-1);
      if(tot<=.98&&row.length>1){var x0=.5-tot/2,v=row[0].v;row.forEach(function(o,i){o.u=x0+ws[i]/2;o.v=v;x0+=ws[i]+g});draw(r);return}
      // else beside the rightmost on its wall, else the leftmost, else a little off the centre
      var s=size(it),others=r.items.filter(function(x){return x!==it&&x.wall===it.wall&&x.pic.naturalWidth});
      var ext=others.map(function(x){var o=size(x);return [x.u-o.W/c[0]/2,x.u+o.W/c[0]/2]}), gap=12/c[0], half=s.W/c[0]/2;
      var right=Math.max.apply(null,ext.map(function(e){return e[1]}).concat([-1])), left=Math.min.apply(null,ext.map(function(e){return e[0]}).concat([2]));
      var cands=[right+gap+half,left-gap-half,it.u+.08];
      for(var i=0;i<cands.length;i++){it.u=cands[i];if(inPhoto(r,quadOf(r,it,s)))break}}
    draw(r)};
  it.pic.src=full(w);draw(r)}
// the suggestions under the photo: tap one to put it on the wall
function fill(r,list){
  r.list=list.filter(function(w){return w[13]});r.n=0;r.strip.textContent='';
  function more(){r.list.slice(r.n,r.n+12).forEach(function(w){
      var b=el('button');b.type='button';b.w=w;var i=el('img');i.src=w[3];i.alt=w[0];i.loading='lazy';i.referrerPolicy='no-referrer-when-downgrade';
      b.appendChild(i);b.appendChild(el('span',null,w[8]?eur(w[8]):cm(w[13])));b.title=w[0]+', '+D.artists[w[1]][0]+' · '+cm(w[13]);
      b.addEventListener('click',function(){hang(r,w)});r.strip.insertBefore(b,r.moreBtn)});
    r.n+=12;r.moreBtn.hidden=r.n>=r.list.length;caption(r)}
  r.moreBtn=el('button','more',T.more);r.moreBtn.type='button';r.moreBtn.addEventListener('click',more);r.strip.appendChild(r.moreBtn);more()}
function roomView(b,photo,walls){
  var r={W:photo.w,H:photo.h,walls:walls,scale:1,items:[],sel:null,polys:[],view:{yaw:0,pitch:0,zoom:1.2}},NS='http://www.w3.org/2000/svg';
  walls.forEach(function(w){w.H=homography(SQ,w.q);w.Hi=homography(w.q,SQ)});
  var v=el('div','room'),st=el('div','stage'),ph=el('img','photo');ph.src=photo.url;ph.alt=T.yourroom;ph.onload=function(){draw(r)};
  var svg=document.createElementNS(NS,'svg');svg.setAttribute('viewBox','0 0 '+r.W+' '+r.H);svg.setAttribute('preserveAspectRatio','none');svg.setAttribute('class','outline');
  walls.forEach(function(){var p=document.createElementNS(NS,'polygon');svg.appendChild(p);r.polys.push(p)});
  r.layer=el('div','layer');r.shades=el('div');r.hangs=el('div');r.layer.appendChild(r.shades);r.layer.appendChild(r.hangs);
  r.scene=el('div','scene');r.scene.style.width=r.W+'px';r.scene.style.height=r.H+'px';ph.style.width=r.W+'px';ph.style.height=r.H+'px';
  r.scene.appendChild(ph);r.scene.appendChild(svg);r.scene.appendChild(r.layer);st.appendChild(r.scene);st.style.aspectRatio=r.W+' / '+r.H;
  r.stage=st;v.appendChild(st);
  // drag the room to look round it; scroll, or pinch with two fingers, to step closer
  var pts={},turn=null,pinch=null;
  st.addEventListener('pointerdown',function(e){if(e.target.closest('.hang'))return;e.preventDefault();try{st.setPointerCapture(e.pointerId)}catch(x){}pts[e.pointerId]=[e.clientX,e.clientY];
    var ids=Object.keys(pts);if(ids.length===2){var a=pts[ids[0]],b=pts[ids[1]];pinch={d:Math.hypot(a[0]-b[0],a[1]-b[1]),z:r.view.zoom};turn=null}
    else turn={x:e.clientX,y:e.clientY,yaw:r.view.yaw,pitch:r.view.pitch};st.classList.add('turning')});
  st.addEventListener('pointermove',function(e){if(!pts[e.pointerId])return;pts[e.pointerId]=[e.clientX,e.clientY];var ids=Object.keys(pts),w=st.clientWidth;
    if(pinch&&ids.length===2){var a=pts[ids[0]],b=pts[ids[1]];look(r,r.view.yaw,r.view.pitch,pinch.z*Math.hypot(a[0]-b[0],a[1]-b[1])/pinch.d);return}
    // the point grabbed stays under the finger: an angle of (distance / focal length), in screen pixels
    if(turn){var s=1/(.8*Math.max(r.W,r.H)*(w/r.W)*r.view.zoom),y=turn.yaw+(e.clientX-turn.x)*s,p=turn.pitch-(e.clientY-turn.y)*s,z=r.view.zoom;
      if(!look(r,y,p,z)&&!look(r,y,r.view.pitch,z))look(r,r.view.yaw,p,z)}});
  function up(e){delete pts[e.pointerId];if(Object.keys(pts).length<2)pinch=null;if(!Object.keys(pts).length){turn=null;st.classList.remove('turning')}}
  st.addEventListener('pointerup',up);st.addEventListener('pointercancel',up);
  st.addEventListener('wheel',function(e){e.preventDefault();look(r,r.view.yaw,r.view.pitch,r.view.zoom*Math.exp(-e.deltaY*.0015))},{passive:false});
  r.arSlot=el('div','arslot');v.appendChild(r.arSlot);
  r.strip=el('div','strip');v.appendChild(el('p','hint',T.choose));v.appendChild(r.strip);
  var tools=el('div','tools');
  r.frames=el('div','seg');Object.keys(FRAMES).forEach(function(f){var x=el('button','btn',T.frames[f]);x.type='button';x.dataset.f=f;
    x.addEventListener('click',function(){if(r.sel){r.sel.frame=f;draw(r)}});r.frames.appendChild(x)});
  tools.appendChild(r.frames);
  var add=el('button','btn',T.hangmore);add.type='button';
  add.addEventListener('click',function(){var w=(r.list||[]).filter(function(x){return !r.items.some(function(i){return i.w===x})})[0];hang(r,w,true)});
  tools.appendChild(add);
  var reset=el('button','btn',T.reset);reset.type='button';reset.addEventListener('click',function(){r.view={yaw:0,pitch:0,zoom:1.2};draw(r)});tools.appendChild(reset);
  // the width is an estimate from the photo: the visitor can set it right, and every size follows
  var lab=el('label','width');lab.appendChild(document.createTextNode(T.wallw+' '));
  r.range=el('input');r.range.type='range';r.range.min=30;r.range.max=600;r.range.step=5;
  r.range.addEventListener('input',function(){r.scale=r.range.value/r.walls[r.sel?r.sel.wall:0].w_cm;draw(r)});
  r.out=el('output');lab.appendChild(r.range);lab.appendChild(r.out);tools.appendChild(lab);
  v.appendChild(tools);v.appendChild(el('p','hint',T.drag));r.cap=el('div','caption');v.appendChild(r.cap);
  b.appendChild(v);r.v=v;rooms.push(r);draw(r);return r}
window.addEventListener('resize',function(){rooms.forEach(draw)});

// ---- AR: the work as a small 3D model at its real size, for the phone's own AR viewer to hang on a real wall ----
// iPhone and iPad: AR Quick Look takes a USDZ file (three.js writes it here, in the browser) anchored to a wall,
// at true scale (no pinching it bigger). The picture's pixels must be readable, so it comes through the
// page's own origin (data-img), fetched as asked for, never kept. Built only when tapped.
var IOS=/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
// only where the picture can come through this origin (data-img): on the published site, without that route and with
// three.js outside the Content-Security-Policy, the button could only fail
var ARDEBUG=/ardebug/.test(location.hash), AR=ARDEBUG||!!page.dataset.img&&(function(){var a=document.createElement('a');return !!(a.relList&&a.relList.supports&&a.relList.supports('ar'))})();
function viaUs(u){return page.dataset.img?page.dataset.img+encodeURIComponent(u):u}
function loadImg(u){return new Promise(function(ok,no){var i=new Image();i.crossOrigin='anonymous';i.onload=function(){ok(i)};i.onerror=no;i.src=u})}
var FRAME_COL={black:[0x161616,.55,0],oak:[0xb88a52,.7,0],white:[0xf0eee8,.6,0],gold:[0xc9a13b,.35,.7]};
function usdz(w,frame){
  return Promise.all([import('three'),import('three/addons/exporters/USDZExporter.js'),loadImg(viaUs(full(w)))]).then(function(m){
    var THREE=m[0],img=m[2],sh=shape(w,img);
    var aw=sh.aw/100,ah=sh.ah/100,f=FRAMES[frame]/100,mt=f&&w[7]==='paper'?Math.max(.04,Math.min(.09,Math.max(aw,ah)*.12)):0,D=.03;
    var g=new THREE.Group(),mesh=function(geo,mat,x,y,z){var o=new THREE.Mesh(geo,mat);o.position.set(x,y,z);g.add(o);return o};
    // a picture cropped to the record's shape is cut on a canvas (the exporter writes no texture offsets)
    var src=img;if(sh.crop){var iw=img.naturalWidth,ih=img.naturalHeight,rw=aw/ah,cw=Math.min(iw,ih*rw),ch=cw/rw;
      src=document.createElement('canvas');src.width=Math.round(cw);src.height=Math.round(ch);src.getContext('2d').drawImage(img,(iw-cw)/2,(ih-ch)/2,cw,ch,0,0,src.width,src.height)}
    var tex=new THREE.Texture(src);tex.colorSpace=THREE.SRGBColorSpace;tex.needsUpdate=true;tex.userData.mimeType='image/jpeg';   // a photograph: JPEG, not a 9 MB PNG
    // the picture on both faces of a board (the mat, or a canvas's own edge): AR Quick Look turns the side
    // it calls the back towards the room when it hangs a model on a wall (seen 2026-10-01), and a model
    // with no front and back looks right whichever way it is hung
    var pm=new THREE.MeshStandardMaterial({map:tex,roughness:.9,metalness:0});
    mesh(new THREE.PlaneGeometry(aw,ah),pm,0,0,D/2+.0015);
    mesh(new THREE.PlaneGeometry(aw,ah),pm,0,0,-D/2-.0015).rotation.y=Math.PI;
    mesh(new THREE.BoxGeometry(aw+2*mt,ah+2*mt,D),new THREE.MeshStandardMaterial({color:mt?0xf5f2ea:0xe8e4dc,roughness:.95}),0,0,0);
    if(f){var c=FRAME_COL[frame],fm=new THREE.MeshStandardMaterial({color:c[0],roughness:c[1],metalness:c[2]}),W=aw+2*(mt+f),H=ah+2*(mt+f),Df=D+.012;
      mesh(new THREE.BoxGeometry(W,f,Df),fm,0,(H-f)/2,0);mesh(new THREE.BoxGeometry(W,f,Df),fm,0,-(H-f)/2,0);
      mesh(new THREE.BoxGeometry(f,H-2*f,Df),fm,-(W-f)/2,0,0);mesh(new THREE.BoxGeometry(f,H-2*f,Df),fm,(W-f)/2,0,0)}
    // AR Quick Look hangs a model with its up axis (+y) out of the wall -- the first try stood out from
    // the wall like a shelf (2026-10-01) -- so the work is tipped back to face +y, its top along -z (up the wall)
    g.rotation.x=-Math.PI/2;
    var scene=new THREE.Scene();scene.add(g);scene.updateMatrixWorld(true);   // the exporter writes each part's .matrix, set only by this
    return new m[1].USDZExporter().parseAsync(scene,{ar:{anchoring:{type:'plane'},planeAnchoring:{alignment:'vertical'}},quickLookCompatible:true,maxTextureSize:2048})})
  .then(function(buf){return new Blob([buf],{type:'model/vnd.usdz+zip'})})}
function arButton(w,frameOf){
  var b=el('button','btn arbtn',T.ar);b.type='button';
  b.addEventListener('click',function(){if(b.disabled)return;b.disabled=true;b.textContent=T.arwait;
    usdz(w,frameOf()).then(function(blob){
      if(ARDEBUG){return fetch('/save',{method:'POST',body:blob}).then(function(){b.textContent='saved '+blob.size})}
      var a=document.createElement('a');a.rel='ar';a.href=URL.createObjectURL(blob)+'#allowsContentScaling=0';a.appendChild(document.createElement('img'));
      document.body.appendChild(a);a.click();setTimeout(function(){a.remove()},1000);b.textContent=T.ar;
      if(window.goatcounter&&goatcounter.count)goatcounter.count({path:'find-ar',title:D.galleries[w[9]],event:true})})
    .catch(function(){b.textContent=T.arfail}).then(function(){b.disabled=false})});
  return b}

// ---- the search: one state, which the controls show and set, and the assistant reads and sets ----
function blank(){return {words:[],terms:[],media:[],min:0,max:0,size:'any',artist:'',you:false}}
var DAY=new Date().toISOString().slice(0,10);
var Q=blank(), MB={};             // each medium's bit in a work's field 14, from the page (build_ask.py BIT)
function fold(s){return s.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase()}
// a name as typed, in any case form: 'leisi' or 'leisilt' finds Malle Leis
function hitName(af,x){return af.indexOf(x)>=0||af.split(' ').some(function(n){return n.length>=3&&x.indexOf(n)===0&&x.length-n.length<=3})}
function esc(s){return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
// every work the search admits, best first; a search that names something (words, title words) admits only what answers to it
function rank(q){
  var wt=[1,.8,.65,.5,.4], out=[], ws=R&&wallCm(R,R.sel?R.sel.wall:0), mm=0, ty=q.you&&TASTE&&TASTE.n?TASTE:null;
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
    if(ws){                                       // a wall on view: what fits it, best near half its width
      var d=w[13];if(!d||w[7]==='sculpture'||w[14]&4)return;
      if(!((d[0]<=.9*ws[0]&&d[1]<=.9*ws[1])||(d[1]<=.9*ws[0]&&d[0]<=.9*ws[1])))return;
      var share=d[0]/Math.max(ws[0],ws[1]);if(share<.25)return;   // a postcard on a big wall: not a suggestion
      s+=2.5*(1-2*Math.abs(share-.5));
    }else{
      if(q.size!=='any'&&w[6]&&w[6]!==q.size)return;
      if(q.size!=='any'&&!w[6])s-=50;             // size unknown: only after every one that fits
    }
    out.push([s,w])});
  out.sort(function(a,b){return b[0]-a[0]});
  // one work per artist in each row of ten, as far as the list allows
  var picked=[],per={},rest=[];
  out.forEach(function(p){var a=p[1][1];if(per[a]>=Math.floor(picked.length/10)+1){rest.push(p[1]);return}per[a]=(per[a]||0)+1;picked.push(p[1])});
  return picked.concat(rest)}
function count(n){return n===1?T.count1:T.count.replace('{n}',String(n).replace(/\B(?=(\d{3})+(?!\d))/g,' '))}
function priceText(lo,hi){return lo&&hi?eur(lo)+' – '+eur(hi):hi?T.upto+' '+eur(hi):lo?T.from_+' '+eur(lo):T.anyprice}
// ---- For you: the works for sale ranked by My list (data/taste.py) ----
// The list is the only taste the page knows: read from this browser, never sent. A work for sale scores by its picture's
// nearness to the nearest picture on the list (and a little to the next), 48 bytes a picture in one space for museum
// and stock, and by its artist being on the list; its card says which. The stock's bytes are one file, fetched the
// first time For you is on; the list's other works come from a shard each, by key (build_ask.py taste_files).
var TS=page.dataset.taste, TSH=page.dataset.tshard, TSV=page.dataset.tver, NV=48, SV=null, TASTE=null, tasteP=null, SHARDS={};
var fyb=document.getElementById('foryou'), fyh=document.getElementById('fyhint');
function listNow(){return slGet().slice(-60)}       // the latest sixty
function tasteFresh(){return !!TASTE&&TASTE.sig===listNow().join(',')}
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
    var vs=items.filter(function(it){return it.v}), n=D.works.length, s=new Float32Array(n), why=[], max=0;
    // each kept picture ranks every work for sale by nearness, and a work scores by its place, 1/(10 + place): the
    // kept works take turns at the top. By nearness itself one gallery photograph on the list outweighed two museum
    // scans (photographs are nearer photographs), and as z-scores the scans outweighed it
    vs.forEach(function(it){var c=new Float32Array(n),o=[],r=it.r=new Float32Array(n),i,d,x;
      for(i=0;i<n;i++){o.push(i);if(!SV[i]){c[i]=-9;continue}x=0;for(d=0;d<NV;d++)x+=SV[i][d]*it.v[d];c[i]=x}
      o.sort(function(a,b){return c[b]-c[a]});for(i=0;i<n;i++)r[o[i]]=SV[o[i]]?1/(10+i):0});
    D.works.forEach(function(w,i){if(inl[w[11]])return;var b1=0,b2=0,bj=null,sc;
      vs.forEach(function(it){var c=it.r[i];if(c>b1){b2=b1;b1=c;bj=it}else if(c>b2)b2=c});
      sc=b1+.3*b2;
      if(arts[w[1]])sc+=.055;   // as a kept work's fourth nearest; no reason line, the card names the artist
      else if(bj)why[i]=T.fylike.replace('{t}',bj.t).replace('{a}',bj.an);
      s[i]=sc;if(sc>max)max=sc});
    if(max)for(var i=0;i<n;i++)s[i]/=max;
    TASTE={sig:keys.join(','),s:s,why:why,in:inl,n:max?items.length:0};return TASTE})}
// On by default from three works on the list, unless this browser turned it off (find-fy: off); the stock's bytes
// are fetched at once, beside stock.json, so the first ten wait for little more than the ranking. Default use counts
// apart from chosen: find-foryou-auto, find-foryou, find-foryou-off.
var TSB=null, fyAuto=false;
function tasteBin(){return TSB=TSB||fetch(TS).then(function(r){if(!r.ok)throw 0;return r.arrayBuffer()}).catch(function(e){TSB=null;throw e})}
function fyOff(){try{return localStorage.getItem('find-fy')==='off'}catch(e){return false}}
function fyKeep(on){try{if(on)localStorage.removeItem('find-fy');else localStorage.setItem('find-fy','off')}catch(e){}}
function fyDefault(){return slGet().length>=3&&!fyOff()}
if(fyDefault()){Q.you=fyAuto=true;tasteBin().catch(function(){})}
// the control: how many are on the list, on from three; under three, how to begin; and the way to the list itself
function syncYou(){var n=slGet().length;fyb.textContent=T.fybtn.replace('{n}',n);fyb.disabled=n<3&&!Q.you;fyb.setAttribute('aria-pressed',String(!!Q.you));
  fyh.textContent=n<3?T.fyhint+' ':'';if(n){var a=el('a',null,T.fysee);a.href='./#'+T.hash+'list=mine';fyh.appendChild(a)}fyh.hidden=!fyh.firstChild}
// ---- the assistant's tools: Claude asks (through the Worker), the page answers from the stock it has ----
function wid(w){return 'w'+w.i}
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
function card(w,why,fy){
  var a=D.artists[w[1]], g=D.galleries[w[9]], c=el('article','card');
  // the picture and title, and the price, go to the gallery; the artist's name to the work in the catalogue
  function out(){var o=el('a','out');o.href=w[10];o.target='_blank';o.rel='noopener';
    // every click out by gallery; and per version: conversations that led to a click out, and clicks on a pick
    o.addEventListener('click',function(){gc('find-out',g);if(talked&&!wentOut){wentOut=true;gc('find-conv-out-'+V)}if(why)gc('find-pick-'+V);if(Q.you)gc('find-foryou-out')});return o}
  var top=out(), img=el('img');img.src=w[3];img.alt=w[0]+', '+a[0];img.loading='lazy';img.decoding='async';img.referrerPolicy='no-referrer-when-downgrade';top.appendChild(img);
  var cap=el('span','cap');cap.appendChild(el('i',null,w[0]));top.appendChild(cap);c.appendChild(top);
  var by=el('span','by'), an=el('a',null,a[0]);an.href='./#'+T.hash+'artist='+a[1]+'&open='+encodeURIComponent(w[11]);an.title=T.record;
  by.appendChild(an);if(w[2])by.appendChild(document.createTextNode(', '+w[2]));c.appendChild(by);
  var low=out(), meta=[tech(w),w[5]].filter(Boolean).join(' · ');if(meta)low.appendChild(el('span','meta',meta));
  var pr=el('span','price');pr.appendChild(el('b',null,w[8]?eur(w[8]):T.noprice));pr.appendChild(document.createTextNode(' '+(T.at?T.at+' ':'')+g+' ↗'));low.appendChild(pr);
  c.appendChild(low);
  if(why)c.appendChild(el('p','why',why));
  if(fy)c.appendChild(el('p','fy',fy));
  if(R&&w[13]){var r=R,on=el('button','btn onwall',T.onwall);on.type='button';
    on.addEventListener('click',function(){hang(r,w);r.v.scrollIntoView({block:'center',behavior:'smooth'})});c.appendChild(on)}
  if(AR&&w[13])c.appendChild(arButton(w,function(){return R&&R.sel?R.sel.frame:'black'}));
  c.appendChild(slBtn(w[11],T,'list-add-find',syncYou));
  return c}
// the search's results into box: what it was, how many answer to it, and ten at a time, leaving out works an
// earlier turn showed
function show(box,q,picks){
  var ty=q.you&&TASTE&&TASTE.n?TASTE:null, why={}, pk=(picks||[]).map(function(p){var w=byId(p.id);if(w)why[w.i]=p.why;return w}).filter(Boolean);
  var all=rank(q), list=pk.concat(all.filter(function(w){return !shownKeys[w[11]]&&!(w.i in why)})), n=0, keys=[], grid=el('div','grid'), more=el('button','btn more',T.more);more.type='button';
  var bits=[count(all.length)].concat(q.media.map(function(m){return T.media[m]}));
  if(R){var ws=wallCm(R,R.sel?R.sel.wall:0);bits.push(T.fits+' '+Math.round(ws[0])+' × '+Math.round(ws[1])+' cm')}else if(q.size!=='any')bits.push(T.sizes[q.size]);
  if(q.min||q.max)bits.push(priceText(q.min,q.max));
  bits=bits.concat(q.words.map(function(x){return labels[x]||x}));
  if(q.terms.length)bits.push(T.titlew+': '+q.terms.join(', '));
  if(q.you)bits.push(ty?T.fybit:T.fynone);
  if(bits.length===1&&!q.artist)bits.push(T.daily);
  if(q.artist)bits.push(q.artist);
  box.appendChild(el('p','search',bits.join(' · ')));
  if(!list.length){box.appendChild(el('p','none',T.none));
    // an artist with works for sale outside the other settings: say how many, and offer them
    var solo=blank();solo.artist=q.artist;var k=q.artist&&(q.media.length||q.min||q.max||q.size!=='any'||q.words.length||q.terms.length)?rank(solo).length:0;
    if(k){var p=el('p','none',T.artistonly.replace('{who}',q.artist).replace('{n}',count(k))+' '),go=el('button','linkbtn',T.showthem);go.type='button';
      go.addEventListener('click',function(){Q=solo;changed()});p.appendChild(go);box.appendChild(p)}
    return {note:k?T.artistonly.replace('{who}',q.artist).replace('{n}',count(k)):'',list:list,keys:keys}}
  function page(){list.slice(n,n+10).forEach(function(w){grid.appendChild(card(w,why[w.i],ty&&ty.why[w.i]));shownKeys[w[11]]=1;keys.push(w[11])});n+=10;more.hidden=n>=list.length}
  page();box.appendChild(grid);box.appendChild(more);more.addEventListener('click',page);
  return {list:list,keys:keys,note:T.shown+' '+Math.min(10,list.length)+' / '+all.length+': '+list.slice(0,10).map(function(w){return w[0]+' — '+D.artists[w[1]][0]+(w[8]?', '+eur(w[8]):'')+(w[13]?', '+cm(w[13]):'')+' ['+wid(w)+']'}).join('; ')}}

// ---- the controls: price range, medium, size, mood words ----
var F=document.getElementById('filters'), plo=document.getElementById('plo'), phi=document.getElementById('phi'), pout=document.getElementById('pout');
var dual=F.querySelector('.dual'), moods=document.getElementById('moods'), fcount=document.getElementById('fcount'), chatset=document.getElementById('chatset');
MB=JSON.parse(F.dataset.bits);
var PR=JSON.parse(plo.dataset.stops), N=PR.length-1, WIDE=window.matchMedia('(min-width:980px)');   // PR's last stop: no limit
function lowAt(v){var i=0;while(v>0&&i<N-1&&PR[i+1]<=v)i++;return i}
function highAt(v){var i=1;if(!v)return N;while(i<N&&PR[i]<v)i++;return i}
function rail(){dual.style.setProperty('--a',plo.value/N);dual.style.setProperty('--b',phi.value/N);
  plo.setAttribute('aria-valuetext',Q.min?eur(Q.min):T.anyprice);phi.setAttribute('aria-valuetext',Q.max?eur(Q.max):T.anyprice)}
function tally(){fcount.textContent=D?count(rank(Q).length)+' ↓':''}
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
  chatset.hidden=!cs.firstChild;syncYou();tally()}
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
  if(!live||live.turn){var b=el('div','msg them');log.appendChild(b);live={b:b,box:el('div')};b.appendChild(live.box)}
  else live.keys.forEach(function(k){delete shownKeys[k]});
  live.box.textContent='';var s=show(live.box,Q);live.keys=s.keys;
  if(R&&s.list.length)fill(R,s.list);
  if(quiet!==true&&WIDE.matches)live.b.scrollIntoView({block:'nearest',behavior:'smooth'})}
function changed(){sync();refresh()}
function slid(e){var a=+plo.value,b=+phi.value;
  if(a>=b){if(e.target===plo)plo.value=a=b-1;else phi.value=b=a+1}
  Q.min=PR[a];Q.max=b===N?0:PR[b];pout.textContent=priceText(Q.min,Q.max);rail();tally()}
[plo,phi].forEach(function(x){x.addEventListener('input',slid);x.addEventListener('change',changed)});
function toggle(a,x){var i=a.indexOf(x);if(i>=0)a.splice(i,1);else a.push(x)}
F.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
  if(b.dataset.m)toggle(Q.media,b.dataset.m);
  else if(b.dataset.w)toggle(Q.words,b.dataset.w);          // in the order chosen: the first weighs most
  else if(b.dataset.s)Q.size=b.dataset.s;
  else if(b.dataset.a)Q.artist=Q.artist===b.dataset.a?'':b.dataset.a;
  else if(b.dataset.clear==='artist')Q.artist='';
  else if(b.dataset.clear==='terms')Q.terms=[];
  else if(b.id==='foryou'){Q.you=!Q.you;fyAuto=false;fyKeep(Q.you);gc(Q.you?'find-foryou':'find-foryou-off')}
  else if(b.id==='fclear'){Q=blank();Q.you=fyDefault()}      // the filters cleared; For you as this browser has it
  else if(b.id==='moremoods'){var o=moods.classList.toggle('open');b.textContent=o?T.fewer:T.moremoods;b.setAttribute('aria-expanded',String(o));return}
  else if(b===fcount){if(live)live.b.scrollIntoView({block:'start',behavior:'smooth'});else refresh();return}
  else return;
  changed()});
// the assistant's search, into the controls (a Worker from before the controls answers with one kind)
function take(q){var m=q.media||({paint:['painting'],paper:['print','drawing'],sculpture:['sculpture'],photo:['photo']}[q.kind]||[]);
  Q={words:(q.words||[]).slice(),terms:(q.terms||[]).slice(),media:m.filter(function(x){return MB[x]}),min:q.budget_min||0,max:q.budget_max||0,size:q.size||'any',artist:q.artist||'',you:Q.you};sync()}

function send(text,photo){
  text=text.replace(/\s+/g,' ').trim(); if((!text&&!photo)||busy)return; busy=true;
  var ub=bubble('you',text);
  if(photo){var th=el('img','thumb');th.src=photo.url;th.alt=T.yourroom;ub.insertBefore(th,ub.firstChild);if(!text)ub.removeChild(ub.lastChild)}
  var said=(photo?T.photomsg+(text?' ':''):'')+text;
  msgs.push({role:'user',content:said}); input.value='';
  var b=bubble('them',photo?T.looking:T.thinking); b.classList.add('wait');
  // the controls as they were when the message was sent, the same for each of its rounds
  var body={messages:msgs.slice(-12),lang:document.documentElement.lang,filters:JSON.parse(JSON.stringify(Q))}, steps=[];
  // the first search's works, shown as soon as Claude asks for it (as fast as one call) while it chooses; its answer replaces them
  var early=null;
  if(!talked){talked=true;gc('find-conv-'+V)}
  if(photo){body.image=photo.data;body.w=photo.w;body.h=photo.h}else if(V==='a'){body.tools=1;body.trail=[]}
  // a round: the Worker answers, or asks for searches, which run here on the stock and go back with the next round
  function round(){return Promise.all([fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json().then(function(j){if(!r.ok)throw j;return j})}),stock()])
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
  round().then(function(res){var q=res[0], extra='', s={note:'',list:[]};
    b.classList.remove('wait'); b.firstChild.textContent=q.reply||'…';
    if(steps.length){var how=el('details','steps');how.appendChild(el('summary',null,T.how));steps.forEach(function(x){how.appendChild(el('p',null,x))});b.insertBefore(how,b.firstChild.nextSibling)}
    if(early){early.s.keys.forEach(function(k){delete shownKeys[k]});
      if(q.show||photo)early.box.remove();else{early.s.keys.forEach(function(k){shownKeys[k]=1});live={b:b,box:early.box,keys:early.s.keys,turn:true}}}
    if(photo){
      if(q.walls&&q.walls.length){R=roomView(b,photo,q.walls);
        extra=' ('+T.roomnote+': '+(q.room||'')+'; '+q.walls.map(function(w){return w.where+' '+w.w_cm+' × '+w.h_cm+' cm'}).join('; ')+')'}
      else b.appendChild(el('p','none',T.nowall));
    }
    if(q.show||photo){take(q);var box=el('div');b.appendChild(box);s=show(box,Q,q.picks);live={b:b,box:box,keys:s.keys,turn:true}}
    else if(live)live.turn=true;
    if(R&&s.list.length){fill(R,s.list);if(photo&&R.v.parentNode===b)hang(R,R.list[0])}
    msgs.push({role:'assistant',content:(q.reply||'')+extra+(s.note?' ('+s.note+')':'')});
    gc('find-turn-'+V,photo?'photo':q.show?'search':'talk');
  }).catch(function(){b.classList.remove('wait');b.firstChild.textContent=T.failed;msgs.pop()})
  .then(function(){busy=false})}
// a photo is shrunk to 1280 pixels and re-encoded here, which also drops its location data, before it is sent
function shrink(f){
  var bmp=window.createImageBitmap?createImageBitmap(f,{imageOrientation:'from-image'}).catch(function(){return createImageBitmap(f)}):Promise.reject();
  return bmp.catch(function(){return new Promise(function(ok,no){var fr=new FileReader();fr.onload=function(){var i=new Image();i.onload=function(){ok(i)};i.onerror=no;i.src=fr.result};fr.onerror=no;fr.readAsDataURL(f)})})
  .then(function(im){var w=im.width,h=im.height,k=Math.min(1,1280/Math.max(w,h));w=Math.round(w*k);h=Math.round(h*k);
    var c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(im,0,0,w,h);
    var url=c.toDataURL('image/jpeg',.85);return {url:url,data:url.slice(url.indexOf(',')+1),w:w,h:h}})}
if(file)file.addEventListener('change',function(){var f=file.files&&file.files[0];file.value='';if(!f||busy)return;
  stock().catch(function(){});shrink(f).then(function(p){send(input.value,p)}).catch(function(){bubble('them',T.badphoto)})});
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
.chat{display:grid;gap:18px 32px}
@media (min-width:980px){.chat{grid-template-columns:270px minmax(0,1fr);align-items:start}
  .filters{grid-row:1 / span 2;position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto}.log,form.ask{grid-column:2}}
.filters{display:grid;gap:18px;align-content:start;border:1px solid var(--rule);background:var(--raise);padding:16px}
.f-name{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:9px;font:500 .68rem/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}
.f-name output{font:500 .8rem/1 var(--mono);letter-spacing:.02em;text-transform:none;color:var(--ink);font-variant-numeric:tabular-nums}
.filters .chips{gap:6px}
.filters .chip{font-size:.92rem;padding:6px 11px 7px}
#akeys{margin-top:10px}
#akeys .n{font:400 .7rem/1 var(--mono);color:var(--grey)}
#akeys [aria-pressed=true] .n{color:inherit}
#media .x:not([aria-pressed=true]),#moods:not(.open) .x:not([aria-pressed=true]),#moods:not(.open) .gname{display:none}
.gname{flex-basis:100%;margin-top:8px;font:500 .62rem/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}
.linkbtn{background:none;border:0;padding:6px 2px;font:500 .68rem/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--grey);text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.linkbtn:hover{color:var(--ink)}
.filters .seg .btn{flex:1;padding:9px 4px;font-size:.66rem}
.dual{position:relative;height:28px;margin:0 2px}
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
.acomp input{width:100%;font:400 1rem/1.2 var(--serif);color:var(--ink);background:var(--paper);border:1px solid var(--rule);border-radius:0;padding:8px 30px 8px 10px;-webkit-appearance:none;appearance:none}
.acomp input::-webkit-search-cancel-button{display:none}
.acomp input:focus{outline:2px solid var(--ink);outline-offset:1px}
.acomp .x{position:absolute;right:2px;top:50%;transform:translateY(-50%);background:none;border:0;color:var(--grey);font-size:1.1rem;line-height:1;padding:4px 7px;cursor:pointer}.acomp .x:hover{color:var(--ink)}
.acomp ul{position:absolute;left:0;right:0;top:100%;z-index:5;margin:3px 0 0;padding:4px 0;list-style:none;background:var(--raise);border:1px solid var(--grey);max-height:264px;overflow:auto}
.acomp li{display:flex;justify-content:space-between;gap:10px;padding:7px 10px;cursor:pointer;font-size:.92rem}
.acomp li span{font:500 .72rem/1.6 var(--mono);color:var(--grey);font-variant-numeric:tabular-nums}
.acomp li:hover,.acomp li[aria-selected=true]{background:var(--field)}
#chatset .bits{display:flex;flex-wrap:wrap;gap:6px}
#chatset .bit{display:inline-flex;align-items:center;gap:4px;font-size:.85rem;border:1px solid var(--rule);padding:3px 4px 3px 9px}
#chatset .x{background:none;border:0;color:var(--grey);font-size:1rem;line-height:1;padding:2px 5px;cursor:pointer}#chatset .x:hover{color:var(--ink)}
.f-foot{display:flex;justify-content:space-between;align-items:center;gap:8px;border-top:1px solid var(--rule);padding-top:12px}
.count{background:none;border:0;padding:4px 0;font:500 .8rem/1 var(--mono);color:var(--ink);font-variant-numeric:tabular-nums;cursor:pointer}.count:empty{visibility:hidden}
.log{display:grid;gap:16px}
.msg p{margin:0}
.msg.you{justify-self:end;max-width:min(560px,90%);background:var(--raise);border:1px solid var(--rule);padding:10px 14px;font:400 1.05rem/1.4 var(--serif)}
.msg.them>p:first-child{font:400 1.18rem/1.45 var(--serif);max-width:62ch}
.msg.wait>p:first-child{color:var(--grey)}
.search{margin:10px 0 0!important;font:500 .72rem/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--grey)}
.none{margin-top:10px!important;color:var(--grey)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:18px 14px;margin-top:14px}
.card{display:grid;align-content:start;gap:4px}
.card .out{display:grid;gap:3px;text-decoration:none}
.card img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:var(--field)}
.card .cap{padding-top:5px;font-size:.78rem;line-height:1.3;color:var(--grey)}
.card .cap i{display:block;font:italic 400 1rem/1.2 var(--serif);color:var(--ink)}
.card .out:hover .cap i{text-decoration:underline}
.card .meta{font-size:.74rem;color:var(--grey);line-height:1.3}
.card .price{font-size:.78rem;color:var(--grey)}.card .price b{font:500 .86rem/1.3 var(--mono);color:var(--ink);margin-right:4px}
.card .fy{margin:2px 0 0;font-size:.74rem;line-height:1.3;color:var(--grey)}
.filters .chip:disabled{opacity:.45;cursor:default}
.f-hint{margin:8px 0 0;font-size:.8rem;line-height:1.4;color:var(--grey)}.f-hint a{color:var(--ink)}
.card .by{font-size:.78rem;line-height:1.3;color:var(--grey)}
.card .by a{color:inherit;text-decoration:none}.card .by a:hover{color:var(--ink);text-decoration:underline}
.card .why{margin:2px 0 0;font-size:.78rem;line-height:1.35;color:var(--ink)}
.steps{margin:6px 0 0;font-size:.74rem;color:var(--grey)}.steps summary{cursor:pointer}.msg .steps p{margin:3px 0 0 1em}
.more{justify-self:start;margin-top:12px}
form.ask{position:sticky;bottom:0;background:var(--paper);padding:12px 0 6px;border-top:1px solid var(--rule);display:flex;gap:8px;flex-wrap:wrap}
form.ask label[for=q]{position:absolute;left:-9999px}
form.ask input{flex:1 1 260px;min-width:0;font:400 1.1rem/1.2 var(--serif);color:var(--ink);background:var(--raise);border:1px solid var(--rule);padding:11px 12px}
form.ask input:focus{outline:2px solid var(--ink);outline-offset:1px}
.photobtn{display:inline-flex;align-items:center}
.msg.you .thumb{display:block;max-width:220px;height:auto;margin-bottom:6px}
.room{margin-top:14px;display:grid;gap:8px;max-width:860px}
.stage{position:relative;overflow:hidden;background:var(--field);touch-action:none;cursor:grab;width:100%}
.stage.turning{cursor:grabbing}
.scene{position:absolute;left:0;top:0;transform-origin:0 0}
.scene .photo{display:block;user-select:none;-webkit-user-drag:none;pointer-events:none}
.stage svg.outline{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none}
.outline polygon{fill:rgba(255,255,255,.05);stroke:#fff;stroke-width:2;stroke-dasharray:10 7;opacity:.75;vector-effect:non-scaling-stroke}
.layer{position:absolute;left:0;top:0;pointer-events:none}
.hang,.shade{position:absolute;left:0;top:0;transform-origin:0 0}
.hang{pointer-events:auto;cursor:grab;touch-action:none;user-select:none;-webkit-user-select:none}
.hang:active{cursor:grabbing}
.hang .fr,.hang .mat{box-sizing:border-box;width:100%;height:100%}
.hang .fr{padding:var(--f)}.hang .mat{padding:var(--m);background:#f5f2ea}
.hang img{display:block;width:100%;height:100%;pointer-events:none;box-shadow:-2px -2px 4px rgba(0,0,0,.28)}
.hang.crop img{object-fit:cover}
.hang::after{content:"";position:absolute;left:0;top:0;right:0;bottom:0;pointer-events:none;background:linear-gradient(165deg,rgba(255,255,255,.08),rgba(0,0,0,.1))}
.hang.sel{outline:5px solid rgba(255,255,255,.9);outline-offset:8px}
.f-none .mat{background:none}.f-none img{box-shadow:none}
.f-none::after{box-shadow:inset -10px -8px 12px -8px rgba(0,0,0,.5)}
.f-black .fr{background:linear-gradient(135deg,#4a4a4a,#161616 35%,#050505);box-shadow:inset 2px 2px 3px rgba(255,255,255,.2),inset -3px -3px 5px rgba(0,0,0,.75)}
.f-oak .fr{background:repeating-linear-gradient(95deg,rgba(95,58,22,.13) 0 3px,transparent 3px 10px),linear-gradient(135deg,#e6c18a,#bb8d55 55%,#93663a);box-shadow:inset 2px 2px 3px rgba(255,255,255,.4),inset -3px -3px 5px rgba(60,35,10,.55)}
.f-white .fr{background:linear-gradient(135deg,#fff,#e6e2d9);box-shadow:inset 2px 2px 3px #fff,inset -3px -3px 5px rgba(0,0,0,.2)}
.f-gold .fr{background:linear-gradient(135deg,#f7e4a3,#d4ad4d 28%,#8e6b1f 52%,#e7c970 78%,#a9842d);box-shadow:inset 3px 3px 4px rgba(255,255,255,.5),inset -4px -4px 6px rgba(70,45,5,.6)}
.shade{background:rgba(0,0,0,.5);filter:blur(24px);pointer-events:none}
.strip{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;scroll-snap-type:x proximity}
.strip button{flex:0 0 auto;width:96px;padding:0;border:1px solid var(--rule);background:var(--raise);color:var(--ink);cursor:pointer;display:grid;gap:4px;text-align:left;scroll-snap-align:start}
.strip button img{display:block;width:100%;height:76px;object-fit:cover;background:var(--field)}
.strip button span{font:500 .68rem/1.2 var(--mono);padding:0 6px 6px;color:var(--grey)}
.strip button.hung{border-color:var(--grey)}.strip button.hung span::before{content:"\2713  "}
.strip button[aria-pressed=true]{border-color:var(--ink);box-shadow:0 0 0 1px var(--ink)}
.strip .more{width:auto;padding:0 12px;font:500 .7rem/1 var(--mono);text-transform:uppercase;letter-spacing:.06em;align-content:center}
.tools{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
.tools .seg .btn{text-transform:none;letter-spacing:0;font-size:.74rem;padding:8px 10px}
.tools .width{display:flex;align-items:center;gap:8px;font:500 .72rem/1.4 var(--mono);color:var(--grey);text-transform:uppercase;letter-spacing:.06em}
.tools .width input{width:160px}
.tools output{color:var(--ink);min-width:6ch}
.room .hint{margin:0;font-size:.78rem;color:var(--grey)}
.room .caption{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline}
.room .placed,.room .total{margin:0;font-size:.9rem;color:var(--ink-soft)}.room .placed i{font:italic 400 1.02rem var(--serif);color:var(--ink)}.room .placed a{color:var(--ink)}
.room .total{font:500 .78rem/1.4 var(--mono);color:var(--grey)}
.room .caption .btn{padding:6px 9px;font-size:.64rem}
.arslot:empty{display:none}
.btn.arbtn.arbig{width:100%;padding:13px;font-size:.78rem;background:var(--on);color:var(--on-ink);border-color:var(--on);margin:0}
.arhint{margin:0;font-size:.85rem;color:var(--ink-soft)}
.btn.arbtn{padding:6px 9px;font-size:.64rem;margin-top:2px;justify-self:start}
.btn.onwall{justify-self:start;padding:6px 9px;font-size:.64rem;margin-top:2px}
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
    sizes = "".join(f'<button type="button" class="btn" data-s="{k}" aria-pressed="{str(k == "any").lower()}"'
                    + (f' title="{e(t["sizehint"][k])}"' if k != "any" else "") + f'>{e(t["sizeany"] if k == "any" else t["sizes"][k])}</button>'
                    for k in ("any", "small", "medium", "large"))
    grp = {w["en"]: ("feeling" if w["g"] == "more" else w["g"]) for w in M}
    moods = "".join(chip("w", w, labels[w]) for w in TOP_MOODS)
    for g in t["groups"]:
        rest = [w["en"] for w in M if grp[w["en"]] == g and w["en"] not in TOP_MOODS]
        if rest: moods += f'<span class="gname">{e(t["groups"][g])}</span>' + "".join(chip("w", w, labels[w], " x") for w in rest)
    moods += f'<button type="button" class="linkbtn" id="moremoods" aria-expanded="false" aria-controls="moods">{e(t["moremoods"])}</button>'
    n = len(PRICE_STOPS) - 1
    return (f'<div class="filters" id="filters" role="group" aria-label="{e(t["filters"])}" data-bits="{e(json.dumps(BIT))}">'
            f'<div class="f-row" id="fyou"><div class="f-name">{e(t["fy"])}</div><div class="chips"><button type="button" class="chip" id="foryou" aria-pressed="false" disabled>{e(t["fybtn"].format(n=0))}</button></div>'
            f'<p class="f-hint" id="fyhint" hidden></p></div>'
            f'<div class="f-row"><div class="f-name">{e(t["price"])} <output id="pout">{e(t["anyprice"])}</output></div>'
            f'<div class="dual" style="--a:0;--b:1"><span class="track"></span><span class="fill"></span>'
            f'<input type="range" id="plo" min="0" max="{n}" step="1" value="0" aria-label="{e(t["lowest"])}" data-stops="{json.dumps(PRICE_STOPS)}">'
            f'<input type="range" id="phi" min="0" max="{n}" step="1" value="{n}" aria-label="{e(t["highest"])}"></div></div>'
            f'<div class="f-row"><div class="f-name">{e(t["medium"])}</div><div class="chips" id="media">{media}</div></div>'
            f'<div class="f-row"><div class="f-name">{e(t["size"])}</div><div class="seg">{sizes}</div></div>'
            f'<div class="f-row"><label class="f-name" for="artist">{e(t["artist"])}</label><div class="acomp">'
            f'<input id="artist" type="search" autocomplete="off" spellcheck="false" placeholder="{e(t["artistph"])}" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="artists">'
            f'<button type="button" class="x" id="aclear" data-clear="artist" aria-label="{e(t["clear"])}" hidden>×</button>'
            f'<ul id="artists" role="listbox" aria-label="{e(t["artistlist"])}" hidden></ul></div>'
            f'<div class="chips" id="akeys" role="group" aria-label="{e(t["names"])}">'
            + "".join(f'<button type="button" class="chip" data-a="{e(a)}" aria-pressed="false">{e(a)} <span class="n">{c}</span></button>' for a, c in names)
            + '</div></div>'
            f'<div class="f-row"><div class="f-name">{e(t["mood"])}</div><div class="chips" id="moods">{moods}</div></div>'
            f'<div class="f-row" id="chatset" hidden><div class="f-name">{e(t["fromchat"])}</div><div class="bits"></div></div>'
            f'<div class="f-foot"><button type="button" class="count" id="fcount"></button><button type="button" class="linkbtn" id="fclear">{e(t["clear"])}</button></div>'
            '</div>')

# "Photo of your wall" (the room view): off for now, 2026-10-02. The code stays; True brings the button back, and the
# lede, hello and note that told of it are in git history (commit 9c3e4a1), to be put back with it
PHOTO = False

def page(lang, ver, api, labels, M, n=0, tver="", names=()):
    t = T[lang]
    me, other = f"{BASE}/{t['file']}", f"{BASE}/{t['other']}"
    tj = json.dumps({k: t[k] for k in ("more", "at", "noprice", "none", "thinking", "how", "like", "choosing", "failed", "record", "sizes", "shown", "hash",
                                       "media", "anyprice", "upto", "from_", "count", "count1", "moremoods", "fewer", "clear", "artist", "titlew", "artistonly", "showthem", "daily",
                                       "yourroom", "looking", "photomsg", "wallw", "drag", "onwall", "fits", "roomnote", "nowall", "badphoto",
                                       "choose", "hangmore", "remove", "together", "frames", "reset", "ar", "arwait", "arfail", "arsafari",
                                       "sl_add", "sl_remove", "fybtn", "fyhint", "fysee", "fybit", "fylike", "fynone")}, ensure_ascii=False).replace("</", "<\\/")
    lj = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")
    ask = (api.rstrip("/") + "/ask") if api else ""
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(t["title"].format(n=f"{n:,}".replace(",", " " if lang == "et" else ",")))} · museaal.ee</title><meta name="description" content="{e(t["lede"][:290])}">'
            f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
            f'<style>{CSS}</style>{H.GC}</head><body><div class="wrap">'
            f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{e(t["site"])}</a> › {e(t["h"])} · <a href="{other}" hreflang="{"et" if lang == "en" else "en"}">{e(t["other_l"])}</a></nav>'
            f'<header><h1>{e(t["h"])}</h1><p class="lede">{e(t["lede"])}</p></header>'
            f'<section class="chat" id="chat" data-api="{e(ask)}" data-src="data/stock.json?v={ver}" data-taste="data/taste-stock.bin?v={tver}" data-tshard="data/taste/" data-tver="{tver}">'
            f'{panel(t, labels, M, names)}<div class="log" id="log" aria-live="polite"><div class="msg them"><p>{e(t["hello"])}</p></div></div>'
            f'<form class="ask" id="ask"><label for="q">{e(t["label"])}</label><input id="q" type="text" maxlength="400" autocomplete="off" placeholder="{e(t["ph"])}">'
            f'<button class="btn solid" type="submit">{e(t["send"])}</button>'
            + (f'<input id="photo" type="file" accept="image/*" hidden><label for="photo" class="btn photobtn" role="button" tabindex="0">{e(t["photo"])}</label>' if PHOTO else '')
            + '</form></section>'
            + browse_links(lang)
            + f'<footer>{e(t["note"])} {H.CONTACT[lang]}</footer></div>'
            f'<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/"}}}}</script>'
            f'<script type="application/json" id="t">{tj}</script><script type="application/json" id="labels">{lj}</script><script>{BM.SL_JS}{JS}</script></body></html>')

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
      "et": dict(lede="{n} teost {g} Eesti galeriis koos küsitud hindadega. Iga teos viib seda müüva galerii lehele.",
                 lede1="1 teos Eesti galeriis koos küsitud hinnaga.", more="Vali neist lehel Osta kunsti →",
                 browse="Sirvi müügil olevat", first="Siin esimesed {k} teost {n}-st; kõik lehel Osta kunsti.", artist="Kunstniku leht")}

def browse_links(lang, here=None):
    i = 3 if lang == "en" else 5
    return (f'<p class="browse"><span class="eyebrow">{e(ST[lang]["browse"])}</span> ' + " · ".join(
        (f'<b>{e(s[i])}</b>' if s[2 if lang == "en" else 4] == here else
         f'<a href="{BASE}/{SALE_DIR[lang]}/{s[2] if lang == "en" else s[4]}.html">{e(s[i])}</a>') for s in SALE) + "</p>")

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
            me = f"{BASE}/{SALE_DIR[lang]}/{sl}.html"; other = f"{BASE}/{SALE_DIR['et' if lang == 'en' else 'en']}/{sl_et if lang == 'en' else sl_en}.html"
            lede = st["lede1"] if len(pick) == 1 else st["lede"].format(n=f"{len(pick):,}".replace(",", " " if lang == "et" else ","), g=g)
            cards = "".join(
                f'<article class="card"><a class="out" href="{e(w[10])}" target="_blank" rel="noopener">'
                f'<img src="{e(w[3])}" alt="{e(w[0])}, {e(arts[w[1]][0])}" loading="lazy" decoding="async" referrerpolicy="no-referrer-when-downgrade">'
                f'<span class="cap"><i>{e(w[0])}</i>{e(arts[w[1]][0])}{", " + e(str(w[2])) if w[2] else ""}</span>'
                + (f'<span class="meta">{e(" · ".join(x for x in ((lang == "en" and w[15]) or w[4], w[5]) if x))}</span>' if (w[4] or w[5]) else "")
                + f'<span class="price"><b>{eur(w[8], lang) if w[8] else e(t["noprice"])}</b> {e((t["at"] + " ") if t["at"] else "")}{e(gals[w[9]])} ↗</span></a>'
                f'<a class="rec" href="{BASE}/{"a" if lang == "en" else "k"}/{arts[w[1]][1]}.html">{e(st["artist"])}</a></article>' for w in rows)
            find = f'{BASE}/{t["file"]}#{hashq}'
            ld = H.ldjson({"@context": "https://schema.org", "@type": "CollectionPage", "name": h, "url": me, "inLanguage": lang,
                           "mainEntity": {"@type": "ItemList", "numberOfItems": len(pick), "itemListElement": [
                               {"@type": "ListItem", "position": k + 1, "item": H.offer_item(
                                   w[0], arts[w[1]][0], w[2], (lang == "en" and w[15]) or w[4], w[3], w[8], gals[w[9]], w[10])}
                               for k, w in enumerate(rows)]}})
            html_ = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                     f'<title>{e(h)} · museaal.ee</title><meta name="description" content="{e(lede[:290])}">'
                     f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
                     f'<script type="application/ld+json">{ld}</script>'
                     '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
                     '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
                     f'<style>{CSS}.browse{{margin:0;font-size:.9rem;line-height:1.9;color:var(--grey)}}.browse .eyebrow{{margin-right:8px}}.browse b{{color:var(--ink);font-weight:500}}</style>{H.GC}</head><body><div class="wrap">'
                     f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{e(t["site"])}</a> › <a href="{BASE}/{t["file"]}">{e(t["h"])}</a> › {e(h)} · '
                     f'<a href="{other}" hreflang="{"et" if lang == "en" else "en"}">{e(t["other_l"])}</a></nav>'
                     f'<header><h1>{e(h)}</h1><p class="lede">{e(lede)}</p><p><a class="btn solid" href="{e(find)}">{e(st["more"])}</a></p></header>'
                     f'<div class="grid">{cards}</div>'
                     + (f'<p class="m">{e(st["first"].format(k=len(rows), n=len(pick)))}</p>' if len(pick) > len(rows) else "")
                     + browse_links(lang, sl)
                     + f'<footer>{e(t["note"].split(". ")[0])}. {H.CONTACT[lang]}</footer></div></body></html>')
            os.makedirs(f"site/{SALE_DIR[lang]}", exist_ok=True)
            open(f"site/{SALE_DIR[lang]}/{sl}.html", "w", encoding="utf-8").write(html_); urls.append(me)
    return urls

def feed(d):
    """/data/for-sale.csv: the stock with every value named, a row a work -- for a spreadsheet, a search engine or an
    agent, none of which can read stock.json's numbered fields. The works and asking prices Buy Art shows"""
    arts, gals, words = d["artists"], d["galleries"], d["words"]
    with open("site/data/for-sale.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["title", "artist", "year", "technique", "technique_en", "medium", "dimensions", "size", "price_eur",
                     "gallery", "url", "image", "moods", "artist_page"])
        for w in d["works"]:
            wr.writerow([w[0], arts[w[1]][0], w[2], w[4], w[15] or w[4], "; ".join(m for m in MEDIA if w[14] & BIT[m]),
                         w[5], w[6], w[8] or "", gals[w[9]], w[10], w[3], "; ".join(words[j] for j in w[12][::2]),
                         f"{BASE}/a/{arts[w[1]][1]}.html"])

def llms_txt(d):
    """/llms.txt (llmstxt.org): what the site is and where its data lives, in plain words for a language model that
    reads it -- above all that the prices are the galleries' asking prices and a work is bought from the gallery"""
    M, W_ = H.META, d["works"]
    n = lambda x: f"{x:,}"
    sale = "\n".join(f"- [{s[3]}]({BASE}/{SALE_DIR['en']}/{s[2]}.html)" for s in SALE)
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
- [Buy Art]({BASE}/{T["en"]["file"]}): the same works, searched by price, medium, size and mood, or by describing what you \
are after ([in Estonian]({BASE}/{T["et"]["file"]}))
{sale}

Each of these is in Estonian too, under {BASE}/{SALE_DIR["et"]}/.

## Artists

- [Artists A–Z]({BASE}/a/): a page for each artist — dates, biography, the museums that hold their work, works for \
sale, record at auction; in Estonian under {BASE}/k/

## Data

- [Every record, CSV, gzip]({BASE}/data/export/works.csv.gz): a row a record, every value written out
- [Artists, CSV, gzip]({BASE}/data/export/artists.csv.gz)
- [The catalogue in figures]({BASE}/stats.html)

## Optional

- [Art by mood]({BASE}/mood.html): museum pictures by the mood words a visitor picks
- Corrections and questions: info@museaal.ee
"""
    open("site/llms.txt", "w", encoding="utf-8").write(txt)

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
        open(f"site/{T[lang]['file']}", "w", encoding="utf-8").write(page(lang, ver, API, labels, M, len(d["works"]), tver, door_names(d))); urls.append(f"{BASE}/{T[lang]['file']}")
    urls += sale_pages(d)
    feed(d); llms_txt(d)
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    W_ = d["works"]
    print(f"  find a work    {len(W_):,} works for sale, {sum(1 for w in W_ if w[8]):,} with a price, {sum(1 for w in W_ if w[12]):,} with moods; "
          f"stock.json {len(blob) // 1024} KB, for-sale.csv, llms.txt; assistant {'at the Worker' if API else 'not set up'}")

if __name__ == "__main__":
    main()
