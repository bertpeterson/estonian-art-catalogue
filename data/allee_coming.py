# -*- coding: utf-8 -*-
"""Allee galerii's coming sale -> upcoming_records.json (house: Allee galerii)

Allee's auction pages are no longer harvested (its server refuses GitHub's runners, and
its results stand as recorded until October 2026). Its coming sale is entered by hand
in sales_by_hand.json; this reads that sale's listing, alleegalerii.ee/kunstioksjon/,
once, and the page of each lot not read before, once, at the ten-second delay the
house's robots file asks for: artist, title, year, size from the listing, the starting
price ("Alghind 84 000 €") and the medium from the lot's page. Run from this Mac only,
by hand or by the weekly local task before a sale; never in CI. A listing that cannot
be read leaves last week's lots as they are.
"""
import re, html, json, os, sys, time, datetime, unicodedata, urllib.request
from upcoming import emit

UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
CACHE = os.path.join("gcache", "allee_coming")
os.makedirs(CACHE, exist_ok=True)
LOT = re.compile(r"^(?P<a>[^“\"„]+?)\s*[“\"„](?P<t>.+?)[”\"“]\s*,?\s*(?P<rest>.*)$", re.S)
DIMS = re.compile(r"(?:\b(?:plm|km|lm|vm|ava)\s*)?(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*(?:cm)?|d\s*=\s*(\d+(?:[.,]\d+)?)\s*cm", re.I)

def fetch(u):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=45).read().decode("utf-8", "replace")
    except Exception as e: print("  failed", u, e); return ""
def page(u):
    f = os.path.join(CACHE, u.rstrip("/").rsplit("/", 1)[1] + ".html")
    if os.path.exists(f): return open(f, encoding="utf-8").read()
    time.sleep(10)
    t = fetch(u)
    if t: open(f, "w", encoding="utf-8").write(t)
    return t
def lot_medium(lp, heading):
    # the line after the sale's heading on the lot's page, up to the year: "Õli lõuendil"
    tx = html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"<script.*?</script>|<style.*?</style>", "", lp or "", flags=re.S)))
    lines = [l.strip() for l in tx.split("\n") if l.strip()]
    medium = ""
    for k, l in enumerate(lines):
        if l.lower() == heading.lower() and k + 1 < len(lines) and lines[k + 1] != "Mõõdud":
            medium = lines[k + 1]; break
    medium = re.sub(r"[,.;]?\s*(?:\d{4}|\d{2,4}\s*[-–/]\s*\d{2,4}|\d{4}ndad).*$", "", medium).strip(" ,.;")
    if not medium or re.match(r"^\d", medium) or len(medium) > 60 or re.search(r"alghind|haamrihind|€|eur", medium, re.I): medium = ""
    return medium

today = datetime.date.today().isoformat()
sales = [x for x in json.load(open("sales_by_hand.json", encoding="utf-8"))
         if x["house"] == "Allee galerii" and (x.get("end") or x["date"]) >= today]
if not sales: print("  ALLEE: no coming sale in sales_by_hand.json"); sys.exit(0)
S = min(sales, key=lambda x: x["date"])
heading = re.sub(r"^Allee\s+", "", S["sale"]); heading = heading[0].upper() + heading[1:]        # "Sügisoksjon 2026"
cat = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", heading.lower()).encode("ascii", "ignore").decode()).strip("-")
h = fetch("https://alleegalerii.ee/kunstioksjon/")
if f"project-cat-{cat}" not in h: print(f"  ALLEE: listing not read or no {cat} lots; last run's lots kept"); sys.exit(0)

prev = {r["url"]: r for r in json.load(open("upcoming_records.json", encoding="utf-8")) if r["house"] == "Allee galerii" and r.get("start")}
seen, lots, bad, new = set(), [], [], 0
for art in re.findall(rf'<article[^>]*project-cat-{cat}[^>]*>(.*?)</article>', h, re.S):
    m = re.search(r'<h3[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', art, re.S)
    if not m or m.group(1) in seen: continue
    url = m.group(1); seen.add(url)
    line = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
    line = re.sub(r"^Teeme koos head!\s*", "", line)                                    # a charity lot's prefix
    if line.count("“") > line.count("”"): line = re.sub(r"(“[^”]*?)(,\s*\d)", r"\1”\2", line, 1)   # a title left unclosed
    lm = LOT.match(line)
    artist = re.sub(r"\s*\(end\.[^)]*\)", "", lm.group("a")).strip() if lm else ""        # "Sirje Petersen (end. Protsin)"
    if not lm or not re.match(r"^[^\d]{3,60}$", artist): bad.append(line); continue
    title, rest = lm.group("t").strip(), lm.group("rest")
    yl = re.split(r"\.\s|\s(?=(?:plm|km|lm|vm|ava|d\s*=)\b)", rest, 1, flags=re.I)[0].strip(" ,.")
    if not re.search(r"\d{4}|ndad|sajand", yl, re.I): yl = ""
    dm = DIMS.search(rest)
    dims = (re.sub(r"\s*[x×]\s*", " x ", dm.group(1)).replace(",", ".") + " cm") if dm and dm.group(1) else ""
    y4 = re.match(r"(\d{4})", yl)
    im = re.search(r'<img[^>]*\ssrc="(https://alleegalerii\.ee/wp-content/[^"]+)"[^>]*?(?:srcset="([^"]*)")?', art)
    img = None
    if im:
        img = next((u for u, w in re.findall(r"(\S+)\s+(\d+)w", im.group(2) or "") if w == "600"), im.group(1))
    if url in prev: start, tech = prev[url]["start"], prev[url].get("tech")
    else:
        new += 1
        lp = page(url); pt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", lp)))
        sm = re.search(r"Alghind\s*:?\s*([\d\s]+)€", pt)
        start = int(re.sub(r"\D", "", sm.group(1))) if sm else None
        tech = lot_medium(lp, heading) or None
    lots.append({"house": "Allee galerii", "sale": S["sale"], "date": S["date"], "artist": artist, "title": title,
                 "year": y4.group(1) if y4 else None, "yl": yl or None, "tech": tech, "dims": dims, "start": start, "url": url, "img": html.unescape(img) if img else None})
print(f"  ALLEE {S['sale']}: {len(lots)} lots ({new} new, {len(set(prev) - seen)} gone), {sum(1 for x in lots if x['start'])} with a starting price; unparsed: {bad}")
emit("Allee galerii", lots)
