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

  await open("", 6000);
  check("landing: sixteen names", (await ev(`document.querySelectorAll("[data-door=a]").length`)) === 16);
  check("landing: seventy-two tiles", (await ev(`document.querySelectorAll(".wt").length`)) === 72);
  check("landing: masthead figures", (await ev(`+document.querySelector("#stat-w").textContent.replace(/[^0-9]/g,"")`)) > 90000);
  await open("#artist=konrad-magi", 5000);
  check("artist view: count line names the artist", /mägi/i.test(await ev(`document.querySelector("#countline").textContent`)));
  check("artist view: a wall of pictures", (await ev(`document.querySelectorAll(".wt").length`)) >= 12);
  check("artist view: similar artists", (await ev(`document.querySelectorAll(".sim-chip").length`)) >= 3);
  await ev(`document.querySelector(".wt").click()`); await sleep(1500);
  check("artist view: a tile opens its record", (await ev(`!!document.querySelector(".wall-open .d-fig")`)) === true);
  await open("#q=Veneetsia&view=list", 4000);
  check("search: rows", (await ev(`document.querySelectorAll(".row").length`)) > 20);
  await open("#group=auction", 5000);
  check("auctions: highest hammer price first", /€\s?\d{3},?\d{3}/.test(await ev(`(document.querySelector(".row .rl-au")||{}).textContent||""`)));
  await open("#lang=et&artist=eduard-wiiralt", 5000);
  check("estonian: the page speaks Estonian", /KUNSTNIKKU|kunstiseinal/.test(await ev(`document.body.textContent`)));
  await open("#decade=1920", 5000);
  check("decade: wall", (await ev(`document.querySelectorAll(".wt").length`)) >= 12);
  check("no JavaScript errors", errors.length === 0, errors.slice(0, 3).join(" | "));
  for (const [f, needle] of [["stats.html", "The auction record"], ["stats-et.html", "Kataloog arvudes"], ["a/konrad-magi.html", 'class="wt"'], ["a/index.html", "Artists A"], ["sitemap.xml", "<urlset"]]){
    const p = path.join(DIR, f); check(`file: ${f}`, fs.existsSync(p) && fs.readFileSync(p, "utf-8").includes(needle));
  }
  check("artist pages: more than a thousand", fs.readdirSync(path.join(DIR, "a")).length > 1000);
  ws.close(); chrome.kill(); server.kill();
  console.log(failures.length ? `\n${failures.length} check(s) failed` : "\nall checks passed");
  process.exit(failures.length ? 1 : 0);
})().catch(e => { console.error(e); chrome.kill(); server.kill(); process.exit(1); });
