# museaal.ee — Estonian Art Catalogue

Static site at https://museaal.ee, built from `data/data.json`. This repo is public on GitHub: keep
anything private (keys, accounts, personal plans, correspondence) out of this file and out of commits.

## Build, test, deploy

- After data changes: `cd data && python3 merge.py`, then `./build_site.sh` (writes `site/`, which is
  gitignored; `i18n.json` is generated from `i18n.py` there).
- Smoke test: `node check_site.js` (headless Chrome over `site/`).
- Local preview with the live assistant: `.claude/launch.json` "museaal-local" (port 8767) serves `site/`
  and answers `/ask` with the current `worker/mood-worker.js` (`.dev/serve.mjs`). Build first.
- Deploy = push to `main`; `.github/workflows/pages.yml` builds and deploys. Commit locally and push only
  when the user says to publish.
- Scheduled workflows: `probe.yml` daily, `auctions.yml` Mondays, `galleries.yml` Thursdays,
  `reharvest.yml` on the 1st of the month.

## Rules

- Images: museum works only by public-domain artists, embedded live from MuIS / EKM; gallery pictures
  only for live stock, embedded from the gallery's own server. Never past listings, auction lots or
  in-copyright museum works. Embed, never copy. Settled; don't reopen.
- Prices: asking prices of current stock only (`data/asking_price.py`), never what a work sold for.
- "The artwall" means the curated first page of the landing wall, `data/masterpieces.json`. Removing
  a work from it never removes it from the catalogue.
- Never print or echo an API key in tool output.
- Never sign in to an account (Cloudflare, Google, GitHub) for the user.

## Pipelines

- Art by mood: CLIP runs locally only, in `data/.venv-clip`. After new museum pictures, run
  `lookalikes.py`, `same_pictures.py`, `moods.py`, then `taste.py`, and commit `lookalikes.json` +
  `same_pictures.json` + `moods.json` + `taste_vecs.json`;
  CI cannot run CLIP on museum pictures. Never refit `taste_proj.npz` without redoing `stock_taste.json` too.
- Buy art (`find.html` / `leia.html`): `build_ask.py` writes the pages and `site/data/stock.json`;
  stock moods and taste vectors come from `data/stock_moods.py`. "For you" ranks stock by My list
  (`museaal.shortlist` in the browser, same list as the register's bookmark).
- Worker: edit `worker/template.js`; it generates `worker/mood-worker.js`, which the user pastes into
  Cloudflare. Any Worker change needs that re-paste before it is live.
- Translations: `data/translate.py`, cached in `data/translations.json`, applied in `merge.py`.
