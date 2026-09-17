# Estonian Art Catalogue · Eesti Kunstikataloog

A browsable catalogue of **100,313 artworks** by **5,349 artists** — museum holdings from **24 Estonian public
collections**, plus what seven commercial galleries and the NOBA marketplace are selling right now,
aggregated from the national museum databases and the galleries' own listings and presented as a static site.

Every record is a real object with a real holder and links back to its source record. Nothing here is
invented, reconstructed, or filled in by hand; where a judgement was made instead of a count, the page
says so with an *ed* tag.

**Live site (canonical):** https://museaal.ee/

---

## Sources

| Source | Records | What it is |
|---|---|---|
| [MuIS](https://www.muis.ee) | 67,217 | Muuseumide Infosüsteem — the shared catalogue of all Estonian museums; the art collections of the Art Museum of Estonia, Tartu Art Museum, the History, National, Maritime and Tartu City museums and the regional museums, the later ones read through its OAI-PMH service |
| [EKM Digital Collection](https://digikogu.ekm.ee) | 32,625 | The Art Museum of Estonia's own database, behind Kumu |
| [CCA Estonia](https://cca.ee) | 58 bios | Centre for Contemporary Art — artist biographies, Venice Biennale archive |
| [EKKM](https://ekkm.ee) | — | Contemporary Art Museum of Estonia |
| Vaal galerii | 115 artists | Life dates printed beside every lot's artist in its sales, taken for artists no museum, Wikidata or biography dates, tagged *Vaal* |
| [Wikidata](https://www.wikidata.org) | 1,629 artists | Dates, birthplace, description, training and art-historical affiliation — matched on name, gated on dates and occupation (see *Rules*) |
| Nine commercial galleries and NOBA | 7,259 | Haus, Vernissage, Allee, E-Kunstisalong, Temnikova & Kasela, Tütar, Artrovert, Kogo, Ruki — current stock from each gallery's own site; and [NOBA](https://noba.ac), the Nordic-Baltic marketplace, for artists the catalogue already holds or whose NOBA page places them in Estonia. Metadata only, never prices |
| Auction results: Haus Galerii, E-Kunstisalong, Allee galerii, Vernissage, Vaal galerii, Eesti Kunsti Oksjonid | 13,122 lots | Every lot in Haus Galerii's hundred sales since 1998, E-Kunstisalong's thirty-five since 2008, Allee galerii's fifteen since 2020, Vernissage's fifteen since 2021, Vaal galerii's nine since 2022 and Eesti Kunsti Oksjonid's eighteen since 2023, as the house published it, plus five earlier record prices as the press reported them (`data/press_results.json`): starting price, hammer price, sold or unsold. A record of what happened at auction, not a valuation |
| Konrad Mägi Foundation — catalogue of works | 99 works | The foundation's list of every Mägi painting, sketch and lost work it knows of (konradmagi.ee); the works in Estonian museums are here already, the rest enter as *known*: in a private collection, unnamed, or of unknown whereabouts |

Of the works for sale, 3,203 are NOBA listings, 4,056 the galleries' own. NOBA also supplies a short
biography, written by the artist or NOBA, for 544 artists who have none from a museum, and a birth year
read from that biography for 301 — both tagged *NOBA* on the page.

20,919 objects appear in both MuIS and the EKM database and are merged on inventory number
(MuIS `Number` = digikogu `Tulmenumber` + `Kogunumber`), which is why 88,788 source objects
collapse to 100,313 works.

**Only attributed works are included.** Anonymous and unattributed objects are excluded by design — including 485 objects catalogued under the name *Tundmatu kunstnik* ("unknown artist"), which is the absence of an attribution written into the name field rather than a name. Notnames stay: *Püha Lucia legendi meister* and its kind identify a hand recognised across several works, and art history treats that as an attribution.

Metadata in MuIS is published under CC0. This repository redistributes **metadata only** — no
image file is copied or served; where the site shows a picture it is loaded from the holder's or
the gallery's own server (see *Images* below). Each record carries the identifiers needed to reach
the original entry at its holding institution.

## What's in the repository

```
site/                 the deployable static site (open index.html over HTTP)
  data/index.json     11 MB — everything the list, search and facets need
  data/detail/<decade>.json  shards — descriptions, dimensions, collapsed duplicates
  a/<artist>.html     a static page per artist, plus redirects for retired spellings
  404.html            for stale addresses
register.html         a dated snapshot as one self-contained file — see below
data/data.json        the merged dataset (see Schema below)
data/*.py             the harvest, enrichment and merge scripts
tpl_head.html         markup + CSS for the app
tpl_app.html          the application itself
i18n.py               the EN/ET dictionary — the source; i18n.json is generated from it on every build
build_site.py/.sh     rebuilds site/ from data/data.json
```

The ~640 MB of cached source pages (`data/cache/`, `data/dkcache/`) are **not** committed —
they are large and genuinely disposable.

The parsed harvest they produced **is**, gzipped, in `data/raw/` (7.7 MB). That is
deliberate. `records.json` is the output of 48,655 fetches against MuIS, whose robots.txt
disallows us; the decision not to re-crawl is what makes that file irreplaceable rather
than merely inconvenient to lose. From a fresh clone:

    python3 data/unpack.py     # expands data/raw/*.gz into data/
    ./build_site.sh            # merge, validate, export, build

Everything then rebuilds without fetching anything from anyone.

## Rules the data follows

These are the decisions between the sources and the page. Each is in `data/merge.py` with its reasons.

**Attribution.** Only attributed work. Objects catalogued as *Tundmatu kunstnik* or with a trailing `(?)`
are out; notnames (*Püha Lucia legendi meister*) stay. A workshop, copy or "after" is never merged with
its master.

**One person, one page.** Two spellings are one artist when they share the surname and birth year and
their first names are a letter apart or one a subsequence of the other (Johan/Johann Köler, Erich
Kügelgen / Erich von Kügelgen). A generation qualifier — *sen.*, *jun.*, *vanem*, *noorem* — must agree.
56 spellings merged; the retired address of each redirects to the survivor.

**Dates.** A range wider than thirty years (*ca 1800–1899*) is a period, not a year: the museum's words
stay as the label, the page shows the century. A year written at the end of a title is used only when
the dating field said nothing at all. A work dated before its artist was born or after they died keeps
the museum's date and carries a flag (`f: pre | post`; 30 and 169) that the page explains and the
artist's activity span ignores. Two source records with a death before a birth are corrected and tagged
*ed*.

**Wikidata.** Matched on the name label, then kept only if the birth year agrees with the museum's, or —
where the museum gives no dates — sits ten to ninety years before the artist's earliest work; and only
if the item's recorded occupations include an artistic one (an item with none recorded is kept). 165
matches were the wrong person by that last rule alone: a veterinarian, a wrestling coach, a footballer
born in 2003. Where the museum gave no dates and Wikidata does, the date is filled and tagged *Wikidata*.

**Galleries.** Only what is purchasable now: past auction lots and Kogo's sold works are excluded
from the stock, and any price phrase is stripped before parsing. One listing per work per gallery. NOBA
lists most works twice, once per site language, with the title translated; pairs are folded on artist,
year, size and medium where that leaves exactly one of each, keeping the Estonian. A work a gallery
lists on its own site and again on NOBA keeps the gallery's listing. NOBA links go to the artwork page
(`/kunst/`, `/artwork/`) where one exists — 5,717 of 8,885 — and otherwise to the product page, which
for the rest is the only page there is.

**Known works.** A catalogue raisonné records what no public source can: works in private hands and works
lost. The Konrad Mägi Foundation's catalogue enters as `kind: known` — title, date, medium, size and the
holder as the catalogue gives it, with one deliberate loss: a private holder of any kind, named or not on
the foundation's page, is *Erakogu* here, a private collection with no name, city or country. Whose house a
painting hangs in is not a fact this catalogue needs, and the foundation's page, linked from every record,
remains the place that says more. A work the foundation places in an Estonian museum is not added twice.

**Past listings.** A work a gallery has sold is still a work that exists and passed through a known
hand. Where the gallery says so — Allee's *Müüdud*, Vernissage's *MÜÜDUD*, Kogo's *Sold*, Artrovert's
out-of-stock badge — the record is kept, marked *sold*, and is never counted as for sale. Where a listing
simply disappears between two monthly harvests it is kept as *no longer listed*, since sold and withdrawn
cannot be told apart from outside. A NOBA product whose artwork page was already private when first seen
is left out altogether: nobody — not NOBA's own site, not this catalogue — ever saw it listed, and a
record no one vouches for is not a record; `ledger.py` keeps the month each
listing was first and last seen. The masthead figure is therefore the number of works the catalogue has
ever verified with a holder, and only grows; the *for sale* figure is current stock and moves both ways.
A sale price is never taken: what a gallery work sold for stays between the gallery and the buyer.

**Auction results** are a kind of their own, neither a holding nor stock. Haus Galerii publishes its
whole archive — a page per sale since 1997, a figure per lot with starting price, last bid and hammer
price, kroon-era prices shown by the house in euro at the fixed rate — except a dozen lots where the hammer
field still held the kroon figure (28 000 on a Wiiralt woodcut started at 1 790 €: 28 000 kroons is 1 790 €);
a round hammer price on a kroon-era lot that reads as the start or more at the fixed rate, or as eight times
the start, is converted and marked. One published figure is set aside by hand rather than by rule: Haus
prints €26,000 as the hammer price of Mägi's *Oberstdorfi maastik* in 1999, with no bid recorded — the sum the
same painting made at Haus in 2019 — so the 1999 lot stands as offered at €6,391 and unsold, with the reason
on the record (`data/auction_doubt.json`). Allee galerii keeps a page per sale
with the lot line, starting and hammer price, and the medium on the lot's own page. Eesti Kunsti Oksjonid keeps each
online sale's page up with the final bid on every lot — *Lõpppakkumine – (0)* for a lot nobody bid on — but prints no
date, so the sale is placed by the day its name gives and the month its lots were listed. Vaal galerii's site draws each
sale from a small JSON API — lots by day with the date, technique, starting and hammer price, year and size — and that is
read as the page reads it. E-Kunstisalong's sale pages carry each lot with its outcome — *Alg: € 1 500,
lõpp: € 1 700*; *müüdud* for a sale at the start price — back to 2008; the earlier pages have no lots.
Vernissage lists every lot it has
offered in the same shop feed as its stock, with the outcome in the lot's name: *Alghind 1800 €,
Haamrihind 1800 €*; *Haamrihind: €* for a lot that found no buyer; *MÜÜDUD* for one sold after the
sale at a price the house did not print. All are kept — an unsold lot is a result too, and leaving it
out would bias every artist's line upward — with the starting price, the hammer price where there is
one, and the sale. A lot that drew no bid in the sale and was sold afterwards, at the start price or
at a price the house then agreed, reads *sold* like any other; the record notes that no one bid: Haus prints such a sale as *Haamrihind* on
the sale page beside a dash for the last bid, Vernissage as *Haamrihind: müüdud*, EKO as *Müüdud (0)*.
A lot in a sale that has not yet taken place is not a result and waits; a lot the house could not
attribute, or attributed to two hands, is left out. The two prices are the only prices
in the catalogue: gallery asking prices are never taken.

**House spellings.** The houses write names their own way — *Amandus Heinrich Adamson*, *Carl Timoleon
von Neff*, *Woldemar Tank* — and each spelling was becoming an artist beside the museum's. A gallery or
house name is taken as a catalogued artist's when the surname matches and every given name of the
shorter form has a close match in the longer (C/K, W/V, X/KS folded; one letter of slack, none for
names under four letters), with one candidate only and the generation word agreeing. 49 resolved.

**Biographies** are the holder's text, whole: MuIS's are two or three paragraphs and an earlier
harvest kept only the longest, which opened Priidu Aavik's life at "on returning to Estonia".

**Translations.** The biographies and record descriptions are Estonian, as the holders wrote them, and
that text is the canonical one. The English interface shows a machine translation of each — made once
with the Claude API (`data/translate.py`, Sonnet 5), cached by a hash of the source text so a text is never
sent twice, and marked *translated* wherever it appears with the note that it is unedited. Names, titles,
inventory numbers, measurements and quoted inscriptions are kept as written; the prompt forbids
summarising, adding or omitting. 895 biographies and 17,160 descriptions; the monthly run translates
whatever is new. The 57 English biographies from the Centre for Contemporary Art are theirs, not translations.

**Similar artists.** Six per artist, computed, not chosen (`data/similar.py`): the same decades, the same
media and techniques, the same subjects in the titles — landscape, portrait, nude, still life, city, sea —
and, where the record knows it, the same movement, school or museum category, each a cosine, weighted
with period and medium first; only artists with five or more works are offered as neighbours. It is a
"more like this" for a reader who liked what they saw, not a statement of influence.

**Editorial.** The sixteen names on the landing page are chosen, not counted, and tagged *ed*. Decade
notes and the English medium vocabulary are editorial. Everything else on a record is the holder's.

## The site

The register groups by decade, artist or **auction sale** — every filter applying to each. A broad view
opens on a mosaic, one column per century and a cell per decade, each as large as its share. **For sale**
in the masthead opens everything a gallery is selling; **auctioned** opens the results, sale by sale.
Every gallery row links out with *For sale ↗*; every lot with its hammer price. The
**shortlist** (bookmark on each row) is kept in the browser, exports as CSV and shares as a link that
carries the keys. Each decade bar shows its for-sale share hatched, because since NOBA the 2020s bar
is 98% gallery stock and unsplit it read as the most-collected decade in Estonian history.

`site/a/` holds a static page per artist for crawlers, each linking to related artists by school and
period, and `site/404.html` prefills a search from any stale artist address.

## Two builds, and which one is current

`site/` is canonical. It shards its data and fetches on demand, so it has no size
limit and is rebuilt on every push.

`register.html` is a single self-contained file, published as a Claude Artifact.
Artifacts cap at 16 MB and cannot fetch anything at runtime, so the whole catalogue
has to fit in the file — which stopped being possible at around 52,000 works. It is
now a **dated snapshot**: it says so on its own masthead, in both languages, and
links to the live site. Rebuild it deliberately with `python3 build_artifact.py`,
not as part of the normal cycle.

## Reusing the data

`data/data.json` is dictionary-encoded and nested, which suits the site and suits
nobody else. Flat exports with every value resolved, one row per work:

    site/data/export/works.csv.gz      100,313 rows
    site/data/export/artists.csv.gz     5,349 rows
    site/data/export/works.jsonl.gz     one JSON object per line

Rebuild them with `python3 data/export_csv.py`. `data/validate.py` runs the sanity
checks — no orphan artists, no impossible years, no undecoded HTML entities, no
Wikidata description contradicting a museum's own dates — and exits non-zero on a
failure, so a bad merge stops the build rather than shipping.

## Schema

`data/data.json` has four top-level keys: `meta`, `artists`, `works`, `vocab`.

Repeated string values are dictionary-encoded: fields listed in `meta.encoded` hold an integer
index into the same-named array in `vocab`. So `w.mu == 0` means
`vocab.mu[0] == "Eesti Kunstimuuseum"`.

**works** — one entry per artwork:

| Key | Meaning |
|---|---|
| `a` | index into `artists` |
| `t` | title |
| `y` | year (integer, `null` when undated) |
| `yl` | the date as the museum wrote it (`"ca 1840"`, `"1930s"`) |
| `e` / `ee` | object type, EN / ET *(encoded)* |
| `tc` / `tce` | technique, EN / ET *(encoded)* |
| `m` / `me` | material, EN / ET *(encoded)* |
| `mu` | holding museum *(encoded)* |
| `co` | collection within the museum *(encoded)* |
| `c` | EKM collection category *(encoded)* |
| `s` | source catalogue *(encoded)* |
| `kind` | `held` in a museum, `gallery` at a commercial gallery, `sold` a past gallery listing, `shown` exhibited, `auction` an auction result, `known` recorded in a catalogue raisonné (`kc`: painting, sketch or lost) |
| `gs`, `gl` | past listings only: 1 the gallery marked it sold / 0 no longer listed; month last seen for sale |
| `an`, `ad`, `as`, `ap`, `ao` | auction results only: sale name, sale month `YYYY-MM`, starting price €, hammer price €, sold (1/0) |
| `nu` | inventory number |
| `d` | description, as recorded by the museum |
| `dm` | dimensions, as recorded |
| `mi` / `oi` | MuIS and EKM object identifiers, for linking back |
| `n` | how many source objects this record represents |

**artists** — `n` name, `l` [birth, death], `b` biography, `c` work count, `cit` citizenships,
`born` birthplace, `qid` Wikidata ID, `wdesc` Wikidata description, `aff` art-historical
affiliation, `ben` English biography (CCA), `ls`/`bs`/`bens` provenance of each of those.

A note on `aff`: it is derived from the Wikidata description, not from citizenship. Citizenship
turned out to be the wrong instrument — P27 lists every state a person was ever subject to, so
it cannot tell Johann Köler (Estonian) from Otto Friedrich Theodor von Möller (Baltic German)
when both read "Russian Empire". `aff` **labels** origin; it does not filter anything out.

## Building

```bash
./build_site.sh          # rebuilds site/ from data/data.json
```

The site is plain HTML, CSS and JavaScript with no build step and no dependencies. It does use
`fetch` to load the data, so it needs to be served over HTTP — `file://` will not work:

```bash
cd site && python3 -m http.server 8000
```

## How this was collected

Museum records come from MuIS and the EKM Digital Collection. The first harvest read MuIS
per artist and per collection, cached locally, then parsed, with part of it through the bulk RDF
files MuIS publishes at `/rdf/collection/`. Everything since goes through **MuIS's OAI-PMH service**
(`muis_oai.py`): the interface MuIS provides for harvesters, which lists a museum's objects by
collection and returns each record in LIDO — maker with role and dates, title, work type,
technique, measurements, description, the pictures' media ids and pixel sizes. Tartu Art Museum's
prints, watercolours, portfolios, ex-libris, sculpture and new media, the Art Museum of Estonia's
print collection, and the art collections of the National, History, Maritime and Tartu City museums
came in this way, twelve requests in flight and every answer cached; records the museum has withdrawn
(`status="deleted"`) and objects without a maker are left out. The monthly run asks the service for
new objects in those collections only. Requests identify themselves as `EstonianArtCatalogue/1.0`;
the metadata is CC0 by MuIS's own statement. MuIS's object pages are never fetched again.

Gallery records come from each gallery's own public listings — WooCommerce's documented Store API
where one exists (Vernissage, NOBA), otherwise the pages themselves. NOBA's artist pages were read
once each for the artist's stated country of location, biography, and the addresses of their artwork
pages. Prices are never collected, and every record links back to the gallery's page. A site's
`robots.txt` is read before it is collected from, and the monthly run re-reads every one
(`data/robots_check.py`) and stops if any source says no, so a site that changes its mind is heard the
next month. Each is fetched at the pace its file asks — `alleegalerii.ee`'s ten-second delay, for one —
and a page already read is not read again.

**Gallery stock is re-harvested monthly** by `.github/workflows/reharvest.yml`, at 04:00 UTC on the
1st: every gallery fetched afresh, rebuilt, README figures updated, committed. `data/harvest_guard.py`
refuses the run if any gallery comes back empty or down more than 40%, so a redesigned site fails
loudly rather than vanishing quietly. The museum sources are never re-crawled by it.

**Images, for public-domain works only.** A museum record shows the holder's own photograph — loaded
from the museum's server when the record is opened, never copied or stored here — when the work is out
of copyright: the artist dead more than seventy years, or born more than 156 years ago with no death
recorded. A faithful photograph of a public-domain work is not itself protected: Autoriõiguse seadus § 5 p. 9
(in force 7 January 2022, implementing Directive (EU) 2019/790 art. 14) takes the Act away from *any material
obtained by reproducing a work of visual art whose term of protection has expired*, unless the reproduction is
an original creation of its own — which a museum's record photograph is not. That holds whatever a catalogue's
rights label says; MuIS marks most images *rights undetermined*, EKM's notice claims its site's content. Images
appear only inside a record, are never offered for download, and any holder can have one removed by asking. Everything by a later artist has no image — a rule of this catalogue, recomputed each January
from life + 70, not a line the law draws at 1955. MuIS's open-data RDF says it in one sentence: *metadata can be used
according to CC0 licence; usage of digital images may be subject to restrictions* — and for a faithful photograph
of a public-domain work no such restriction can rest on copyright. MuIS images come by media id from the record,
the same id MuIS's persistent identifier `opendata.muis.ee/dhmedia/<id>` names, which the picture links to;
EKM's by the file path the search listing pairs with each object (`data/ekm_images.py`) — the object
pages sit behind a login and show a highlights carousel to everyone else, which an earlier pass had
read as the object's image.

A work a gallery is selling now shows the gallery's own photograph, embedded from the gallery's server
and captioned with the gallery, for as long as the listing is live — the one case where the party who
owns the picture wants it seen. A past listing keeps no image, and auction lots have none: once the
sale is over nobody but this catalogue has an interest in illustrating it, and the artist and the
buyer may have one against. Any holder or rights holder can have an image removed by asking.

**The artwall.** A view with pictures enough to be one — an artist, a decade, a search, with twelve
pictures or more — opens as an artwall of them, paintings first, the works without a
picture listed beneath; *List* and *Artwall* switch it for that view — change the artist, decade or search and the rule decides again — and a choice travels in the link. The tiles
are the same images as the records, loaded from the holders' and galleries' servers as they scroll
into view, seventy-two at a time. On an artist's own wall the key works come first; on a mixed wall
— a decade, a search, the whole catalogue — the sixteen names of the door and every highlighted work
come first and the artists take turns, dealt in a fixed shuffle rather than by year, so it opens on
Mägi, Estna, Triik and Wiiralt side by side rather than on the 1440s. Nothing is on the artwall
that is not in a record.

**What comes first on an artist's wall.** Paintings, then watercolours, sculpture, drawings and prints; and for
thirteen artists whose key works are a matter of record — Wiiralt's *Põrgu* and *Kabaree*, Mägi's Norway and
Saaremaa pictures, Köler's *Truu valvur*, Raud's and Kallis's Kalevipoeg cycles — those works come before the
rest, in the order `data/highlights.json` gives them, the finished work before its studies. A hand-kept list,
open to correction. Impressions of one print, casts of one sculpture and the versions of a highlighted
composition show as one tile, marked ×n.

**Visits are counted, visitors are not.** The site loads GoatCounter, which keeps a count of page
views by page, referrer and country, without cookies and without storing anything that identifies
a person.

## Licence

Code: MIT (see `LICENSE`).

**Data is mixed, and the split is in the data itself.** Records marked `kind: held` —
78,958 of them, 78.7% — derive from museum metadata published under CC0, which carries no
restriction on reuse, commercial included. The 9,985 records marked `kind: gallery` come from
commercial galleries and the NOBA marketplace, which grant no licence; they are included as a
public catalogue of current work, and anyone reusing this dataset should decide for themselves
whether to keep them. One filter on `kind` separates the two. Biographies and birth years tagged
*NOBA* are NOBA's or the artist's own text.

Attribution to the holding institution is carried in every record, and every record links back
to its source.

Corrections and removal requests are welcome — open an issue on this repository.
