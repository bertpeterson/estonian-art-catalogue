// My List across a visitor's devices, once they sign in with their email (the Worker's /list/*, worker/template.js).
// list_sync.py puts this in the head of every page that has the list, with the Worker's address. Signed out it only
// reads a sign-in link's token from the address -- before the page's own script reads the address -- and keeps it
// out of history. Signed in, it brings the list in step with the Worker's copy when a page opens or comes back into
// view, and two seconds after a change: it sends what was added and removed since the two last agreed and takes the
// Worker's list back, keeping whatever changed here meanwhile. The pages call museaalList.changed() after they save
// the list, and listen for "museaal:list" (a list came in) and "museaal:account" (signed in or out, a link sent).
(function () {
  var me = document.currentScript, API = me && me.getAttribute("data-list-api");
  if (!API) return;
  var LIST = "museaal.shortlist", ACC = "museaal.account", timer = 0, busy = null, again = false, last = 0, note = "";
  function read(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } }
  function write(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function list() { var a = read(LIST); return Array.isArray(a) ? a.filter(function (k) { return typeof k === "string"; }) : []; }
  function acc() { var a = read(ACC); return a && typeof a.s === "string" ? a : null; }
  function tell(name) { try { window.dispatchEvent(new Event(name)); } catch (e) {} }
  function has(a, k) { return a.indexOf(k) >= 0; }
  function post(path, body, keep) {
    return fetch(API.replace(/\/?$/, "/") + "list/" + path, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), keepalive: !!keep })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; }); });
  }
  // Turnstile before a sign-in link is sent (the Worker's /list/login wants it when it has a secret): the widget is
  // put in the page's box only for that, shows itself only if Cloudflare wants a click, and goes once it answers.
  // The site key (data-ts) works on museaal.ee only, Cloudflare's test keys (1x00...) anywhere; elsewhere no token.
  var KEY = (me && me.getAttribute("data-ts")) || "";
  if (!(/(^|\.)museaal\.ee$/.test(location.hostname) || /^[123]x0+A[AB]$/.test(KEY))) KEY = "";
  function turnstile() {
    return new Promise(function (ok) {
      if (window.turnstile) return ok(window.turnstile);
      if (!document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]')) {
        var s = document.createElement("script");
        s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"; s.async = true; document.head.appendChild(s);
      }
      var n = 0, t = setInterval(function () { if (window.turnstile || ++n > 150) { clearInterval(t); ok(window.turnstile || null); } }, 100);
    });
  }
  function human(box) {
    if (!KEY) return Promise.resolve("");
    return turnstile().then(function (ts) {
      if (!ts) return "";
      return new Promise(function (ok) {
        var el = document.createElement("div"), done = false, id = null;
        el.style.flexBasis = "100%";
        (box || document.body).appendChild(el);
        function end(t) { if (done) return; done = true; try { if (id !== null) ts.remove(id); } catch (e) {} el.remove(); ok(t || ""); }
        try { id = ts.render(el, { sitekey: KEY, appearance: "interaction-only", callback: end, "error-callback": function () { end(""); } }); }
        catch (e) { end(""); }
        setTimeout(function () { end(""); }, 60000);
      });
    });
  }
  function setNews(on, why) {
    var a = acc(); if (a && !!a.news !== on) { a.news = on; write(ACC, a); if (!why) tell("museaal:account"); }
    if (why) { note = why; tell("museaal:account"); }
  }
  function out(why) { write(ACC, null); note = why; tell("museaal:account"); }
  function sync(keep) {
    var a = acc(); if (!a) return Promise.resolve();
    if (busy) { again = true; return busy; }
    var sent = list(), base = a.base || [];
    last = Date.now();
    busy = post("sync", { session: a.s, add: sent.filter(function (k) { return !has(base, k); }),
                          remove: base.filter(function (k) { return !has(sent, k); }) }, keep).then(function (j) {
      if (j.status === 401) return out("gone");
      if (!Array.isArray(j.items) || !acc()) return;
      // what changed here while the request was out stays changed, and goes with the next one
      var now = list(), mine = j.items.filter(function (k) { return has(now, k) || !has(sent, k); });
      now.forEach(function (k) { if (!has(sent, k) && !has(mine, k)) mine.push(k); });
      var b = acc(); b.base = j.items; write(ACC, b);
      if (typeof j.news === "boolean") setNews(j.news);
      if (JSON.stringify(mine) !== JSON.stringify(now)) { write(LIST, mine); tell("museaal:list"); }
      if (JSON.stringify(mine) !== JSON.stringify(j.items)) again = true;
    }).catch(function () {}).then(function () { busy = null; if (again) { again = false; sync(); } });
    return busy;
  }

  var h = new URLSearchParams(location.hash.replace(/^#/, "")), tok = h.get("login");
  if (tok) {
    h.delete("login");
    var rest = h.toString().replace(/%2C/g, ",");
    try { history.replaceState(null, "", location.pathname + location.search + (rest ? "#" + rest : "")); } catch (e) {}
    post("verify", { token: tok }).then(function (j) {
      if (!j.session) { note = j.status === 410 ? "expired" : "failed"; tell("museaal:account"); return; }
      // the first sync sends everything kept here as added: the two lists are joined, nothing lost
      write(ACC, { s: j.session, e: j.email, base: [], news: !!j.news }); note = "in"; tell("museaal:account");
      return sync();
    }, function () { note = "failed"; tell("museaal:account"); });
  } else if (acc()) sync();
  // the unsubscribe link from a news email: #unsub=<account>.<seal>, signed in or not
  var unsub = h.get("unsub");
  if (unsub) {
    h.delete("unsub");
    var left = h.toString().replace(/%2C/g, ",");
    try { history.replaceState(null, "", location.pathname + location.search + (left ? "#" + left : "")); } catch (e) {}
    post("unsubscribe", { token: unsub }).then(function (j) { setNews(false, j.ok ? "unsub" : "unsub_bad"); },
      function () { note = "unsub_bad"; tell("museaal:account"); });
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && acc() && Date.now() - last > 30000) sync();
    if (document.visibilityState === "hidden" && timer) { clearTimeout(timer); timer = 0; sync(true); }
  });

  window.museaalList = {
    changed: function () { if (!acc()) return; clearTimeout(timer); timer = setTimeout(function () { timer = 0; sync(); }, 2000); },
    who: function () { var a = acc(); return a ? a.e : ""; },
    // whether the signed-in account gets the news emails (n:<account> in the Worker), and stopping them
    news: function () { var a = acc(); return !!(a && a.news); },
    stopNews: function () {
      var a = acc(); if (!a) return Promise.resolve();
      return post("news", { session: a.s }).then(function (j) { if (j.ok) setNews(false, "unsub"); else { note = "failed"; tell("museaal:account"); } },
        function () { note = "failed"; tell("museaal:account"); });
    },
    // what last happened, for the page to say: sent, busy, bad, robot, failed, in, expired, gone, out, deleted, unsub, unsub_bad
    note: function () { return note; },
    signIn: function (email, lang, box, news) {
      return human(box).then(function (t) {
        var b = { email: email, lang: lang, news: !!news }; if (t) b.human = t;
        return post("login", b);
      }).then(function (j) {
        note = j.ok ? "sent" : j.status === 429 ? "busy" : j.status === 400 ? "bad" : j.status === 401 ? "robot" : "failed";
      }, function () { note = "failed"; }).then(function () { tell("museaal:account"); });
    },
    signOut: function () { var a = acc(); if (a) post("logout", { session: a.s }).catch(function () {}); out("out"); },
    remove: function () {
      var a = acc(); if (!a) return Promise.resolve();
      return post("delete", { session: a.s }).then(function (j) { if (j.ok) out("deleted"); else { note = "failed"; tell("museaal:account"); } },
        function () { note = "failed"; tell("museaal:account"); });
    },
  };
})();
