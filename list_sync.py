# -*- coding: utf-8 -*-
"""My List across devices: list-sync.js, copied into site/, and the tag that loads it.

The pages that have the list (the register, the mood wall, Buy art) put TAG in their <head>, before their own
script, which is how the script reads a sign-in link's token before the page reads the address. data-list-api is
the Worker's address (data/mood_api.json). It is on only with "lists": true there, set once the Worker has its KV store
and mail key (worker/README.md), or MUSEAAL_LISTS=1 for a local build; else TAG is empty and the list stays in the browser."""
import hashlib, json, os, shutil

_cfg = json.load(open("data/mood_api.json", encoding="utf-8")) if os.path.exists("data/mood_api.json") else {}
_api = (_cfg.get("url") or "") if _cfg.get("lists") or os.environ.get("MUSEAAL_LISTS") == "1" else ""
_src = open("list-sync.js", "rb").read()
TAG = (f'<script src="/list-sync.js?v={hashlib.sha256(_src).hexdigest()[:10]}" data-list-api="{_api}"></script>') if _api else ""
os.makedirs("site", exist_ok=True)
shutil.copyfile("list-sync.js", "site/list-sync.js")
