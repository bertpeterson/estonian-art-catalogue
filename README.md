# Estonian Art Catalogue · Eesti Kunstikataloog

A browsable catalogue of **57,546 artworks** by **4,050 artists** — museum holdings from **24 Estonian public
collections**, plus current work from three commercial galleries, aggregated from the national museum databases and presented as a static site.

Every record is a real museum object and links back to its source record. Nothing here is
invented, reconstructed, or filled in by hand.

**Live site (canonical):** https://museaal.ee/

---

## Sources

| Source | Records | What it is |
|---|---|---|
| [MuIS](https://www.muis.ee) | 27,237 | Muuseumide Infosüsteem — the shared catalogue of all Estonian museums |
| [EKM Digital Collection](https://digikogu.ekm.ee) | 27,681 | The Art Museum of Estonia's own database, behind Kumu |
| [CCA Estonia](https://cca.ee) | 58 bios | Centre for Contemporary Art — artist biographies, Venice Biennale archive |
| [EKKM](https://ekkm.ee) | — | Contemporary Art Museum of Estonia |
| [Wikidata](https://www.wikidata.org) | 1,678 artists | Dates, birthplace, training and art-historical affiliation |
| Seven commercial galleries and NOBA | 9,985 | Haus, Vernissage, Temnikova & Kasela, Tütar, Artrovert, Kogo, Ruki, and the NOBA marketplace for artists the catalogue already holds or who are based in Estonia — current stock, metadata only, never prices |

7,415 objects appear in both MuIS and the EKM database and are merged on inventory number
(MuIS `Number` = digikogu `Tulmenumber` + `Kogunumber`), which is why 60,750 source objects
collapse to 57,546 works.

**Only attributed works are included.** Anonymous and unattributed objects are excluded by design — including 485 objects catalogued under the name *Tundmatu kunstnik* ("unknown artist"), which is the absence of an attribution written into the name field rather than a name. Notnames stay: *Püha Lucia legendi meister* and its kind identify a hand recognised across several works, and art history treats that as an attribution.

Metadata in MuIS is published under CC0. This repository redistributes **metadata only** — no
images are harvested, stored, or served. Each record carries the identifiers needed to reach
the original entry at its holding institution.

## What's in the repository

```
site/                 the deployable static site (open index.html over HTTP)
  data/index.json     9.3 MB — everything the list, search and facets need
  data/detail/<decade>.json  46 shards — descriptions, dimensions, collapsed duplicates
register.html         a dated snapshot as one self-contained file — see below
data/data.json        the merged dataset (see Schema below)
data/*.py             the harvest, enrichment and merge scripts
tpl_head.html         markup + CSS for the app
tpl_app.html          the application itself
i18n.json             the EN/ET dictionary
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

    site/data/export/works.csv.gz      57,546 rows
    site/data/export/artists.csv.gz     4,050 rows
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
| `kind` | `held` in a museum, `gallery` at a commercial gallery, `shown` exhibited |
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

Gallery records come from each gallery's own public listings — WooCommerce's Store API where
one exists, otherwise the pages themselves. Prices are never collected, and every record
links back to the gallery's page. Where a site asked not to be collected from, it was not:
`alleegalerii.ee` sets `ClaudeBot: Disallow` and an Article 4 reservation, and holds no
records here.

**Images are deliberately absent.** MuIS states a licence per image, and none of the 31,000
carry a permissive one — 26,308 are marked *rights undetermined*, 4,905 *protected by
copyright*. An attempt at hotlinking EKM thumbnails was reverted: their pages lead with a
related-works carousel, so the images attached to the wrong artworks.

## Licence

Code: MIT (see `LICENSE`).

**Data is mixed, and the split is in the data itself.** Records marked `kind: held` —
47,538 of them, 82.6% — derive from museum metadata published under CC0, which carries no
restriction on reuse, commercial included. The 4,222 records marked `kind: gallery` come from
commercial galleries that grant no licence; they are included as a public catalogue of current
work, and anyone reusing this dataset should decide for themselves whether to keep them. One
filter on `kind` separates the two.

Attribution to the holding institution is carried in every record, and every record links back
to its source.

Corrections and removal requests are welcome — open an issue on this repository.
