# -*- coding: utf-8 -*-
"""Sale alerts: an email when an artist on someone's My List comes up for sale, at a gallery or at auction.

    python3 build_alerts.py                      site/data/alerts.json: what is for sale now, {artist slug: [ids]}
    python3 build_alerts.py new LIVE.json OUT    what this build has that the live site's alerts.json had not, in full
    python3 build_alerts.py send OUT             that, to the Worker's /alerts/send (ALERT_KEY), which mails the accounts

The deploy (.github/workflows/pages.yml) fetches the live alerts.json before it builds, so "new" is new since the
last deploy, whichever run made it; with no live file yet (the first deploy) nothing is new. The Worker keeps what it
already announced, so a deploy run twice mails nothing twice. An id is the first twelve hex of the SHA-1 of the work's
or lot's address; where several share one address (Ruki's category pages, a sale's one page for all its lots), of the
address and the work's key or the lot's number, so a work added to such a page later is new. A work the daily stock
check found gone (data/stock_gone.json) is not for sale, whatever data.json says outside a build. Slugs are the bare name slugs the register keeps on My List (museaal.artists), not the page slugs.
"""
import json, os, sys, hashlib, datetime, collections, urllib.request

def sid(url): return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
def euros(v):
    try: return int(float(str(v or 0).replace(" ", "").replace(",", ".")))
    except ValueError: return 0

def for_sale():
    """{slug: {n: name, w: [[id, title, price, "s"|"l", gallery or house, date, link, picture]]}}: gallery stock with an
    address, and auction lots of sales not yet past. The picture is the seller's own, by address, never a copy."""
    import build_hubs as H     # here, not above: the send job has only the repository, not a build
    today, out = datetime.date.today().isoformat(), {}
    gone = json.load(open("data/stock_gone.json", encoding="utf-8")) if os.path.exists("data/stock_gone.json") else {}
    stock = [w for w in H.W if w.get("kind") == "gallery" and (w.get("url") or "").startswith("http") and w.get("k") not in gone]
    lots = [x for x in H.d.get("upcoming", []) if (x.get("u") or "").startswith("http") and not (x.get("d") and x["d"] < today)]
    shared = collections.Counter([w["url"] for w in stock] + [x["u"] for x in lots])
    def ident(u, own): return sid(u if shared[u] < 2 else u + "#" + str(own))
    def pic(im): return H.imsrc(im) if (im or "").startswith("g:") else ""
    def add(a, row):
        k = H.bare_slug(H.A[int(a)]["n"])
        if k: out.setdefault(k, {"n": H.A[int(a)]["n"], "w": []})["w"].append(row)
    for w in stock:
        u = w["url"]
        tech = H.val(w, "tce") or H.val(w, "tc") or ""
        if "müüdud" in tech.lower() or "sold" in tech.lower(): continue
        add(w["a"], [ident(u, w.get("k")), w.get("t") or "", euros(w.get("pr")), "s", H.val(w, "mu") or "", "", u, pic(w.get("im"))])
    for x in lots:
        u = x["u"]
        add(x["a"], [ident(u, x.get("n") or x.get("t") or ""), x.get("t") or "", euros(x.get("p")), "l", x.get("h") or "", x.get("d") or "", u, pic(x.get("im"))])
    return out

def main():
    if sys.argv[1:2] == ["new"]:
        live, dest = sys.argv[2], sys.argv[3]
        try: old = json.load(open(live, encoding="utf-8"))
        except (OSError, ValueError): print("  alerts: no live alerts.json, nothing is new"); return
        was = {i for ids in old.values() for i in ids}
        new = {}
        for k, a in for_sale().items():
            w = [r for r in a["w"] if r[0] not in was and sid(r[6]) not in was]    # sid(address): the id a shared page's works had before
            if w: new[k] = {"n": a["n"], "w": w}
        if new: json.dump(new, open(dest, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  alerts: {sum(len(a['w']) for a in new.values())} new works by {len(new)} artists")
        return
    if sys.argv[1:2] == ["send"]:
        key = os.environ.get("ALERT_KEY", "")
        if not key: print("  alerts: no ALERT_KEY, nothing sent"); return
        api = json.load(open("data/mood_api.json", encoding="utf-8"))["url"].rstrip("/") + "/alerts/send"
        body = json.dumps({"key": key, "items": json.load(open(sys.argv[2], encoding="utf-8"))}).encode("utf-8")
        req = urllib.request.Request(api, body, {"Content-Type": "application/json", "Origin": "https://museaal.ee", "User-Agent": "museaal-alerts"})
        r = json.load(urllib.request.urlopen(req, timeout=120))
        print(f"  alerts: {r.get('new')} new, {r.get('subscribers')} subscribers, {r.get('sent')} emails sent, {r.get('unsent')} over the day's cap")
        if r.get("unsent"): print("::warning::sale alerts over the day's mail cap: " + str(r["unsent"]) + " not sent")
        return
    ids = {k: [r[0] for r in a["w"]] for k, a in for_sale().items()}
    os.makedirs("site/data", exist_ok=True)
    json.dump(ids, open("site/data/alerts.json", "w", encoding="utf-8"), separators=(",", ":"))
    print(f"  sale alerts    data/alerts.json: {sum(map(len, ids.values()))} works for sale by {len(ids)} artists")

if __name__ == "__main__":
    main()
