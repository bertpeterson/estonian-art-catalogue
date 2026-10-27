# -*- coding: utf-8 -*-
"""Kunstikoda auctions -> auction_records.json and upcoming_records.json (house: Kunstikoda)

Kunstikoda (kunstikoda.ee) is a shop of Estonian prints and paintings that holds an online
sale from a private collection: the first, "Kunstikoda sügisoksjon 2026", 24 lots closing
on 28 October 2026 at 19:00. The catalogue is one page (kunstioksjon-2026/, the same lots
again under eesti-graafika-oksjon-2026/): per lot its number, artist, title, then a list of
year, technique, size, signature and "ekspertiisiakt olemas", and "Alghind 350 €". Each lot
links to its own page (WooCommerce Simple Auctions), which gives the closing time
("Oksjon lõpeb: 28.10.2026 19:00") and the bid history ("21.10.2026 11:48 450,00 € k***1").
robots.txt fences off only the shop's own paths.

A sale still ahead goes to upcoming_records.json. Once it has closed, a lot with bids is
sold at its highest bid, a lot with none unsold; a page that still says the sale is open,
or that speaks of a reserve not met, is kept with no outcome ("nores") until the next run
reads it again. A closed lot's page is cached, since it does not change.
"""
import re, html, json, os, time, datetime, urllib.request
from auction_keep import merged
from upcoming import emit

BASE = "https://kunstikoda.ee"
HOUSE = "Kunstikoda"
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
CACHE = os.path.join("gcache", "kunstikoda")
os.makedirs(CACHE, exist_ok=True)
KNOWN = ["/kunstioksjon-2026/"]               # the sale pages so far; the menu names any new one
U = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2))).strftime("%Y-%m-%d %H:%M")   # Tallinn, near enough

def fetch(u):
    for attempt in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=45).read().decode("utf-8", "replace")
        except Exception as e:
            if getattr(e, "code", None) == 404: return ""
            print("  retry", u, e, flush=True); time.sleep(5 * (attempt + 1))
    return None

def lot_page(u):
    f = os.path.join(CACHE, re.sub(r"[^a-z0-9]+", "-", u[len(BASE):].lower()).strip("-") + ".html")
    if os.path.exists(f): return open(f, encoding="utf-8").read(), True
    time.sleep(2)
    return fetch(u), False

def money(s):
    return int(re.sub(r"\D", "", s.split(",")[0])) if s and re.sub(r"\D", "", s.split(",")[0]) else None

home = fetch(BASE + "/")
if not home: raise SystemExit("  Kunstikoda: the home page could not be read; nothing changed")
cats = list(dict.fromkeys(KNOWN + re.findall(r'href="https://kunstikoda\.ee(/[a-z-]*oksjon-\d{4}/)"', home)))
recs, coming, failed, seen = [], [], [], set()
for path in cats:
    cat = fetch(BASE + path)
    if not cat: failed.append(path); continue
    sm = re.search(r"Kunstikoda\s+([a-zõäöü]*oksjon\s+\d{4})", U(cat))
    sale = f"{HOUSE} {sm.group(1)}" if sm else None                   # "Kunstikoda sügisoksjon 2026"
    n = 0
    for a in re.findall(r"<article\b(.*?)</article>", cat, re.S):
        um = re.search(r'href="(https://kunstikoda\.ee/product/[^"]+)"', a)
        nr = re.search(r">\s*Nr\s*(\d+)\s*<", a)
        if not um or not nr or um.group(1) in seen or not sale: continue
        url = um.group(1); seen.add(url)
        artist = U((re.search(r"<h3[^>]*>(.*?)</h3>", a, re.S) or [None, ""])[1])
        title = U((re.search(r"</h3>\s*<p[^>]*>(.*?)</p>", a, re.S) or [None, ""])[1]).strip("„“”\"' ")
        lis = [U(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", a, re.S)]
        # "1922–1924", "1950. aastad (dateerimata)", "1974 / tõmmis 2021"; then the technique, the size
        # ("leht 19 × 13,7 cm, kujutis 14 × 10,2 cm": the first), the signature, "ekspertiisiakt olemas"
        yl = next((x for x in lis if re.match(r"(1[89]|20)\d\d\b", x)), None)
        size = next((x for x in lis if re.search(r"\d\s*[×x]\s*\d.*cm", x)), "")
        tech = next((x for x in lis if x not in (yl, size) and not re.search(
            r"\d\s*[×x]\s*\d|signe|ekspertiis|tiraaž|autograaf|tagapapil|tagaküljel|all paremal|all vasakul|ülal|mapist|sildistatud", x)), "")
        dm = re.search(r"(\d+(?:[.,]\d+)?\s*[×x]\s*\d+(?:[.,]\d+)?(?:\s*[×x]\s*\d+(?:[.,]\d+)?)?)", size)
        dims = re.sub(r"\s*[×x]\s*", " x ", dm.group(1)).replace(",", ".") + " cm" if dm else ""
        y4 = re.match(r"(\d{4})", yl or "")
        start = money((re.search(r"Alghind\s*([\d\s ]+)\s*€", html.unescape(a)) or [None, ""])[1] + ",")
        pid = re.search(r"/product/([^/]+)/", url).group(1)
        page, cached = lot_page(url)
        if page is None: failed.append(pid); continue
        txt = U(re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S))
        em = re.search(r"Oksjon lõpeb:\s*(\d\d)\.(\d\d)\.(\d{4})\s+(\d\d:\d\d)", txt)
        end = f"{em.group(3)}-{em.group(2)}-{em.group(1)} {em.group(4)}" if em else None
        if not end: failed.append(pid); continue
        r = {"aid": f"kk-{pid}", "artist": re.sub(r"\s*\([^)]*\)", "", artist).strip(), "title": title or "Pealkirjata",
             "year": y4.group(1) if y4 else None, "yl": yl, "tech": tech[:80], "dims": dims,
             "house": HOUSE, "sale": sale, "when": end[:7], "date": end[:10], "start": start, "url": url, "lot": int(nr.group(1))}
        if end > now: coming.append(r); n += 1; continue
        hist = txt.split("Pakkumiste ajalugu")[-1].split("Arvustused")[0]
        bids = [money(b) for b in re.findall(r"\d\d\.\d\d\.\d{4} \d\d:\d\d\s+([\d\s ]+,\d\d)\s*€", hist)]
        bids = [b for b in bids if b]
        if "Oksjon on avatud" in txt or re.search(r"reserv|ebaõnnestu", txt, re.I):
            recs.append({**r, "hammer": None, "sold": None, "nores": True})
            print(f"  lot {r['lot']} {pid}: no clear result yet, kept as offered", flush=True)
        else:
            recs.append({**r, "hammer": max(bids) if bids else None, "sold": bool(bids)})
            if not cached: open(os.path.join(CACHE, re.sub(r"[^a-z0-9]+", "-", url[len(BASE):].lower()).strip("-") + ".html"), "w", encoding="utf-8").write(page)
        n += 1
    print(f"  {path:28} {sale or '?':34} lots {n}", flush=True)

emit(HOUSE, [{k: r[k] for k in ("house", "sale", "date", "artist", "title", "year", "yl", "tech", "dims", "start", "url", "lot")} for r in coming])
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump(sorted(merged(prev, HOUSE, recs), key=lambda r: (r["house"], str(r.get("date") or r.get("when") or ""), str(r["aid"]))),
          open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"\nKUNSTIKODA: {len(recs)} past lots ({sum(1 for r in recs if r.get('sold'))} sold, {sum(1 for r in recs if r.get('nores'))} no result yet), "
      f"{len(coming)} coming; {len({r['artist'] for r in recs + coming})} artists; with year {sum(1 for r in recs + coming if r['year'])}, "
      f"medium {sum(1 for r in recs + coming if r['tech'])}, size {sum(1 for r in recs + coming if r['dims'])}; not read: {failed}")
