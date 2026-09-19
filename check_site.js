// Smoke test of the built site in headless Chrome, before it is deployed.
//   node check_site.js [site dir]        (default: site)
// Serves the folder locally, opens the pages a visitor would, and asserts what
// they must show: the landing's door and wall, an artist view, a search, the
// auction ledger by price, the Estonian page, the figures pages, a static artist
// page -- and that no JavaScript error was thrown. Exit 1 on any failure, so a
// broken build stops the workflow instead of reaching museaal.ee.
// No dependencies: Chrome's DevTools protocol over the WebSocket Node ships with.
const { spawn } = require("child_process"); const fs = require("fs"); const path = require("path");
const DIR = process.argv[2] || "site";
const CHROME = process.env.CHROME || ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser", "/usr/bin/chromium"].find(p => fs.existsSync(p));
if (!CHROME){ console.error("no Chrome found; set CHROME=/path"); process.exit(1); }
const port = 8790 + Math.floor(Math.random() * 100), dport = 9400 + Math.floor(Math.random() * 400);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const server = spawn("python3", ["-m", "http.server", String(port), "--bind", "127.0.0.1"], {cwd: DIR, stdio: "ignore"});
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", `--remote-debugging-port=${dport}`, "--window-size=1400,1000", "--user-data-dir=/tmp/check-site-" + dport, "about:blank"], {stdio: "ignore"});
const failures = [];
const check = (name, ok, detail) => { console.log(`${ok ? "ok  " : "FAIL"} ${name}${detail ? " — " + detail : ""}`); if (!ok) failures.push(name); };
(async () => {
  let targets;
  for (let i = 0; i < 60; i++){ try { targets = await (await fetch(`http://127.0.0.1:${dport}/json`)).json(); if (targets.length) break; } catch(e){} await sleep(250); }
  const ws = new WebSocket(targets.find(t => t.type === "page").webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map(); const errors = [];
  ws.onmessage = m => { const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)){ pending.get(d.id)(d); pending.delete(d.id); }
    if (d.method === "Runtime.exceptionThrown") errors.push(d.params.exceptionDetails.text + " " + (d.params.exceptionDetails.exception || {}).description);
    if (d.method === "Log.entryAdded" && d.params.entry.level === "error" && !/favicon|net::ERR_|Failed to load resource/.test(d.params.entry.text)) errors.push(d.params.entry.text); };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({id: i, method, params})); });
  await send("Runtime.enable"); await send("Log.enable");
  const open = async (hash, wait = 4000) => { await send("Page.navigate", {url: `http://127.0.0.1:${port}/${hash}`}); await sleep(wait); };
  const ev = async expr => { const r = await send("Runtime.evaluate", {expression: expr, returnByValue: true, awaitPromise: true}); return r.result && r.result.result ? r.result.result.value : null; };

  // The first visit is made on a throttled connection, so the index arrives after the
  // load event as it does on a real one; the worker was once registered on load and
  // never ran for anyone whose index took longer than the page.
  await send("Network.enable"); await send("Network.emulateNetworkConditions", {offline: false, latency: 40, downloadThroughput: 60e6 / 8, uploadThroughput: 10e6 / 8});
  await open("", 9000);
  await send("Network.emulateNetworkConditions", {offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1});
  check("landing: sixteen names", (await ev(`document.querySelectorAll("[data-door=a]").length`)) === 16);
  check("landing: the names are links a crawler can follow", (await ev(`document.querySelectorAll('a[data-door=a][href^="a/"]').length`)) === 16
        && (fs.readFileSync(path.join(DIR, "index.html"), "utf-8").match(/href="a\/[a-z0-9-]+\.html" data-door="a"/g) || []).length === 16);
  check("landing: seventy-two tiles", (await ev(`document.querySelectorAll(".wt").length`)) === 72);
  check("landing: masthead figures", (await ev(`+document.querySelector("#stat-w").textContent.replace(/[^0-9]/g,"")`)) > 90000);
  // the worker stores the content-named data files on the first visit; a reload is then answered from the cache
  const cached = await ev(`(async () => { for (let i = 0; i < 40; i++){ const c = await caches.open("museaal-v1"); const ks = (await c.keys()).map(k => k.url); if (ks.some(u => /index\\.json\\?v=/.test(u))) return ks.length; await new Promise(r => setTimeout(r, 250)); } return 0; })()`);
  check("service worker: data stored on the first visit", cached > 0, `${cached} entries`);
  await send("Page.reload"); await sleep(5000);
  const sw = await ev(`(() => { const e = performance.getEntriesByType("resource").find(e => /index\\.json\\?v=/.test(e.name)); return e ? {w: e.workerStart > 0, t: e.transferSize} : null; })()`);
  check("service worker: the index comes from the cache on the second", !!sw && sw.w && sw.t === 0, JSON.stringify(sw));
  await open("#artist=konrad-magi", 5000);
  check("artist view: biography", (await ev(`(document.querySelector("#mono-bio")||{}).textContent||""`)).length > 100);
  check("artist view: count line names the artist", /mägi/i.test(await ev(`document.querySelector("#countline").textContent`)));
  check("artist view: a wall of pictures", (await ev(`document.querySelectorAll(".wt").length`)) >= 12);
  check("artist view: similar artists", (await ev(`document.querySelectorAll(".sim-chip").length`)) >= 3);
  await ev(`document.querySelector(".wt").click()`); await sleep(1500);
  check("artist view: a tile opens its record", (await ev(`!!document.querySelector(".wall-open .d-fig")`)) === true);
  check("record: works that look like this", (await ev(`document.querySelectorAll(".wall-open .la-t img").length`)) >= 3);
  check("wall: no detail shard fetched for the pictures", (await ev(`performance.getEntriesByType("resource").filter(e => /data\\/detail\\//.test(e.name)).length`)) <= 1);
  // a link to a picture beyond the first seventy-two tiles opens its record all the same
  await open("#artist=kristjan-raud&open=EKMJ26004G16138", 5000);
  check("deep link: a record beyond the wall's first page opens", /Kevade laul/.test(await ev(`(document.querySelector(".wall-open .r-title")||{}).textContent||""`)));
  await open("#q=Veneetsia&view=list", 4000);
  check("search: rows", (await ev(`document.querySelectorAll(".row").length`)) > 20);
  // the groups are laid out on demand (content-visibility); a row opened deep in the
  // list must stay where it was on the screen when the register is redrawn
  const kept = await ev(`(async () => { const r = [...document.querySelectorAll(".row")]; const x = r[Math.min(r.length - 1, 400)]; x.scrollIntoView({block: "center"}); await new Promise(f => setTimeout(f, 400));
    const before = x.getBoundingClientRect().top; const id = x.querySelector(".row-btn").dataset.id; x.querySelector(".row-btn").click(); await new Promise(f => setTimeout(f, 1200));
    const o = document.querySelector('.row[data-open="true"] .row-btn'); return o && o.dataset.id === id ? Math.abs(o.closest(".row").getBoundingClientRect().top - before) : 9999; })()`);
  check("search: an opened row stays where it was", kept < 3, `${kept}px`);
  await open("#group=auction", 5000);
  check("auctions: highest hammer price first", /€\s?\d{3},?\d{3}/.test(await ev(`(document.querySelector(".row .rl-au")||{}).textContent||""`)));
  await open("#lang=et&artist=eduard-wiiralt", 5000);
  check("estonian: the page speaks Estonian", /KUNSTNIKKU|kunstiseinal/.test(await ev(`document.body.textContent`)));
  await open("#decade=1920", 5000);
  check("decade: wall", (await ev(`document.querySelectorAll(".wt").length`)) >= 12);
  check("no JavaScript errors", errors.length === 0, errors.slice(0, 3).join(" | "));
  for (const [f, needle] of [["stats.html", "The auction record"], ["stats-et.html", "Kataloog arvudes"], ["a/konrad-magi.html", 'class="wt"'], ["a/index.html", "Artists A"],
                             ["k/konrad-magi.html", 'hreflang="en" href="https://museaal.ee/a/konrad-magi.html"'], ["k/index.html", "Kunstnikud A"], ["sitemap.xml", "k/konrad-magi.html"],
                             ["decades/1920.html", 'class="wt"'], ["kumnendid/1920.html", "Eesti kunst 1920ndatel"], ["museums/index.html", "tartu-art-museum.html"], ["ained/maastik.html", "Maastik"], ["sitemap.xml", "subjects/landscape.html"],
                             ["embed/konrad-magi.html", 'target="_top"'], ["embed/et/kumnendid/1920.html", "Eesti kunst 1920ndatel"], ["a/konrad-magi.html", "embed/konrad-magi.html"]]){
    const p = path.join(DIR, f); check(`file: ${f}`, fs.existsSync(p) && fs.readFileSync(p, "utf-8").includes(needle));
  }
  check("artist pages: more than a thousand", fs.readdirSync(path.join(DIR, "a")).length > 1000);
  // every page carries the policy; the browser run above would have logged a violation as an error
  for (const f of ["index.html", "a/konrad-magi.html", "stats.html", "404.html"])
    check(`csp: ${f}`, /http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https:\/\/gc\.zgo\.at 'sha256-/.test(fs.readFileSync(path.join(DIR, f), "utf-8")));
  ws.close(); chrome.kill(); server.kill();
  console.log(failures.length ? `\n${failures.length} check(s) failed` : "\nall checks passed");
  process.exit(failures.length ? 1 : 0);
})().catch(e => { console.error(e); chrome.kill(); server.kill(); process.exit(1); });
