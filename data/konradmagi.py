# -*- coding: utf-8 -*-
"""The Konrad Mägi Foundation's catalogue of works -> konradmagi_records.json

konradmagi.ee lists every Mägi painting, sketch and lost work the foundation knows of,
with title, date, medium, size and holder: a museum, a named private collection,
"Erakogu", or nothing for a work whose whereabouts are unknown. The listing pages carry
it all as schema.org markup; no work page is opened. Holders are kept as the site gives
them only where they are institutions; a private holder of any kind becomes "Erakogu"
(private collection), with no name, no city and no country -- whose house a painting is
in is nobody's business here. robots.txt allows everything; pages are fetched once, with
a pause between them.
"""
import re, json, html, time, urllib.request

BASE = "https://konradmagi.ee/et/work_category/"
CATS = {"maalid": "painting", "eskiisid": "sketch", "kadunud": "lost"}
UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
ITEM = re.compile(r'<li class="c-works-list-item[^"]*"[^>]*>(.*?)</li>', re.S)
def field(it, pat):
    m = re.search(pat, it, re.S); return html.unescape(m.group(1)).strip() if m else ""
def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=45) as r: return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt == 2: return ""
            time.sleep(3)
INSTITUTION = re.compile(r"muuseum|museum|arhiiv|selts|ülikool|raamatukogu|galerii|sihtasutus|kunstihoone", re.I)

recs, seen = [], set()
for slug, cat in CATS.items():
    page = 1
    while True:
        h = get(BASE + slug + "/" + (f"page/{page}/" if page > 1 else ""))
        items = ITEM.findall(h)
        if not items: break
        for it in items:
            url = field(it, r'href="([^"]+)"')
            if not url or url in seen: continue
            seen.add(url)
            holder = field(it, r"c-works-list-item-collection'>(.*?)<")
            if cat == "lost" and not holder: kind = "lost"; holder_out = ""
            elif INSTITUTION.search(holder) and not re.search(r"erakogu|private|kollektsioon|kogu\b", holder, re.I): kind = "held"; holder_out = holder
            elif holder: kind = "private"; holder_out = "Erakogu"
            else: kind = "unknown"; holder_out = ""
            recs.append({"url": url, "title": field(it, r'itemprop="name">(.*?)<'), "date": field(it, r"itemprop='dateCreated'>(.*?)<"),
                         "medium": field(it, r"itemprop='material'>(.*?)<"), "dims": field(it, r"</span><span>(.*?)</span></span>"),
                         "img": field(it, r'<img src="([^"]+)"'), "category": cat, "holder_kind": kind, "holder": holder_out,
                         "holder_as_listed_is_institution": kind == "held"})
        print(f"  {slug} page {page}: {len(items)} works", flush=True)
        page += 1; time.sleep(2)
json.dump(recs, open("konradmagi_records.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
import collections
print("\nKONRAD MÄGI SA:", len(recs), "works;", dict(collections.Counter(r["holder_kind"] for r in recs)))
