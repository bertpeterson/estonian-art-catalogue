# -*- coding: utf-8 -*-
"""English translations of the Estonian prose -> translations.json

The museums, NOBA and the galleries write in Estonian: 924 artist biographies and
17,000 record descriptions (condition notes, inscriptions, provenance). The English
interface showed them untranslated. This makes an English rendering of each, once,
with the Claude API, and keeps it keyed on a hash of the source text: a text that
has not changed is never sent again, a new or edited one is translated on the next
run. The Estonian stays canonical -- it is what the Estonian interface shows and
what the holder wrote; the English is marked as a translation wherever it appears.

    python3 translate.py            # fills the cache for every untranslated text in data.json
    python3 translate.py --dry-run  # counts and estimates only

The prompt is strict: translate, do not summarise, add or omit; names, titles,
inventory numbers, measurements, dates and signatures stay as written. Batches of
texts go as a JSON array and come back as one of the same length; a batch whose
answer does not line up is retried one text at a time. merge.py applies the cache
to data.json at the end of every merge (apply_translations below), so a re-merge
never loses a translation.

Needs ANTHROPIC_API_KEY (or an `ant auth login` profile). Model: claude-sonnet-5.
"""
import json, os, sys, hashlib, time, re
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "translations.json")
MODEL = os.environ.get("MT_MODEL", "claude-sonnet-5")
BATCH_CHARS, BATCH_N, WORKERS = 9000, 25, 4

SYSTEM = """You translate Estonian art-museum catalogue text into English for a reference catalogue.

Rules:
- Translate faithfully and completely. Do not summarise, shorten, add, explain or omit anything.
- Keep verbatim: names of people and places, titles of artworks (in their quotation marks), names of institutions, inventory numbers, measurements, dates, signatures and inscriptions quoted from the work, series numbers such as "8/17".
- Keep the register: plain, factual, museum prose. Keep paragraph breaks.
- Estonian art terms: "graafiline leht" = print; "paspartuu" = mount; "plm" = plate size; "km" = image size; "lm" = sheet size; "vm" = frame size; "signeeritud" = signed; "dateeritud" = dated; "all paremal" = lower right; "all vasakul" = lower left; "pöördel" = on the verso; "Pallas" stays "Pallas"; "ERKI" stays "ERKI".
- Drop a trailing language marker such as "(eesti)" or "(est)".
- A text already in English is returned unchanged.

Input: a JSON array of strings. Output: a JSON array of strings, the same length, in the same order, nothing else -- no code fence, no commentary."""

h = lambda s: hashlib.sha1(s.strip().encode("utf-8")).hexdigest()

def apply_translations(data, cache=None):
    """Attach the cached English to artists (ben, marked bmt) and works (de). Idempotent."""
    if cache is None:
        cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    na = nw = 0
    for a in data["artists"]:
        b = a.get("b")
        if b and (not a.get("ben") or a.get("bmt")) and h(b) in cache:
            a["ben"], a["bens"], a["bmt"] = cache[h(b)], a.get("bs"), 1; na += 1
    for w in data["works"]:
        d = w.get("d")
        if d and h(d) in cache: w["de"] = cache[h(d)]; nw += 1
    return na, nw

def texts_needed(data, cache):
    out = {}
    for a in data["artists"]:
        b = a.get("b")
        if b and (not a.get("ben") or a.get("bmt")) and h(b) not in cache: out[h(b)] = b.strip()
    for w in data["works"]:
        d = w.get("d")
        if d and h(d) not in cache: out[h(d)] = d.strip()
    return out

def batches(items):
    cur, size = [], 0
    for k, t in items:
        if cur and (size + len(t) > BATCH_CHARS or len(cur) >= BATCH_N):
            yield cur; cur, size = [], 0
        cur.append((k, t)); size += len(t)
    if cur: yield cur

def translate_batch(client, batch):
    src = [t for _, t in batch]
    for attempt in range(3):
        try:
            r = client.messages.create(model=MODEL, max_tokens=16000, system=SYSTEM,
                                       messages=[{"role": "user", "content": json.dumps(src, ensure_ascii=False)}])
            text = "".join(b.text for b in r.content if b.type == "text").strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
            out = json.loads(text)
            if isinstance(out, str) and len(src) == 1: out = [out]      # a lone text sometimes comes back bare
            if isinstance(out, list) and len(out) == len(src) and all(isinstance(x, str) for x in out):
                return {k: x.strip() for (k, _), x in zip(batch, out)}, r.usage
        except json.JSONDecodeError:
            if len(src) == 1 and text and not text.startswith(("[", "{")): return {batch[0][0]: text.strip('"').strip()}, r.usage
        except Exception as e:
            # out of credit or a hard API error: stop asking, keep what is cached
            if "credit" in str(e).lower() or "billing" in str(e).lower(): raise SystemExit("  API: " + str(e)[:120])
        time.sleep(2 * (attempt + 1))
    if len(batch) == 1: print("  gave up on one text:", src[0][:60], flush=True); return {}, None
    # a batch that would not line up: one at a time
    got, usage = {}, None
    for one in batch:
        g, u = translate_batch(client, [one]); got.update(g)
    return got, usage

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    need = texts_needed(data, cache)
    chars = sum(len(t) for t in need.values())
    print(f"translations cached: {len(cache)}; to translate: {len(need)} texts, {chars:,} chars (~{chars // 3:,} tokens in)", flush=True)
    if dry or not need:
        na, nw = apply_translations(data, cache)
        if not dry:
            json.dump(data, open(os.path.join(HERE, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            print(f"applied: {na} biographies, {nw} descriptions")
        sys.exit(0)
    import anthropic
    client = anthropic.Anthropic()
    items = sorted(need.items(), key=lambda kv: -len(kv[1]))
    bl = list(batches(items)); done = 0; tin = tout = 0
    def work(b):
        got, u = translate_batch(client, b)
        return got, u
    with ThreadPoolExecutor(WORKERS) as ex:
        for got, u in ex.map(work, bl):
            cache.update(got); done += 1
            if u: tin += u.input_tokens; tout += u.output_tokens
            if done % 10 == 0 or done == len(bl):
                json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
                print(f"  {done}/{len(bl)} batches; {len(cache)} cached; tokens in {tin:,} out {tout:,}", flush=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    na, nw = apply_translations(data, cache)
    json.dump(data, open(os.path.join(HERE, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    price = {"claude-sonnet-5": (2, 10), "claude-opus-5": (5, 25), "claude-haiku-4-5": (1, 5)}.get(MODEL, (2, 10))
    print(f"\napplied: {na} biographies, {nw} descriptions; still missing {len(texts_needed(data, cache))}")
    print(f"tokens in {tin:,} out {tout:,} ≈ ${tin / 1e6 * price[0] + tout / 1e6 * price[1]:.2f} at {MODEL}")
