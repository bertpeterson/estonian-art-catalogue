# -*- coding: utf-8 -*-
"""Artisoon (artisoon.ee) -> appends to gallery_records.json. Metadata only.

A Tallinn dealer in art from private hands ("kunsti ost ja müük, kiirmüük"), ~400 works
in November 2026: Soviet-era and earlier paintings and prints (Hugo Lepik, Marju
Bormeister, Ahti Sepsivart, Aino Bach), ceramics, photographs. The shop is Voog; its
robots.txt closes only /files/ and /admin/. Four listings (Maalid at /tooted, Graafika,
Keraamika, Fotograafia) give the works' addresses; "Viimati lisatud" repeats them under
other addresses (".../x-1"), so a work is one Voog product id and keeps its category page.
Each work's page carries the product as JSON on its cart button (id, stock, price, picture)
and the text a visitor reads: 'Artist "Title"' as the heading, then a line such as
"Ofort 1937. Originaalraamis ... Ava mõõdud 27 x 34 cm." A heading or stock that says
MÜÜDUD, or no stock left, is the dealer's word that it sold: kept, flagged; BRONEERITUD
(reserved) stays listed without a price. The asking price of a work for sale is read
(asking_price.py); a sold work's never. Pictures are the site's own /photos/ copies.
Pages are cached for a day.
"""
import json, re, os, gzip, ssl, time, html, urllib.request
from asking_price import euros
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
BASE = "https://www.artisoon.ee"
CATS = ["tooted", "graafika", "keraamika", "fotograafia", "viimati-lisatud"]
ctx = ssl.create_default_context()
os.makedirs("gcache", exist_ok=True)
U = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def get(u, key):
    p = f"gcache/{key}.html.gz"
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > 86400: os.remove(p)
    if os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f: return f.read()
    h = ""
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60, context=ctx) as f:
                h = f.read().decode("utf-8", "replace"); break
        except Exception as e:
            if k == 2: print("ERR", u, repr(e)[:60], flush=True)
            time.sleep(3 * (k + 1))
    if h:
        with gzip.open(p, "wt", encoding="utf-8") as f: f.write(h)
    time.sleep(1.2)
    return h

# the catalogue's artist names, longest first: a heading without quotes ("Hugo Lepik akvarell",
# "Ernö Koch EKA maja ehitus") is split where a known name ends
known = sorted({a["n"] for a in (json.load(open("data.json", encoding="utf-8"))["artists"] if os.path.exists("data.json") else []) if len(a["n"].split()) > 1}, key=len, reverse=True)

def split(head):
    head = re.sub(r"\s*\b(MÜÜDUD|BRONEERITUD)\b\s*", " ", head).strip(" ,")
    m = re.match(r'^(.+?)\s*[„"“”«]\s*(.+?)\s*(?:["“”»](.*))?$', head)
    if m:      # a technique between name and title ("Naima Neidre ofort", "Voldemar Eller õlimaal") is not the name
        return re.sub(r"(\s+[a-zõäöüšž][\wõäöüšž-]*)+$", "", m.group(1).strip(" ,")), (m.group(2) + " " + (m.group(3) or "")).strip(" ,")
    low = head.lower()
    for n in known:
        if low == n.lower() or low.startswith(n.lower() + " ") or low.startswith(n.lower() + ","): return head[:len(n)], head[len(n):].strip(" ,")
    # otherwise the capitalised words up front (with del/von/van/de between them)
    w = head.split()
    k = 0
    while k < len(w) and (w[k][:1].isupper() or (w[k] in ("del", "von", "van", "de", "der") and k + 1 < len(w))) and k < 4: k += 1
    if len(w) > k >= 2: return " ".join(w[:k]).strip(","), " ".join(w[k:]).strip(" ,")
    return head, ""

links, seen = [], set()
for c in CATS:
    h = get(f"{BASE}/{c}", f"artisoon_{c}")
    for s in re.findall(rf'href="/{c}/([a-z0-9-]+)"', h):
        if c == "viimati-lisatud" and (s in seen or re.sub(r"-\d+$", "", s) in seen): continue
        if s not in seen: seen.add(s); links.append((c, s))
print("works listed:", len(links), flush=True)

recs, ids = [], set()
for c, s in links:
    h = get(f"{BASE}/{c}/{s}", f"artisoon_{c}_{s}")
    m = re.search(r'data-product="([^"]+)"', h)
    hd = re.search(r'content-item-title[^>]*>\s*<h1>(.*?)</h1>', h, re.S)
    if not m or not hd: continue
    p = json.loads(html.unescape(m.group(1)))
    if p["id"] in ids or p.get("status") != "live": continue
    ids.add(p["id"])
    head = U(hd.group(1))
    artist, title = split(head)
    # two makers, no maker ("Tundmatu kunstnik"), a doubted one ("Mall Valk?") or a workshop mark ('"Öökull"'): no single artist
    if not artist or "/" in artist or re.search(r"\bja\b|&|\?|^[„\"“]|tundmatu", artist, re.I): continue
    body = re.search(r'class="formatted area-normal"[^>]*>(.*?)<div class="edy-buy-button', h, re.S)
    text = U(body.group(1)) if body else ""
    sold = bool(re.search(r"müüdud", head + " " + text, re.I)) or (p.get("stock") is not None and p["stock"] <= 0)
    held = bool(re.search(r"broneeritud", head + " " + text, re.I)) or (p.get("reserved_quantity") or 0) > 0
    ym = re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", text)
    dm = re.search(r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?)\s*cm", text)
    tech = re.sub(r"\b(1[89]|20)\d\d\b\.?", "", re.split(r"\.\s+(?=[A-ZÕÄÖÜ])", text)[0]) if text else ""
    q = re.search(r'[„"“]([^"“”]{2,60})["“”]', tech)
    if q and not title: title, tech = q.group(1), tech.replace(q.group(0), "")    # an untitled heading, the title in the text: '"Kassnaine" õli/akrüül papil'
    tech = re.sub(r"(?:(?:ava|pildi|raami)?\s*mõõdu?d?:?\s*)?\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?\s*(?:cm)?", "", tech, flags=re.I)
    tech = re.sub(r"\s*,\s*,+|\s+", " ", tech).strip(" ,.;")
    img = re.search(r'property="og:image" content="(https://www\.artisoon\.ee/photos/[^"]+)"', h)
    price = {} if sold or held or p.get("currency") != "EUR" else euros(f'{round(float(p.get("effective_price") or p.get("price") or 0))} €')
    recs.append({**price, "gid": f"ats-{p['id']}", "artist": artist, "title": title.strip('“”"„') or "Nimetu",
                 "year": ym.group(1) if ym else None, "tech": tech[:80],
                 "dims": re.sub(r"\s*[x×]\s*", " x ", dm.group(1)) + " cm" if dm else "",
                 "gallery": "Artisoon", "city": "Tallinn", "url": f"{BASE}/{c}/{s}",
                 **({"sold": True} if sold else {}),
                 **({"img": re.sub(r"_huge\.", "_block.", img.group(1))} if img else {})})

prev = json.load(open("gallery_records.json", encoding="utf-8"))
keep = [r for r in prev if not r["gid"].startswith("ats-")]
json.dump(keep + recs, open("gallery_records.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"ARTISOON WORKS: {len(recs)}  artists: {len({r['artist'] for r in recs})}  sold: {sum(1 for r in recs if r.get('sold'))}  priced: {sum(1 for r in recs if r.get('price'))}")
print(f"  with year {sum(1 for r in recs if r['year'])}, with dims {sum(1 for r in recs if r['dims'])}, with picture {sum(1 for r in recs if r.get('img'))}")
for r in recs[:4]: print(f"   {r['artist'][:20]:20} {r['title'][:26]:26} {r['year'] or '—':6} {r['dims']:14} {r['tech'][:22]}")
