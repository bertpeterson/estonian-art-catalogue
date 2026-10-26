# -*- coding: utf-8 -*-
"""site/admin.html -- the backoffice: the site's own figures on one page, for Bert.

Not linked from anywhere, not in the sitemap, noindex. What it shows:
  accounts     KV keys by kind, every address, new accounts a day          } live, from the Worker's
  visits       GoatCounter's views, pages, referrers, sign-in events       } /admin/stats, which wants
  assistant    questions to Buy Art and readings on the mood page a day  } ADMIN_KEY (worker/README.md)
  stock        works for sale by gallery, and what left since the weekly run: written in here at build time
  pipelines    each workflow's last run, read in the browser from GitHub's public API
The key is asked for once and kept in this browser (localStorage "museaal.admin"). The page loads no
GoatCounter, so opening it counts nothing.
"""
import json, os, re, statistics, collections, datetime, html

e = html.escape
d = json.load(open("data/data.json", encoding="utf-8"))
V = d["vocab"]
api = (json.load(open("data/mood_api.json", encoding="utf-8")).get("url") or "") if os.path.exists("data/mood_api.json") else ""
stock = json.load(open("site/data/stock.json", encoding="utf-8"))
gone = json.load(open("data/stock_gone.json", encoding="utf-8")) if os.path.exists("data/stock_gone.json") else {}

# for sale now: the works Buy Art shows (stock.json rows: [title, artist, year, img, tech, dims, size, kind, price, gallery, ...])
gals = stock["galleries"]
by = collections.defaultdict(list)
for w in stock["works"]: by[w[9]].append(w)
# left since the weekly run: stock_gone.json, the daily check's finds -- the gallery from data.json, where they are past listings now
gal_of = {w["k"]: V["mu"][w["mu"]] for w in d["works"] if w.get("k") in gone and isinstance(w.get("mu"), int)}
today = datetime.date.today()
left = collections.defaultdict(lambda: [0, 0])          # gallery -> [in the last 7 days, sold (the gallery said so)]
for k, (day, sold) in gone.items():
    g = gal_of.get(k, "?")
    if (today - datetime.date.fromisoformat(day)).days < 7: left[g][0] += 1
    left[g][1] += sold
rows = []
for i, g in sorted(enumerate(gals), key=lambda x: -len(by[x[0]])):
    ps = [w[8] for w in by[i] if w[8]]
    rows.append([g, len(by[i]), len({w[1] for w in by[i]}), len(ps), round(statistics.median(ps)) if ps else None, left[g][0], left[g][1]])
for g in left:
    if g not in gals: rows.append([g, 0, 0, 0, 0, left[g][0], left[g][1]])
STOCK = {"built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "works": len(stock["works"]),
         "artists": len({w[1] for w in stock["works"]}), "priced": sum(1 for w in stock["works"] if w[8]),
         "gone": len(gone), "rows": rows}
REPO = "bertpeterson/estonian-art-catalogue"
FLOWS = [["pages.yml", "Build and deploy", "every push"], ["stock.yml", "Stock check", "daily"], ["probe.yml", "Probe", "daily"],
         ["galleries.yml", "Galleries", "Thursdays"], ["auctions.yml", "Auctions", "Mondays"], ["reharvest.yml", "Reharvest", "1st of the month"]]

CSS = ("body{margin:0;padding:28px;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fff;color:#111;max-width:1040px}"
       ":root:not([data-theme=light]) body{background:#0b0c0e;color:#f1f2f4}:root:not([data-theme=light]) a{color:#9ec5ff}"
       ":root:not([data-theme=light]) th,:root:not([data-theme=light]) td,:root:not([data-theme=light]) .card{border-color:#2b2e34!important}"
       ":root:not([data-theme=light]) .m{color:#8b9098!important}:root:not([data-theme=light]) .bars i{background:#c9ccd2}"
       ":root:not([data-theme=light]) input{background:#15171a;color:#f1f2f4;border-color:#2b2e34}"
       "h1{font-weight:500;font-size:2rem;margin:0 0 4px}h2{font-weight:500;font-size:1.25rem;margin:40px 0 10px}h3{font-weight:500;font-size:1rem;margin:22px 0 6px}"
       ".m{color:#6b7078}a{color:#1a5fd0}"
       ".cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px}"
       ".card{border:1px solid #e3e5e8;border-radius:8px;padding:12px 14px}.card b{display:block;font-size:1.7rem;font-weight:500;line-height:1.2}.card span{font-size:.85rem}"
       ".bars{display:flex;align-items:flex-end;gap:2px;height:70px;margin:8px 0 2px}.bars i{flex:1;background:#222;min-height:1px;border-radius:1px 1px 0 0}"
       ".axis{display:flex;justify-content:space-between;font-size:.75rem}"
       "table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{text-align:left;padding:5px 8px 5px 0;border-bottom:1px solid #e3e5e8;vertical-align:top}"
       "th{font-weight:500}.n{text-align:right;font-variant-numeric:tabular-nums}td.p{word-break:break-all}"
       ".two{display:grid;grid-template-columns:1fr 1fr;gap:28px}@media(max-width:720px){body{padding:16px}.two{grid-template-columns:1fr}}"
       "input{font:inherit;padding:7px 10px;border:1px solid #ccd0d5;border-radius:6px;width:260px;max-width:100%}button{font:inherit;padding:7px 14px;margin-left:6px;cursor:pointer}"
       ".ok{color:#1d7f3b}.bad{color:#c0392b}")

JS = r"""
(function () {
  var main = document.getElementById("live"), API = main.getAttribute("data-list-api").replace(/\/?$/, "/") + "admin/stats";
  var STOCK = JSON.parse(document.getElementById("stock").textContent), FLOWS = JSON.parse(document.getElementById("flows").textContent);
  var REPO = main.getAttribute("data-repo");
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function add(p) { for (var i = 1; i < arguments.length; i++) if (arguments[i]) p.appendChild(arguments[i]); return p; }
  function fmt(n) { return n == null ? "—" : Number(n).toLocaleString("en-GB"); }
  function sum(a) { return (a || []).reduce(function (s, x) { return s + x; }, 0); }
  function card(n, label) { return add(el("div", "card"), el("b", null, fmt(n)), el("span", "m", label)); }
  function bars(days, vals, label) {
    var w = el("div"), b = el("div", "bars"), max = Math.max.apply(null, vals.concat([1]));
    vals.forEach(function (v, i) { var x = el("i"); x.style.height = (v / max * 100) + "%"; x.title = days[i] + ": " + v; b.appendChild(x); });
    b.setAttribute("role", "img"); b.setAttribute("aria-label", label + ", " + sum(vals) + " in 30 days, most in a day " + Math.max.apply(null, vals.concat([0])));
    return add(w, b, add(el("div", "axis m"), el("span", null, days[0]), el("span", null, "max " + fmt(max)), el("span", null, days[days.length - 1])));
  }
  function table(head, rows, num) {
    var t = el("table"), h = el("tr");
    head.forEach(function (x, i) { h.appendChild(el("th", num[i] ? "n" : null, x)); });
    add(t, add(el("thead"), h));
    var tb = el("tbody");
    rows.forEach(function (r) { var tr = el("tr"); r.forEach(function (c, i) { tr.appendChild(el("td", num[i] ? "n" : i === 0 ? "p" : null, num[i] ? fmt(c) : c)); }); tb.appendChild(tr); });
    return add(t, tb);
  }
  function section(title, note) { var s = el("section"); add(s, el("h2", null, title)); if (note) add(s, el("p", "m", note)); return s; }
  function key() { try { return localStorage.getItem("museaal.admin") || ""; } catch (e) { return ""; } }

  function ask(msg) {
    main.textContent = "";
    var p = el("p", msg ? "bad" : "m", msg || "The admin key (ADMIN_KEY in the Worker) — kept in this browser."), i = el("input"), b = el("button", null, "Open");
    i.type = "password"; i.autocomplete = "current-password"; i.setAttribute("aria-label", "Admin key");
    function go() { try { localStorage.setItem("museaal.admin", i.value.trim()); } catch (e) {} load(); }
    b.onclick = go; i.onkeydown = function (ev) { if (ev.key === "Enter") go(); };
    add(main, p, add(el("div"), i, b)); i.focus();
  }

  function load() {
    var k = key(); if (!k) return ask();
    main.textContent = "Loading…";
    fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: k }) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; }); })
      .then(function (j) {
        if (j.status === 401) { try { localStorage.removeItem("museaal.admin"); } catch (e) {} return ask("Wrong key."); }
        if (j.status !== 200) { main.textContent = j.error || "The Worker answered " + j.status + "."; return; }
        show(j);
      }, function () { main.textContent = "The Worker could not be reached."; });
  }

  function show(j) {
    main.textContent = "";
    var D = j.days, K = j.keys || {};
    var s = section("Accounts", "Counted now in the KV store. An account is made when someone opens their sign-in link.");
    add(s, add(el("div", "cards"), card(K.accounts, "accounts"), card(K.news, "want news emails"), card(K.devices, "devices signed in"), card(K.links, "sign-in links waiting")));
    if (j.signup) add(s, el("h3", null, "New accounts a day — " + fmt(sum(j.signup)) + " in 30 days"), bars(D, j.signup, "New accounts a day"));
    if (j.people && j.people.length) {
      add(s, el("h3", null, "Who"));
      add(s, table(["Address", "Since", "Works", "Last change", "News"], j.people.map(function (p) {
        return [p[0] || "(from before 15 Oct, kept at next sign-in)", p[1] || "—", p[2], p[3] ? new Date(p[3]).toISOString().slice(0, 10) : "—", p[4] ? "yes" : ""];
      }), [0, 0, 1, 0, 0]));
      // the same rows as a file, made here in the browser: nothing more leaves the Worker
      var dl = el("button", null, "Download CSV");
      dl.style.marginLeft = "0";
      dl.onclick = function () {
        // a cell that starts like a formula gets a ' first, so a spreadsheet shows an address as text and never runs it
        var q = function (v) { v = v == null ? "" : String(v); if (/^[=+\-@\t\r]/.test(v)) v = "'" + v; return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
        var lines = [["address", "since", "works", "last_change", "news"]].concat(j.people.map(function (p) {
          return [p[0], p[1], p[2], p[3] ? new Date(p[3]).toISOString().slice(0, 10) : "", p[4] ? "yes" : "no"];
        }));
        var a = el("a"), url = URL.createObjectURL(new Blob([lines.map(function (r) { return r.map(q).join(","); }).join("\n") + "\n"], { type: "text/csv" }));
        a.href = url; a.download = "museaal-accounts-" + new Date().toISOString().slice(0, 10) + ".csv";
        document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      };
      add(s, add(el("p"), dl));
    }
    main.appendChild(s);

    s = section("Visits", "GoatCounter, the last 30 days.");
    var g = j.goat;
    if (!g) add(s, el("p", "m", j.goat_error ? "GoatCounter did not answer: " + j.goat_error : "Add GOATCOUNTER_TOKEN to the Worker to see visits here (worker/README.md)."));
    else {
      var ev = {}; (g.events_list || []).forEach(function (x) { ev[x.path] = x.count; });
      // a click through to a gallery: "find-out" from Buy art, "out-artist" and "out-forsale" from the pages that list stock
      var outs = (g.events_list || []).reduce(function (t, x) { return t + (/^(find-out|out-)/.test(x.path) ? x.count : 0); }, 0);
      add(s, add(el("div", "cards"), card(g.total - (g.events || 0), "page views"), card(outs, "clicks to a gallery"), card(ev["sign-in-link-sent"] || 0, "sign-in links sent"), card(ev["signed-in"] || 0, "sign-ins")));
      // /find and /find.html are one page (links from before the clean addresses still carry .html): counted together
      var pg = {}; (g.pages || []).forEach(function (r) { var k = r[0].replace(/\.html$/, "").replace(/\/index$/, "/"); pg[k] = (pg[k] || 0) + r[1]; });
      var pages = Object.keys(pg).map(function (k) { return [k, pg[k]]; }).sort(function (a, b) { return b[1] - a[1]; });
      add(s, el("h3", null, "Views a day"), bars(D, D.map(function (d) { var x = (g.days || []).filter(function (y) { return y[0] === d; })[0]; return x ? x[1] : 0; }), "Views a day"));
      var two = el("div", "two");
      add(two, add(el("div"), el("h3", null, "Top pages"), table(["Page", "Views"], pages, [0, 1])),
               add(el("div"), el("h3", null, "Referrers"), table(["From", "Visits"], g.refs || [], [0, 1])));
      add(s, two);
      if ((g.events_list || []).length) add(s, el("h3", null, "Events"), table(["Event", "Count"], g.events_list.map(function (x) { return [x.path, x.count]; }), [0, 1]));
    }
    add(s, add(el("p", "m"), document.createTextNode("More at "), Object.assign(el("a", null, "museaal.goatcounter.com"), { href: "https://museaal.goatcounter.com/" })));
    main.appendChild(s);

    s = section("Assistant", "Counted by the Worker, a day at a time. Spend is in the Anthropic console.");
    if (j.ask) {
      add(s, add(el("div", "cards"), card(sum(j.ask), "Buy Art questions, 30 days"), card(sum(j.mood), "mood readings, 30 days")));
      add(s, el("h3", null, "Buy Art questions a day"), bars(D, j.ask, "Buy Art questions a day"), el("h3", null, "Mood readings a day"), bars(D, j.mood, "Mood readings a day"));
    }
    main.appendChild(s);
    add(main, el("p", "m", "Figures read " + new Date(j.at).toLocaleString("en-GB") + "."));
  }

  // stock, written in at build time
  var st = document.getElementById("stockout");
  add(st, add(el("div", "cards"), card(STOCK.works, "works for sale"), card(STOCK.artists, "artists with work for sale"), card(STOCK.priced, "with a price"), card(STOCK.gone, "left since the weekly run")));
  add(st, el("h3", null, "By gallery"), table(["Gallery", "Works", "Artists", "Priced", "Median €", "Left, 7 days", "Sold"], STOCK.rows, [0, 1, 1, 1, 1, 1, 1]));

  // pipelines, from GitHub's public API
  var pl = document.getElementById("pipes"), t = el("table"), tb = el("tbody");
  add(t, add(el("thead"), add(el("tr"), el("th", null, "Workflow"), el("th", null, "Runs"), el("th", null, "Last run"), el("th", null, "Result"))), tb);
  pl.appendChild(t);
  FLOWS.forEach(function (f) {
    var tr = el("tr"), when = el("td", "m", "…"), res = el("td");
    add(tb, add(tr, el("td", null, f[1]), el("td", "m", f[2]), when, res));
    fetch("https://api.github.com/repos/" + REPO + "/actions/workflows/" + f[0] + "/runs?per_page=1")
      .then(function (r) { return r.json(); })
      .then(function (x) {
        var r = (x.workflow_runs || [])[0]; if (!r) { when.textContent = "—"; return; }
        when.textContent = new Date(r.run_started_at || r.created_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
        var c = r.status === "completed" ? r.conclusion : r.status.replace("_", " "), a = el("a", c === "success" ? "ok" : r.status === "completed" ? "bad" : null, c);
        a.href = r.html_url; res.appendChild(a);
      }, function () { when.textContent = "GitHub did not answer"; });
  });

  load();
})();
"""

page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<script>try{if(localStorage.getItem("ekr:theme")==="light")document.documentElement.setAttribute("data-theme","light")}catch(e){}</script>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">'
        f'<title>Backoffice — museaal.ee</title><style>{CSS}</style></head><body>'
        '<h1>Backoffice</h1><p class="m">museaal.ee, for its keeper. <a href="/">Home</a> · <a href="/stats">The catalogue in figures</a></p>'
        f'<div id="live" data-list-api="{e(api)}" data-repo="{REPO}"><p class="m">Loading…</p></div>'
        f'<section><h2>Stock</h2><p class="m">From the build of {STOCK["built"]}. "Left" and "Sold" are the daily check\'s finds since the weekly gallery run; "Sold" when the gallery said so.</p><div id="stockout"></div></section>'
        '<section><h2>Pipelines</h2><p class="m">Each workflow\'s last run on GitHub.</p><div id="pipes"></div></section>'
        '<script type="application/json" id="stock">' + json.dumps(STOCK, ensure_ascii=False).replace("</", "<\\/") + '</script>'
        f'<script type="application/json" id="flows">{json.dumps(FLOWS)}</script>'
        f'<script>{JS}</script></body></html>')
open("site/admin.html", "w", encoding="utf-8").write(page)
print(f"  backoffice     site/admin.html: {STOCK['works']:,} works for sale, {len(rows)} galleries")
