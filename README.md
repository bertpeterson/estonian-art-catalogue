# Estonian Art Catalogue · Eesti Kunstikataloog

A browsable catalogue of **63,542 artworks** by **4,163 artists** — museum holdings from **24 Estonian public
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
| [MuIS](https://www.muis.ee) | 27,237 | Muuseumide Infosüsteem — the shared catalogue of all Estonian museums |
| [EKM Digital Collection](https://digikogu.ekm.ee) | 27,681 | The Art Museum of Estonia's own database, behind Kumu |
| [CCA Estonia](https://cca.ee) | 58 bios | Centre for Contemporary Art — artist biographies, Venice Biennale archive |
| [EKKM](https://ekkm.ee) | — | Contemporary Art Museum of Estonia |
| [Wikidata](https://www.wikidata.org) | 1,629 artists | Dates, birthplace, description, training and art-historical affiliation — matched on name, gated on dates and occupation (see *Rules*) |
| Seven commercial galleries and NOBA | 6,151 | Haus, Vernissage, Temnikova & Kasela, Tütar, Artrovert, Kogo, Ruki — current stock from each gallery's own site; and [NOBA](https://noba.ac), the Nordic-Baltic marketplace, for artists the catalogue already holds or whose NOBA page places them in Estonia. Metadata only, never prices |
| Auction results: Haus Galerii, Allee galerii, Vernissage, Eesti Kunsti Oksjonid | 9,830 lots | Every lot in Haus Galerii's hundred sales since 1998, Allee galerii's fifteen since 2020, Vernissage's fifteen since 2021 and Eesti Kunsti Oksjonid's eighteen since 2023, as the house published it: starting price, hammer price, sold or unsold. A record of what happened at auction, not a valuation |

Of the works for sale, 7,039 are NOBA listings, 2,946 the galleries' own. NOBA also supplies a short
biography, written by the artist or NOBA, for 544 artists who have none from a museum, and a birth year
read from that biography for 301 — both tagged *NOBA* on the page.

7,415 objects appear in both MuIS and the EKM database and are merged on inventory number
(MuIS `Number` = digikogu `Tulmenumber` + `Kogunumber`), which is why 60,750 source objects
collapse to 63,542 works.

**Only attributed works are included.** Anonymous and unattributed objects are excluded by design — including 485 objects catalogued under the name *Tundmatu kunstnik* ("unknown artist"), which is the absence of an attribution written into the name field rather than a name. Notnames stay: *Püha Lucia legendi meister* and its kind identify a hand recognised across several works, and art history treats that as an attribution.

Metadata in MuIS is published under CC0. This repository redistributes **metadata only** — no
images are harvested, stored, or served. Each record carries the identifiers needed to reach
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

**Auction results** are a kind of their own, neither a holding nor stock. Haus Galerii publishes its
whole archive — a page per sale since 1997, a figure per lot with starting price, last bid and hammer
price, kroon-era prices shown by the house in euro at the fixed rate. Allee galerii keeps a page per sale
with the lot line, starting and hammer price, and the medium on the lot's own page. Eesti Kunsti Oksjonid keeps each
online sale's page up with the final bid on every lot — *Lõpppakkumine – (0)* for a lot nobody bid on — but prints no
date, so the sale is placed by the day its name gives and the month its lots were listed. Vernissage lists every lot it has
offered in the same shop feed as its stock, with the outcome in the lot's name: *Alghind 1800 €,
Haamrihind 1800 €*; *Haamrihind: €* for a lot that found no buyer; *MÜÜDUD* for one sold after the
sale at a price the house did not print. All are kept — an unsold lot is a result too, and leaving it
out would bias every artist's line upward — with the starting price, the hammer price where there is
one, and the sale. A lot in a sale that has not yet taken place is not a result and waits; a lot the
house could not attribute, or attributed to two hands, is left out. The two prices are the only prices
in the catalogue: gallery asking prices are never taken.

**House spellings.** The houses write names their own way — *Amandus Heinrich Adamson*, *Carl Timoleon
von Neff*, *Woldemar Tank* — and each spelling was becoming an artist beside the museum's. A gallery or
house name is taken as a catalogued artist's when the surname matches and every given name of the
shorter form has a close match in the longer (C/K, W/V, X/KS folded; one letter of slack, none for
names under four letters), with one candidate only and the generation word agreeing. 49 resolved.

**Biographies** are the holder's text, whole: MuIS's are two or three paragraphs and an earlier
harvest kept only the longest, which opened Priidu Aavik's life at "on returning to Estonia".

**Editorial.** The sixteen names on the landing page are chosen, not counted, and tagged *ed*. Decade
notes and the English medium vocabulary are editorial. Everything else on a record is the holder's.

## The site

The register groups by decade, artist or **timeline** — one bar per artist with a known birth year, a
darker segment for the years the catalogue holds dated work from, every filter applying. **For sale**
in the masthead opens everything a gallery is selling; the line under the names opens the 325 artists
who are both in a museum and on the market. Every gallery row links out with *For sale ↗*. The
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

    site/data/export/works.csv.gz      63,542 rows
    site/data/export/artists.csv.gz     4,163 rows
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
| `kind` | `held` in a museum, `gallery` at a commercial gallery, `shown` exhibited, `auction` an auction result |
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

Museum records come from MuIS and the EKM Digital Collection, fetched per artist and per
collection and cached locally, then parsed. Requests identified themselves as
`EstonianArtCatalogue/1.0`, every page was cached so nothing was fetched twice, and part of
the MuIS harvest used the bulk RDF files it publishes at `/rdf/collection/`. **A refresh
should go through those bulk files and the OAI interface rather than fetching object pages.**

Gallery records come from each gallery's own public listings — WooCommerce's documented Store API
where one exists (Vernissage, NOBA), otherwise the pages themselves. NOBA's artist pages were read
once each for the artist's stated country of location, biography, and the addresses of their artwork
pages. Prices are never collected, and every record links back to the gallery's page. Where a site
asked not to be collected from, it was not: `alleegalerii.ee` sets `ClaudeBot: Disallow` and an
Article 4 reservation, and holds no records here.

**Gallery stock is re-harvested monthly** by `.github/workflows/reharvest.yml`, at 04:00 UTC on the
1st: every gallery fetched afresh, rebuilt, README figures updated, committed. `data/harvest_guard.py`
refuses the run if any gallery comes back empty or down more than 40%, so a redesigned site fails
loudly rather than vanishing quietly. The museum sources are never re-crawled by it.

**Images are deliberately absent.** MuIS states a licence per image, and none of the 31,000
carry a permissive one — 26,308 are marked *rights undetermined*, 4,905 *protected by
copyright*. An attempt at hotlinking EKM thumbnails was reverted: their pages lead with a
related-works carousel, so the images attached to the wrong artworks.

## Licence

Code: MIT (see `LICENSE`).

**Data is mixed, and the split is in the data itself.** Records marked `kind: held` —
47,538 of them, 74.8% — derive from museum metadata published under CC0, which carries no
restriction on reuse, commercial included. The 9,985 records marked `kind: gallery` come from
commercial galleries and the NOBA marketplace, which grant no licence; they are included as a
public catalogue of current work, and anyone reusing this dataset should decide for themselves
whether to keep them. One filter on `kind` separates the two. Biographies and birth years tagged
*NOBA* are NOBA's or the artist's own text.

Attribution to the holding institution is carried in every record, and every record links back
to its source.

Corrections and removal requests are welcome — open an issue on this repository.
