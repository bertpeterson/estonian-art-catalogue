# Estonian Art Catalogue · Eesti Kunstikataloog

A browsable catalogue of **52,085 artworks** by **3,664 artists** — museum holdings from **24 Estonian public
collections**, plus current work from three commercial galleries, aggregated from the national museum databases and presented as a static site.

Every record is a real museum object and links back to its source record. Nothing here is
invented, reconstructed, or filled in by hand.

**Live site:** https://bertpeterson.github.io/estonian-art-catalogue/

---

## Sources

| Source | Records | What it is |
|---|---|---|
| [MuIS](https://www.muis.ee) | 27,681 | Muuseumide Infosüsteem — the shared catalogue of all Estonian museums |
| [EKM Digital Collection](https://digikogu.ekm.ee) | 27,711 | The Art Museum of Estonia's own database, behind Kumu |
| [CCA Estonia](https://cca.ee) | 58 bios | Centre for Contemporary Art — artist biographies, Venice Biennale archive |
| [EKKM](https://ekkm.ee) | — | Contemporary Art Museum of Estonia |
| [Wikidata](https://www.wikidata.org) | 1,793 |
| Seven commercial galleries | 4,224 | Commercial galleries — current work, metadata only, no prices | Birthplace, dates, and art-historical affiliation for artists |

7,551 objects appear in both MuIS and the EKM database and are merged on inventory number
(MuIS `Number` = digikogu `Tulmenumber` + `Kogunumber`), which is why 61,363 source objects
collapse to 47,899 works.

**Only attributed works are included.** Anonymous and unattributed objects are excluded by design.

Metadata in MuIS is published under CC0. This repository redistributes **metadata only** — no
images are harvested, stored, or served. Each record carries the identifiers needed to reach
the original entry at its holding institution.

## What's in the repository

```
site/                 the deployable static site (open index.html over HTTP)
  data/index.json     9.3 MB — everything the list, search and facets need
  data/detail/<decade>.json  46 shards — descriptions, dimensions, collapsed duplicates
register.html         the same catalogue as one self-contained 13.6 MB HTML file
data/data.json        the merged dataset (see Schema below)
data/*.py             the harvest, enrichment and merge scripts
tpl_head.html         markup + CSS for the app
tpl_app.html          the application itself
i18n.json             the EN/ET dictionary
build_site.py/.sh     rebuilds site/ from data/data.json
```

Two things are deliberately **not** committed, because they are large and re-derivable:
the ~490 MB of cached source pages (`data/cache/`, `data/dkcache/`, `data/cca_cache/`) and the
raw per-source harvest dumps that `data/merge.py` reads. Re-run the harvest scripts to
regenerate them; `data/data.json`, the thing everything else is built from, is committed.

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

## Licence

Code: MIT (see `LICENSE`).

Metadata: aggregated from sources that publish under CC0 or equivalent open terms, and shared
here on the same basis. Attribution to the holding institutions is carried in every record.
