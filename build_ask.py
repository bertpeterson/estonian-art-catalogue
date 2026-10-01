# -*- coding: utf-8 -*-
"""Find a work: /find.html and /leia.html, and the stock they read, /data/stock.json.

A visitor says what they are looking for -- the room, the budget, the mood -- and an
assistant answers in a sentence or two while the page shows works the galleries have for
sale now. The assistant is Claude Haiku behind the mood page's Worker (its /ask door,
worker/template.js): it gets the conversation and answers with a reply and a search --
mood words from the same vocabulary, a kind, a size and a budget. It never sees the
works. The page ranks the stock itself from that search: the mood scores of the gallery's
own picture (data/stock_moods.py, on the museum pictures' scale), the asking price the
gallery's page states, and the size read off the dimensions. Every card links to the
gallery's own page, where the work is sold.

Only current stock with the gallery's picture; a work without a price is shown only
while no budget is set. Run after build_mood.py (it adds to the sitemap) and before csp.py.
"""
import json, os, re, hashlib, datetime, urllib.parse
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

T = {"en": dict(file="find.html", other="leia.html", other_l="Eesti keeles", site="Estonian Art Catalogue",
                h="Find a work", lede="Looking for something for your wall? Tell the assistant where it will hang, what you would like to spend and the feeling you are after, or send a photo of the wall: it finds the space, picks works that fit it and hangs them there for you to see. It looks through the works the catalogue's galleries have for sale now, and each one links to the gallery that sells it.",
                hello="Looking for something? Tell me the room, your budget and the mood, or send a photo of the wall.",
                photo="Photo of your wall", yourroom="Your room", looking="Looking at your room…", photomsg="(a photo of my room)",
                wallw="Wall space, width", drag="Drag the room to look around it; scroll or pinch to step closer. Drag a work to move it along the wall, or onto another outlined space. If the sizes look wrong, set the wall's width.", reset="Reset view", ar="See it on your wall (AR)", arsafari="To see a work on your real wall in AR, open this page in Safari.", arwait="Making the model…", arfail="AR could not be opened", onwall="On my wall",
                choose="Tap a work to hang it", hangmore="Hang another", remove="Take it down", together="{n} works on the wall",
                frames=dict(none="No frame", black="Black", oak="Oak", white="White", gold="Gold"),
                fits="fits", roomnote="Room", nowall="I couldn't find a clear stretch of wall in that photo. Try one taken straight on, with the empty wall in view.",
                badphoto="That photo could not be read. Try a JPEG or PNG.",
                starters=["A calm sea painting for the bedroom, under €1,000", "Something bright and joyful for a big living-room wall", "A small print as a gift, around €200"],
                label="Your message", ph="e.g. a misty landscape above the sofa, up to €2,000", send="Send",
                more="Show more", at="at", noprice="Price on request", none="Nothing for sale matches all of that. Try a wider budget or another size.",
                thinking="Thinking…", failed="The assistant could not be reached. Try again in a moment.", record="In the catalogue",
                kinds=dict(paint="paintings", paper="works on paper", sculpture="sculpture", photo="photographs"),
                sizes=dict(small="small", medium="medium", large="large"), under="under", over="over", shown="Shown",
                note="The works are the galleries' current stock with their asking prices, read weekly from each gallery's own site; the gallery's page is the one to trust. Your messages are read by Claude to choose the search and are not stored. A photo of your room is shrunk in your browser, which also removes its location data, then read by Claude to find the wall space, and is not stored; the works are shown on it from the galleries' own pictures, at a size estimated from the photo. The moods are read from the gallery's photograph by CLIP, an image model: a guide, not a judgement of the work.",
                hash=""),
     "et": dict(file="leia.html", other="find.html", other_l="In English", site="Eesti Kunstikataloog",
                h="Leia teos", lede="Otsid midagi seinale? Ütle abilisele, kuhu see tuleb, kui palju tahad kulutada ja millist tunnet otsid, või saada foto seinast: ta leiab vaba koha, valib sinna sobivad teosed ja riputab need pildile, et saaksid vaadata. Ta vaatab läbi teosed, mis kataloogi galeriidel praegu müügil on, ja iga teos viib seda müüva galerii lehele.",
                hello="Otsid midagi? Ütle, mis tuppa, mis eelarvega ja mis meeleoluga, või saada foto seinast.",
                photo="Foto seinast", yourroom="Sinu tuba", looking="Vaatan su tuba…", photomsg="(foto minu toast)",
                wallw="Vaba seinaosa laius", drag="Lohista tuba, et ringi vaadata; keri või näpista, et lähemale astuda. Lohista teost, et seda seinal liigutada või teisele märgitud kohale viia. Kui suurused tunduvad valed, sea seina laius õigeks.", reset="Algvaade", ar="Vaata oma seinal (AR)", arsafari="Et näha teost AR-is oma päris seinal, ava see leht Safaris.", arwait="Teen mudelit…", arfail="AR-i ei õnnestunud avada", onwall="Minu seinale",
                choose="Puuduta teost, et see seinale riputada", hangmore="Riputa veel üks", remove="Võta maha", together="Seinal {n} teost",
                frames=dict(none="Raamita", black="Must", oak="Tamm", white="Valge", gold="Kuld"),
                fits="mahub", roomnote="Tuba", nowall="Ma ei leidnud sellelt fotolt vaba seinaosa. Proovi fotot, mis on tehtud otse seina poole ja kus tühi sein on näha.",
                badphoto="Seda fotot ei õnnestunud lugeda. Proovi JPEG- või PNG-faili.",
                starters=["Rahulik merepilt magamistuppa, alla 1000 €", "Midagi heledat ja rõõmsat suurele elutoa seinale", "Väike graafikaleht kingituseks, umbes 200 €"],
                label="Sinu sõnum", ph="nt udune maastik diivani kohale, kuni 2000 €", send="Saada",
                more="Näita rohkem", at="", noprice="Hind päringul", none="Müügil pole midagi, mis kõigele vastaks. Proovi laiemat eelarvet või muud suurust.",
                thinking="Mõtlen…", failed="Abilist ei õnnestunud kätte saada. Proovi hetke pärast uuesti.", record="Kataloogis",
                kinds=dict(paint="maalid", paper="tööd paberil", sculpture="skulptuur", photo="fotod"),
                sizes=dict(small="väike", medium="keskmine", large="suur"), under="alla", over="üle", shown="Näidatud",
                note="Teosed on galeriide praegune müügivalik ja nende küsitud hinnad, loetud iga nädal galeriide endi lehtedelt; usaldusväärne on galerii leht. Sinu sõnumeid loeb Claude otsingu valimiseks ja neid ei salvestata. Toa foto vähendatakse sinu brauseris, mis eemaldab ka asukohaandmed, seejärel loeb Claude sellelt vaba seinaosa ning fotot ei salvestata; teosed näidatakse sellel galeriide endi piltidelt, fotolt hinnatud suuruses. Meeleolu loeb galerii fotolt pildimudel CLIP: see on juhatus, mitte hinnang teosele.",
                hash="lang=et&")}

def data():
    S = json.load(open("data/stock_moods.json", encoding="utf-8")) if os.path.exists("data/stock_moods.json") else {}
    words = [w["en"] for w in json.load(open("data/moods.json", encoding="utf-8"))["words"]]
    aidx, arts, gals, works = {}, [], {}, []
    seen = set()
    for w in W:
        if w.get("kind") != "gallery" or not (w.get("im") or "").startswith("g:"): continue
        u = re.sub(r"^http:", "https:", w["im"][2:])
        if not u.startswith("https://") or not (w.get("url") or "").startswith("http"): continue
        k = H.key(w)
        if k in seen: continue
        seen.add(k)
        a = w["a"]
        if a not in aidx: aidx[a] = len(arts); arts.append([A[a]["n"], H.ARTIST_SLUG[a]])
        g = H.val(w, "mu") or ""
        gals.setdefault(g, len(gals))
        tech = H.val(w, "tce") or H.val(w, "tc") or ""
        works.append([w.get("t") or "", aidx[a], w.get("y") or "", u, tech[:60], w.get("dm") or "",
                      size_of(w.get("dm")), kind_of(w), w.get("pr") or 0, gals[g], w["url"], k,
                      [x for j, z in S.get(w["im"], [])[:8] if z >= 1.0 for x in (j, round(z * 10))],   # word, z x 10, flat
                      dims_of(w.get("dm")) or 0])
    return {"words": words, "artists": arts, "galleries": list(gals), "works": works}

JS = r"""
(function(){
var T=JSON.parse(document.getElementById('t').textContent), page=document.getElementById('chat');
var api=page.dataset.api, src=page.dataset.src, log=document.getElementById('log'), form=document.getElementById('ask'), input=document.getElementById('q'), file=document.getElementById('photo');
var D=null, P=null, msgs=[], shownKeys={}, busy=false, labels=JSON.parse(document.getElementById('labels').textContent);
var R=null, rooms=[];                              // the room on view (the latest photo), and every one shown
function stock(){ return P=P||fetch(src).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(d){
  d.works.forEach(function(w){var m={},f=w[12];for(var i=0;i<f.length;i+=2)m[d.words[f[i]]]=f[i+1]/10;w.m=m}); D=d; return d}).catch(function(e){P=null;throw e})}
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
  else if(IOS)r.arSlot.appendChild(el('p','arhint',T.arsafari));
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
var ARDEBUG=/ardebug/.test(location.hash), AR=ARDEBUG||(function(){var a=document.createElement('a');return !!(a.relList&&a.relList.supports&&a.relList.supports('ar'))})();
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

function rank(q){
  var wt=[1,.8,.65,.5,.4], out=[], ws=R&&wallCm(R,R.sel?R.sel.wall:0);
  D.works.forEach(function(w){
    if(q.kind!=='any'&&w[7]!==q.kind)return;
    if(q.budget_max>0&&!(w[8]&&w[8]<=q.budget_max*1.05))return;
    if(q.budget_min>0&&!(w[8]&&w[8]>=q.budget_min))return;
    if(shownKeys[w[11]])return;                   // shown earlier in the conversation
    var s=0;q.words.forEach(function(x,i){s+=wt[i]*(w.m[x]||0)});
    if(!q.words.length)s=hash(w[11]);
    if(ws){                                       // a wall on view: what fits it, best near half its width
      var d=w[13];if(!d||w[7]==='sculpture')return;
      if(!((d[0]<=.9*ws[0]&&d[1]<=.9*ws[1])||(d[1]<=.9*ws[0]&&d[0]<=.9*ws[1])))return;
      var share=d[0]/Math.max(ws[0],ws[1]);if(share<.25)return;   // a postcard on a big wall: not a suggestion
      s+=2.5*(1-2*Math.abs(share-.5));
    }else{
      if(q.size!=='any'&&w[6]&&w[6]!==q.size)return;
      if(q.size!=='any'&&!w[6])s-=50;             // size unknown: only after every one that fits
    }
    out.push([s,w])});
  out.sort(function(a,b){return b[0]-a[0]});
  // one work per artist in each row of six, as far as the list allows
  var picked=[],per={},rest=[];
  out.forEach(function(p){var a=p[1][1];if(per[a]>=Math.floor(picked.length/6)+1){rest.push(p[1]);return}per[a]=(per[a]||0)+1;picked.push(p[1])});
  return picked.concat(rest)}
function card(w){
  var a=D.artists[w[1]], g=D.galleries[w[9]], c=el('article','card');
  var out=el('a','out');out.href=w[10];out.target='_blank';out.rel='noopener';
  out.addEventListener('click',function(){if(window.goatcounter&&goatcounter.count)goatcounter.count({path:'find-out',title:g,event:true})});
  var img=el('img');img.src=w[3];img.alt=w[0]+', '+a[0];img.loading='lazy';img.decoding='async';img.referrerPolicy='no-referrer-when-downgrade';out.appendChild(img);
  var cap=el('span','cap');cap.appendChild(el('i',null,w[0]));cap.appendChild(document.createTextNode(a[0]+(w[2]?', '+w[2]:'')));out.appendChild(cap);
  var meta=[w[4],w[5]].filter(Boolean).join(' · ');if(meta)out.appendChild(el('span','meta',meta));
  var pr=el('span','price');pr.appendChild(el('b',null,w[8]?eur(w[8]):T.noprice));pr.appendChild(document.createTextNode(' '+(T.at?T.at+' ':'')+g+' ↗'));out.appendChild(pr);
  c.appendChild(out);
  if(R&&w[13]){var r=R,on=el('button','btn onwall',T.onwall);on.type='button';
    on.addEventListener('click',function(){hang(r,w);r.v.scrollIntoView({block:'center',behavior:'smooth'})});c.appendChild(on)}
  if(AR&&w[13])c.appendChild(arButton(w,function(){return R&&R.sel?R.sel.frame:'black'}));
  var rec=el('a','rec',T.record);rec.href='./#'+T.hash+'artist='+a[1]+'&open='+encodeURIComponent(w[11]);c.appendChild(rec);
  return c}
function show(b,q){
  var list=rank(q), n=0, grid=el('div','grid'), more=el('button','btn more',T.more);more.type='button';
  var bits=[];if(q.kind!=='any')bits.push(T.kinds[q.kind]);
  if(R){var ws=wallCm(R,R.sel?R.sel.wall:0);bits.push(T.fits+' '+Math.round(ws[0])+' × '+Math.round(ws[1])+' cm')}else if(q.size!=='any')bits.push(T.sizes[q.size]);
  if(q.budget_max>0)bits.push((q.budget_min>0?eur(q.budget_min)+'–':T.under+' ')+eur(q.budget_max));else if(q.budget_min>0)bits.push(T.over+' '+eur(q.budget_min));
  bits=bits.concat(q.words.map(function(x){return labels[x]||x}));
  if(bits.length)b.appendChild(el('p','search',bits.join(' · ')));
  if(!list.length){b.appendChild(el('p','none',T.none));return {note:'',list:list}}
  function page(){list.slice(n,n+6).forEach(function(w){grid.appendChild(card(w));shownKeys[w[11]]=1});n+=6;more.hidden=n>=list.length}
  page();b.appendChild(grid);b.appendChild(more);more.addEventListener('click',page);
  return {list:list,note:list.slice(0,6).map(function(w){return w[0]+' — '+D.artists[w[1]][0]+(w[8]?', '+eur(w[8]):'')+(w[13]?', '+cm(w[13]):'')}).join('; ')}}
function send(text,photo){
  text=text.replace(/\s+/g,' ').trim(); if((!text&&!photo)||busy)return; busy=true;
  var ub=bubble('you',text);
  if(photo){var th=el('img','thumb');th.src=photo.url;th.alt=T.yourroom;ub.insertBefore(th,ub.firstChild);if(!text)ub.removeChild(ub.lastChild)}
  var said=(photo?T.photomsg+(text?' ':''):'')+text;
  msgs.push({role:'user',content:said}); input.value='';
  var b=bubble('them',photo?T.looking:T.thinking); b.classList.add('wait');
  var body={messages:msgs.slice(-12),lang:document.documentElement.lang};
  if(photo){body.image=photo.data;body.w=photo.w;body.h=photo.h}
  Promise.all([fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json().then(function(j){if(!r.ok)throw j;return j})}),stock()])
  .then(function(res){var q=res[0], extra='';
    b.classList.remove('wait'); b.firstChild.textContent=q.reply||'…';
    if(photo){
      if(q.walls&&q.walls.length){R=roomView(b,photo,q.walls);
        extra=' ('+T.roomnote+': '+(q.room||'')+'; '+q.walls.map(function(w){return w.where+' '+w.w_cm+' × '+w.h_cm+' cm'}).join('; ')+')'}
      else b.appendChild(el('p','none',T.nowall));
    }
    var s=q.show||photo?show(b,q):{note:'',list:[]};
    if(R&&s.list.length){fill(R,s.list);if(photo&&R.v.parentNode===b)hang(R,R.list[0])}
    msgs.push({role:'assistant',content:(q.reply||'')+extra+(s.note?' ('+T.shown+': '+s.note+')':'')});
    if(window.goatcounter&&goatcounter.count)goatcounter.count({path:'find-turn',title:photo?'photo':q.show?'search':'talk',event:true});
  }).catch(function(){b.classList.remove('wait');b.firstChild.textContent=T.failed;msgs.pop()})
  .then(function(){busy=false})}
// a photo is shrunk to 1280 pixels and re-encoded here, which also drops its location data, before it is sent
function shrink(f){
  var bmp=window.createImageBitmap?createImageBitmap(f,{imageOrientation:'from-image'}).catch(function(){return createImageBitmap(f)}):Promise.reject();
  return bmp.catch(function(){return new Promise(function(ok,no){var fr=new FileReader();fr.onload=function(){var i=new Image();i.onload=function(){ok(i)};i.onerror=no;i.src=fr.result};fr.onerror=no;fr.readAsDataURL(f)})})
  .then(function(im){var w=im.width,h=im.height,k=Math.min(1,1280/Math.max(w,h));w=Math.round(w*k);h=Math.round(h*k);
    var c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(im,0,0,w,h);
    var url=c.toDataURL('image/jpeg',.85);return {url:url,data:url.slice(url.indexOf(',')+1),w:w,h:h}})}
file.addEventListener('change',function(){var f=file.files&&file.files[0];file.value='';if(!f||busy)return;
  stock().catch(function(){});shrink(f).then(function(p){send(input.value,p)}).catch(function(){bubble('them',T.badphoto)})});
form.addEventListener('submit',function(ev){ev.preventDefault();send(input.value)});
Array.prototype.forEach.call(document.querySelectorAll('.starter'),function(s){s.addEventListener('click',function(){send(s.textContent)})});
if(!api){form.hidden=true}
input.addEventListener('focus',function(){stock().catch(function(){})},{once:true});   // the stock as the visitor starts typing
})();
"""

CSS = BM.CSS + """
.chat{display:grid;gap:18px;max-width:1040px}
.log{display:grid;gap:16px}
.msg p{margin:0}
.msg.you{justify-self:end;max-width:min(560px,90%);background:var(--raise);border:1px solid var(--rule);padding:10px 14px;font:400 1.05rem/1.4 var(--serif)}
.msg.them>p:first-child{font:400 1.18rem/1.45 var(--serif);max-width:62ch}
.msg.wait>p:first-child{color:var(--grey)}
.search{margin:10px 0 0!important;font:500 .72rem/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--grey)}
.none{margin-top:10px!important;color:var(--grey)}
.starters{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:18px 14px;margin-top:14px}
.card{display:grid;align-content:start;gap:4px}
.card .out{display:grid;gap:3px;text-decoration:none}
.card img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:var(--field)}
.card .cap{padding-top:5px;font-size:.78rem;line-height:1.3;color:var(--grey)}
.card .cap i{display:block;font:italic 400 1rem/1.2 var(--serif);color:var(--ink)}
.card .out:hover .cap i{text-decoration:underline}
.card .meta{font-size:.74rem;color:var(--grey);line-height:1.3}
.card .price{font-size:.78rem;color:var(--grey)}.card .price b{font:500 .86rem/1.3 var(--mono);color:var(--ink);margin-right:4px}
.card .rec{font-size:.72rem;color:var(--grey)}
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

def page(lang, ver, api, labels):
    t = T[lang]
    me, other = f"{BASE}/{t['file']}", f"{BASE}/{t['other']}"
    tj = json.dumps({k: t[k] for k in ("more", "at", "noprice", "none", "thinking", "failed", "record", "kinds", "sizes", "under", "over", "shown", "hash",
                                       "yourroom", "looking", "photomsg", "wallw", "drag", "onwall", "fits", "roomnote", "nowall", "badphoto",
                                       "choose", "hangmore", "remove", "together", "frames", "reset", "ar", "arwait", "arfail", "arsafari")}, ensure_ascii=False).replace("</", "<\\/")
    lj = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")
    ask = (api.rstrip("/") + "/ask") if api else ""
    starters = "".join(f'<button type="button" class="chip starter">{e(s)}</button>' for s in t["starters"])
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{H.STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(t["h"])} · museaal.ee</title><meta name="description" content="{e(t["lede"][:290])}">'
            f'<link rel="canonical" href="{me}"><link rel="alternate" hreflang="{lang}" href="{me}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{other}">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
            f'<style>{CSS}</style>{H.GC}</head><body><div class="wrap">'
            f'<nav><a href="{BASE}/{"" if lang == "en" else "#lang=et"}">{e(t["site"])}</a> › {e(t["h"])} · <a href="{other}" hreflang="{"et" if lang == "en" else "en"}">{e(t["other_l"])}</a></nav>'
            f'<header><h1>{e(t["h"])}</h1><p class="lede">{e(t["lede"])}</p></header>'
            f'<section class="chat" id="chat" data-api="{e(ask)}" data-src="data/stock.json?v={ver}">'
            f'<div class="log" id="log" aria-live="polite"><div class="msg them"><p>{e(t["hello"])}</p><div class="starters">{starters}</div></div></div>'
            f'<form class="ask" id="ask"><label for="q">{e(t["label"])}</label><input id="q" type="text" maxlength="400" autocomplete="off" placeholder="{e(t["ph"])}">'
            f'<button class="btn solid" type="submit">{e(t["send"])}</button>'
            f'<input id="photo" type="file" accept="image/*" hidden><label for="photo" class="btn photobtn" role="button" tabindex="0">{e(t["photo"])}</label></form></section>'
            f'<footer>{e(t["note"])} {H.CONTACT[lang]}</footer></div>'
            f'<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/"}}}}</script>'
            f'<script type="application/json" id="t">{tj}</script><script type="application/json" id="labels">{lj}</script><script>{JS}</script></body></html>')

def main():
    d = data()
    blob = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    ver = hashlib.sha1(blob.encode()).hexdigest()[:8]
    open("site/data/stock.json", "w", encoding="utf-8").write(blob)
    M = json.load(open("data/moods.json", encoding="utf-8"))["words"]
    urls = []
    for lang in ("en", "et"):
        labels = {w["en"]: (w["et"] if lang == "et" else BM.LABEL_EN.get(w["en"], w["en"])) for w in M}
        open(f"site/{T[lang]['file']}", "w", encoding="utf-8").write(page(lang, ver, API, labels)); urls.append(f"{BASE}/{T[lang]['file']}")
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    W_ = d["works"]
    print(f"  find a work    {len(W_):,} works for sale, {sum(1 for w in W_ if w[8]):,} with a price, {sum(1 for w in W_ if w[12]):,} with moods; "
          f"stock.json {len(blob) // 1024} KB; assistant {'at the Worker' if API else 'not set up'}")

if __name__ == "__main__":
    main()
