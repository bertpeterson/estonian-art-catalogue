# -*- coding: utf-8 -*-
"""The account page: /account.html and /konto.html.

Signed in (list-sync.js keeps the session in this browser): the address, the news emails on or off, sign out, and
at the foot, set apart, deleting the account after a second click. Signed out: the sign-in form, the same one the
masthead strip has. Everything the page does is a call list-sync.js already makes to the Worker (login, logout,
news, delete); turning the news emails on is a sign-in link with the box ticked, which is how the Worker keeps an
address for them. Strings from i18n.py. Not in the sitemap, and noindex: there is nothing here for a search engine.
Run before csp.py, which hashes the inline script.
"""
import json, html
import list_sync as LS

e = lambda s: html.escape(str(s or ""), quote=True)
STAMP = "<script>try{if(localStorage.getItem(\"ekr:theme\")===\"light\")document.documentElement.setAttribute(\"data-theme\",\"light\")}catch(e){}</script>"
GC = '<script data-goatcounter="https://museaal.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'
I18N = json.load(open("i18n.json", encoding="utf-8"))
KEYS = ["acc_h", "acc_lede", "acc_who", "acc_signout", "acc_news_h", "acc_news_on", "acc_news_off", "acc_news_confirm",
        "acc_del_h", "acc_del_note", "acc_delete", "acc_del_yes", "acc_del_no", "acc_del_sure", "acc_signin_h",
        "acc_signin_lede", "acc_email", "acc_send", "acc_news", "acc_off", "acc_sent", "acc_busy", "acc_bad", "acc_robot",
        "acc_failed", "acc_expired", "acc_gone", "acc_out", "acc_deleted", "acc_unsub", "acc_unsub_bad"]
PAGE = {"en": dict(file="account", other="konto", other_l="Eesti keeles", site="Estonian Art Catalogue", home="./"),
        "et": dict(file="konto", other="account", other_l="In English", site="Eesti Kunstikataloog", home="./#lang=et")}

CSS = (":root{--paper:#0B0C0E;--field:#15171A;--ink:#F1F2F4;--ink-soft:#C7CACE;--grey:#8B9098;--rule:#2B2E34;--rule-soft:#212429;--warn:#E5484D;"
       "--serif:'Newsreader','Iowan Old Style',Georgia,serif;--sans:'Archivo','Helvetica Neue',Arial,sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}"
       ":root[data-theme=light]{--paper:#FFFFFF;--field:#F5F6F8;--ink:#0B0C0E;--ink-soft:#33363B;--grey:#6C7178;--rule:#DCDFE3;--rule-soft:#EBEDF0;--warn:#C62A2F}"
       "*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 var(--sans);-webkit-font-smoothing:antialiased}"
       ".pg{max-width:760px;margin:0 auto;padding:22px 32px 40px}a{color:inherit}"
       ".top{display:flex;justify-content:space-between;align-items:baseline;gap:16px;padding-bottom:14px;border-bottom:1px solid var(--rule)}"
       ".wm{font-family:var(--serif);font-size:1.15rem;font-weight:500;text-decoration:none}.wm:hover{text-decoration:underline}"
       ".eb{font-family:var(--mono);font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;color:var(--grey)}a.eb{text-decoration:none;border-bottom:1px solid var(--rule)}a.eb:hover{color:var(--ink)}"
       ".mast{padding:34px 0 22px;border-bottom:1px solid var(--ink)}"
       "h1{font-family:var(--serif);font-weight:500;font-size:2.6rem;line-height:1.05;letter-spacing:-.015em;margin:0 0 12px}"
       ".lede{margin:0;max-width:60ch;color:var(--ink-soft);font-size:.95rem}"
       ".row{display:flex;justify-content:space-between;align-items:center;gap:16px 24px;flex-wrap:wrap;padding:22px 0;border-bottom:1px solid var(--rule-soft)}"
       ".row .v{display:block;margin-top:4px;font-family:var(--serif);font-size:1.3rem;word-break:break-all}"
       ".row .s{display:block;margin-top:4px;color:var(--ink-soft)}"
       ".btn{font:500 .7rem/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;background:none;color:var(--ink);border:1px solid var(--ink);padding:10px 14px;cursor:pointer}"
       ".btn:hover{background:var(--ink);color:var(--paper)}.btn:disabled{opacity:.5;cursor:default}"
       ".btn.warn{color:var(--warn);border-color:var(--warn)}.btn.warn:hover{background:var(--warn);color:var(--paper)}"
       ".btn.plain{border-color:var(--rule);color:var(--grey)}.btn.plain:hover{background:none;color:var(--ink);border-color:var(--ink)}"
       ".sw{position:relative;flex:none;width:46px;height:26px;border-radius:13px;border:1px solid var(--grey);background:var(--field);cursor:pointer;padding:0}"
       ".sw::after{content:'';position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:var(--grey);transition:transform .15s}"
       ".sw[aria-checked=true]{background:var(--ink);border-color:var(--ink)}.sw[aria-checked=true]::after{transform:translateX(20px);background:var(--paper)}"
       ".sw:disabled{opacity:.5;cursor:default}"
       ".msg{margin:18px 0 0;padding:10px 12px;border-left:2px solid var(--ink);background:var(--field);color:var(--ink-soft);font-size:.9rem}"
       ".danger{margin-top:96px;padding-top:22px;border-top:1px solid var(--rule)}"
       "h2{font-family:var(--serif);font-weight:500;font-size:1.4rem;margin:0 0 6px}.danger p{margin:0 0 16px;color:var(--ink-soft);font-size:.9rem;max-width:60ch}"
       ".sure{display:flex;flex-wrap:wrap;align-items:center;gap:12px}.sure b{font-weight:500;flex-basis:100%}"
       ".form{display:flex;flex-wrap:wrap;gap:12px;margin-top:22px}"
       ".form input[type=email]{flex:1 1 260px;font:15px var(--sans);color:var(--ink);background:var(--field);border:1px solid var(--rule);padding:9px 12px}"
       ".form input[type=email]:focus{outline:none;border-color:var(--ink)}"
       ".form label{flex-basis:100%;color:var(--ink-soft);font-size:.9rem}"
       ".foot{margin-top:44px;padding-top:14px;border-top:1px solid var(--rule);color:var(--grey);font-size:.8rem}.foot a{color:var(--ink-soft)}"
       "@media(max-width:700px){.pg{padding:16px 16px 32px}h1{font-size:2rem}.danger{margin-top:72px}}")

JS = r"""(function(){
var T=JSON.parse(document.getElementById("acc-t").textContent),LANG=document.documentElement.lang,ML=window.museaalList;
var app=document.getElementById("acc"),h1=document.querySelector("h1"),lede=document.querySelector(".lede");
var asked=false,sure=false,busy=false;
function h(tag,attrs,kids){var el=document.createElement(tag);for(var k in attrs||{})if(k==="text")el.textContent=attrs[k];else el.setAttribute(k,attrs[k]);
  (kids||[]).forEach(function(c){if(c)el.appendChild(c)});return el}
function say(){var n=ML.note();if(!n||n==="in")return null;
  var t=n==="sent"&&asked&&ML.who()?T.acc_news_confirm.replace("{e}",ML.who()):T["acc_"+n];return t?h("p",{"class":"msg",role:"status",text:t}):null}
function draw(){
  app.textContent="";
  if(!ML){h1.textContent=T.acc_h;lede.textContent=T.acc_off;return}
  var who=ML.who(),m=say();
  if(!who){
    h1.textContent=T.acc_signin_h;lede.textContent=T.acc_signin_lede;document.title=T.acc_signin_h+" · museaal.ee";
    var inp=h("input",{type:"email",id:"acc-email",autocomplete:"email",spellcheck:"false",placeholder:T.acc_email,"aria-label":T.acc_email});
    var box=h("input",{type:"checkbox",id:"acc-news"}),send=h("button",{type:"button","class":"btn",text:T.acc_send});
    var form=h("div",{"class":"form"},[inp,send,h("label",{},[box,document.createTextNode(" "+T.acc_news)])]);
    var go=function(){var v=inp.value.trim();if(!v||!inp.checkValidity()){inp.focus();return}
      inp.disabled=send.disabled=true;ML.signIn(v,LANG,form,box.checked)};
    send.addEventListener("click",go);inp.addEventListener("keydown",function(ev){if(ev.key==="Enter")go()});
    app.appendChild(form);if(m)app.appendChild(m);
    if(ML.note()!=="sent")inp.focus();
    return}
  h1.textContent=T.acc_h;lede.textContent=T.acc_lede;document.title=T.acc_h+" · museaal.ee";
  var out=h("button",{type:"button","class":"btn",text:T.acc_signout});
  out.addEventListener("click",function(){ML.signOut()});
  app.appendChild(h("div",{"class":"row"},[h("div",{},[h("span",{"class":"eb",text:T.acc_who}),h("span",{"class":"v",text:who})]),out]));
  var on=ML.news(),sw=h("button",{type:"button",role:"switch","class":"sw","aria-checked":String(on),"aria-labelledby":"acc-news-l"});
  if(busy)sw.disabled=true;
  sw.addEventListener("click",function(){busy=true;sw.disabled=true;
    var p=on?ML.stopNews():(asked=true,ML.signIn(who,LANG,app,true));
    p.then(function(){busy=false;draw()})});
  app.appendChild(h("div",{"class":"row"},[h("div",{},[h("span",{"class":"eb",text:T.acc_news_h}),
    h("span",{"class":"s",id:"acc-news-l",text:on?T.acc_news_on:T.acc_news_off})]),sw]));
  if(m)app.appendChild(m);
  var del=h("div",{"class":"danger"},[h("h2",{text:T.acc_del_h}),h("p",{text:T.acc_del_note})]);
  if(!sure){var b=h("button",{type:"button","class":"btn warn",text:T.acc_delete});
    b.addEventListener("click",function(){sure=true;draw();var y=document.getElementById("acc-del-yes");if(y)y.focus()});del.appendChild(b)}
  else{var yes=h("button",{type:"button","class":"btn warn",id:"acc-del-yes",text:T.acc_del_yes}),no=h("button",{type:"button","class":"btn plain",text:T.acc_del_no});
    yes.addEventListener("click",function(){yes.disabled=no.disabled=true;ML.remove().then(function(){sure=false;draw()})});
    no.addEventListener("click",function(){sure=false;draw()});
    del.appendChild(h("div",{"class":"sure",role:"alertdialog","aria-label":T.acc_del_sure},[h("b",{text:T.acc_del_sure}),yes,no]))}
  app.appendChild(del)}
addEventListener("museaal:account",function(){if(!ML||!ML.who())sure=false;draw()});
draw();
})();"""

def main():
    for lang in ("en", "et"):
        p, S = PAGE[lang], I18N["EN" if lang == "en" else "ET"]
        t = {k: S[k] for k in KEYS}
        tj = json.dumps(t, ensure_ascii=False).replace("</", "<\\/")
        page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{e(t["acc_h"])} · museaal.ee</title><meta name="robots" content="noindex">'
                f'<link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{p["other"]}">'
                '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
                f'<style>{CSS}</style>{LS.TAG}{GC}</head><body><div class="pg">'
                f'<div class="top"><a class="wm" href="{p["home"]}">{e(p["site"])}</a><a class="eb" href="{p["other"]}">{p["other_l"]}</a></div>'
                f'<header class="mast"><h1>{e(t["acc_h"])}</h1><p class="lede"></p></header><main id="acc"></main>'
                f'<footer class="foot"><a href="{p["home"]}">{e(S["acc_back"])}</a></footer></div>'
                f'<script type="application/json" id="acc-t">{tj}</script>'
                f'<script>{JS}</script></body></html>')
        open(f"site/{p['file']}.html", "w", encoding="utf-8").write(page)
    print("  account page   account.html, konto.html" + ("" if LS.TAG else " (lists off: the page says so)"))

if __name__ == "__main__":
    main()
