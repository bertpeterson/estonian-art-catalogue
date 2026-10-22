# -*- coding: utf-8 -*-
"""Osta Noort Kunsti auctions -> auction_records.json and upcoming_records.json (house: Osta Noort Kunsti)

"Buy Young Art": Art & Tonic's sale of young artists' work, twice a year since November
2021 (the 11th on 23 October 2026), in the gallery and online at once, 60 to 90 lots a
sale, many from 1 €. Each sale has a catalogue, ostanoortkunsti.ee/kataloog/oksjonid/<sale>/,
paged by about 25: per lot its number, artist, title, starting price ("Alghind: 30 €"),
size, technique and year ("2025a"). robots.txt fences off only the shop's own paths.

The house publishes no results: a lot's page says only "Oksjon lõppenud" once the sale
is over. A past lot is kept as offered, with its starting price and no outcome
("nores"), never as unsold; merge.py shows it as "result not published". A sale still
ahead goes to upcoming_records.json. A past sale's catalogue does not change, so its
pages are cached; the coming sale's are read each run.
"""
import re, html, json, os, time, datetime, urllib.request
from auction_keep import merged
from upcoming import emit

BASE = "https://ostanoortkunsti.ee"
HOUSE = "Osta Noort Kunsti"
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
CACHE = os.path.join("gcache", "onk")
os.makedirs(CACHE, exist_ok=True)
MONTHS = {"jaan": 1, "veebr": 2, "märts": 3, "märtsil": 3, "apr": 4, "mai": 5, "juun": 6, "juul": 7,
          "aug": 8, "sept": 9, "okt": 10, "nov": 11, "dets": 12}
U = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
today = datetime.date.today().isoformat()

def fetch(u):
    for attempt in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=45).read().decode("utf-8", "replace")
        except Exception as e:
            if getattr(e, "code", None) == 404: return ""
            print("  retry", u, e, flush=True); time.sleep(5 * (attempt + 1))
    return None

def page(u, keep):
    f = os.path.join(CACHE, re.sub(r"[^a-z0-9]+", "-", u[len(BASE):].lower()).strip("-") + ".html")
    if keep and os.path.exists(f): return open(f, encoding="utf-8").read()
    time.sleep(2)
    t = fetch(u)
    if t and keep: open(f, "w", encoding="utf-8").write(t)
    return t

def sale_date(name):
    # "10. oksjon 15. mai 2026", "1. oksjon 4. novembril 2021"
    m = re.search(r"(\d{1,2})\.\s*([a-zõäöü]+)\s+(\d{4})", name.split("oksjon", 1)[1])
    mo = next((v for k, v in MONTHS.items() if m and m.group(2).startswith(k)), None)
    return f"{m.group(3)}-{mo:02d}-{int(m.group(1)):02d}" if m and mo else None

home = fetch(BASE + "/kataloogid/")
if not home: raise SystemExit("  ONK: the list of catalogues could not be read; nothing changed")
cats = sorted(set(re.findall(r'href="(https://ostanoortkunsti\.ee/kataloog/oksjonid/([^"/]+)/)"', home)), key=lambda c: int(c[1].split("-")[0]))
recs, coming, failed = [], [], []
for url, slug in cats:
    first = page(url, False)              # the first page names the sale and its date; read each run, it is one fetch
    if not first: failed.append(slug); continue
    name = U(re.search(r"<title>(.*?)</title>", first, re.S).group(1)).split(" – ")[0].split(" &#8211; ")[0]
    date = sale_date(name)
    if not date: failed.append(slug); continue
    ahead = date >= today
    sale = f"{HOUSE} {name.split(' oksjon')[0]}. oksjon".replace("..", ".")      # "Osta Noort Kunsti 10. oksjon"
    pages = sorted({int(n) for n in re.findall(rf'/oksjonid/{re.escape(slug)}/page/(\d+)/', first)})
    htmls = [first] + [page(f"{url}page/{n}/", not ahead) for n in pages]
    if any(h is None for h in htmls): failed.append(slug); continue
    n = 0
    for h in htmls:
        for art in re.findall(r'<article id="auction_(\d+)"(.*?)</article>', h, re.S):
            pid, a = art
            if f"product_cat-{slug}" not in a: continue
            artist = U((re.search(r'class="_author[^"]*"[^>]*>(.*?)</h2>', a, re.S) or [None, ""])[1])
            tm = re.search(r'class="_title[^"]*"[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', a, re.S)
            # "Getter-Kadi Valter (Kaldma)", "Triina Britt Aumere / ARTbyTBA", "Olesja Katšanovskaja – Münd": the
            # name without the bracket or the one-word studio name, a double surname hyphenated; two artists'
            # names ("Eliise Raadik x Sigrid Kuusk") are left to merge.py, which takes no joint lot
            artist = re.sub(r"\s*\([^)]*\)", "", artist).strip()
            artist = re.sub(r"\s+/\s+\S+$", "", artist)
            artist = re.sub(r"(\w)\s+[–-]\s+(\w)", r"\1-\2", artist)
            artist = re.sub(r"\s+x\s+", " & ", artist)
            if not artist or not tm: continue
            title = U(tm.group(2)).strip("“”\"„ ")
            lot = re.search(r'class="_lotnr[^"]*">\s*(\d+)\.', a)
            sm = re.search(r"Alghind:\s*</b>\s*([\d\s ]+)", html.unescape(a))
            start = int(re.sub(r"\D", "", sm.group(1))) if sm and re.sub(r"\D", "", sm.group(1)) else None
            meta = a.split('class="_meta"', 1)[1] if 'class="_meta"' in a else ""
            dims = U((re.search(r'uk-tooltip="Teose mõõdud".*?<span>(.*?)</span>', meta, re.S) or [None, ""])[1])
            tech = U((re.search(r'uk-tooltip="Teose (?:maali)?tehnika".*?<span>(.*?)</span>', meta, re.S) or [None, ""])[1])
            ym = re.search(r"<li>\s*((?:19|20)\d\d)\s*a?\.?\s*</li>", meta)
            dm = re.search(r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)", dims)
            dims = re.sub(r"\s*[x×]\s*", " x ", dm.group(1)).replace(",", ".") + " cm" if dm else ""
            r = {"aid": f"onk-{pid}", "artist": artist, "title": title or "Pealkirjata",
                 "year": ym.group(1) if ym else None, "yl": ym.group(1) if ym else None, "tech": tech[:80], "dims": dims,
                 "house": HOUSE, "sale": sale, "when": date[:7], "date": date, "start": start, "url": tm.group(1),
                 "lot": int(lot.group(1)) if lot else None}
            if ahead: coming.append(r)
            else: recs.append({**r, "hammer": None, "sold": None, "nores": True})
            n += 1
    print(f"  {date} {sale:32} lots {n}{' (ahead)' if ahead else ''}", flush=True)

emit(HOUSE, [{k: r[k] for k in ("house", "sale", "date", "artist", "title", "year", "yl", "tech", "dims", "start", "url", "lot")} for r in coming])
prev = json.load(open("auction_records.json", encoding="utf-8")) if os.path.exists("auction_records.json") else []
json.dump(sorted(merged(prev, HOUSE, recs), key=lambda r: (r["house"], str(r.get("date") or r.get("when") or ""), str(r["aid"]))),
          open("auction_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"\nOSTA NOORT KUNSTI: {len(recs)} past lots in {len({r['sale'] for r in recs})} sales (results not published), "
      f"{len(coming)} coming; {len({r['artist'] for r in recs + coming})} artists; with year {sum(1 for r in recs if r['year'])}, "
      f"medium {sum(1 for r in recs if r['tech'])}, size {sum(1 for r in recs if r['dims'])}; sales not read: {failed}")
