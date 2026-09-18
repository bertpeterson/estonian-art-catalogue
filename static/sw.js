// museaal.ee service worker.
//
// The catalogue's data files are named by their content (data/index.json?v=<hash>,
// the detail shards, bios.json, i18n.json), so a cached copy can never be stale: a
// changed file is a different address. Those are answered from Cache Storage and
// fetched once; when a new version of a file is stored, the old versions of it are
// dropped. Every other request goes to the network. Pages are kept as they pass
// through, so the last copy opens when there is no connection.
//
// A page the worker does not yet control (the first visit) fetched its data before
// the worker existed; it posts the list, and the worker copies those in -- from the
// HTTP cache, which still holds them.
const CACHE = "museaal-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

const versioned = u => u.origin === self.location.origin && u.pathname.startsWith("/data/") && /^v=[0-9a-f]+$/.test(u.search.slice(1));

async function prune(cache, u){
  for (const k of await cache.keys()){
    const ku = new URL(k.url);
    if (ku.pathname === u.pathname && ku.search !== u.search) await cache.delete(k);
  }
}
async function store(cache, url){
  const hit = await cache.match(url);
  if (hit) return hit;
  const r = await fetch(url);
  if (r.ok){ await cache.put(url, r.clone()); prune(cache, new URL(url)); }
  return r;
}

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const u = new URL(e.request.url);
  if (versioned(u) && e.request.cache !== "reload"){
    e.respondWith(caches.open(CACHE).then(c => store(c, e.request.url)));
  } else if (e.request.mode === "navigate"){
    // The page itself is asked for afresh every time -- GitHub Pages lets a browser
    // keep it for ten minutes, which after a deploy showed the old page, naming the
    // old data, until a hard reload. Revalidating costs one round trip (304 when
    // nothing changed); the data files are versioned and stay cached.
    e.respondWith(fetch(u.pathname + u.search, {cache: "no-cache", credentials: "same-origin"}).then(r => {
      if (r.ok) caches.open(CACHE).then(c => c.put(u.pathname, r.clone()));
      return r;
    }).catch(() => caches.match(u.pathname).then(h => h || Response.error())));
  }
});

self.addEventListener("message", e => {
  const urls = e.data && e.data.warm;
  if (!Array.isArray(urls)) return;
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(urls.filter(x => { try { return versioned(new URL(x)); } catch(err){ return false; } }).map(x => store(c, x).catch(() => {})))));
});
