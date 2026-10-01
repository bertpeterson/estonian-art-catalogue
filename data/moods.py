# -*- coding: utf-8 -*-
"""Art by mood: how strongly each museum picture answers to a word -> moods.json

A visitor picks a few words -- solemn, misty, tender -- and sees the paintings that
answer to them. The pictures' CLIP embeddings are already made (lookalikes.py, cached in
embcache/); CLIP puts words in the same space, so each word is written out as a few
short phrases ("a solemn painting", "an artwork that feels solemn"), embedded by the
same model's text side and averaged, and every picture is scored by its cosine to it.

A raw cosine favours some pictures for every word, so a picture's score for a word is
taken relative to its own mean over the whole vocabulary: what it is more than it is
anything else. Each word's scores are then made z-scores across all pictures, so the
words add up evenly when a visitor picks two or three.

Only museum pictures (and the Mägi Foundation's known works): gallery stock changes
weekly. Per word and kind (paintings, works on paper, all art) the best 400 are kept, one impression per print, at most three works
by one artist in a word's first 60.

    .venv-clip/bin/python moods.py        (from data/; after lookalikes.py)
"""
import json, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KEEP, SHOWN, PER_ARTIST = 400, 60, 3

# group, English, Estonian, the words CLIP is given (the first is the label's own)
VOCAB = [
    ("feeling", "solemn", "pühalik", ["solemn", "grave and dignified"]),
    ("feeling", "serene", "rahulik", ["serene", "calm and peaceful"]),
    ("feeling", "contemplative", "mõtlik", ["contemplative", "thoughtful, lost in thought"]),
    ("feeling", "melancholy", "melanhoolne", ["melancholy", "sad and wistful"]),
    ("feeling", "lonely", "üksildane", ["lonely", "a solitary figure alone"]),
    ("feeling", "nostalgic", "nostalgiline", ["nostalgic", "a memory of old times"]),
    ("feeling", "tender", "õrn", ["tender", "gentle and affectionate"]),
    ("feeling", "intimate", "intiimne", ["intimate", "a private, close moment"]),
    ("feeling", "joyful", "rõõmus", ["joyful", "happy and cheerful"]),
    ("feeling", "playful", "mänguline", ["playful", "whimsical and light-hearted"]),
    ("feeling", "festive", "pidulik", ["festive", "a celebration"]),
    ("feeling", "romantic", "romantiline", ["romantic", "a romantic scene"]),
    ("feeling", "dreamy", "unenäoline", ["dreamy", "dreamlike and surreal"]),
    ("feeling", "mysterious", "salapärane", ["mysterious", "enigmatic and strange"]),
    ("feeling", "eerie", "kõhe", ["eerie", "uncanny and unsettling"]),
    ("feeling", "anxious", "ärev", ["anxious", "tense and uneasy"]),
    ("feeling", "gloomy", "sünge", ["gloomy", "dark and brooding"]),
    ("feeling", "dramatic", "dramaatiline", ["dramatic", "full of drama and movement"]),
    ("feeling", "heroic", "kangelaslik", ["heroic", "mythic heroes"]),
    ("light", "bright", "hele", ["bright", "full of light"]),
    ("light", "dark", "tume", ["dark", "in deep shadow"]),
    ("light", "sunny", "päikeseline", ["sunny", "bright sunlight"]),
    ("light", "golden", "kuldne", ["golden", "golden light"]),
    ("light", "twilight", "hämar", ["twilight", "dusk, the light fading"]),
    ("light", "moonlit", "kuuvalge", ["moonlit", "a night lit by the moon"]),
    ("light", "misty", "udune", ["misty", "fog and haze"]),
    ("colour", "vivid", "erk", ["vivid", "vivid, saturated colours"]),
    ("colour", "muted", "mahe", ["muted", "soft, muted colours"]),
    ("colour", "warm", "soe", ["warm", "warm reds and oranges"]),
    ("colour", "cold", "külm", ["cold", "cold blues and greys"]),
    ("weather", "stormy", "tormine", ["stormy", "a storm, wind and waves"]),
    ("weather", "still", "vaikne", ["still", "silent and motionless"]),
    ("weather", "wintry", "talvine", ["wintry", "snow and winter"]),
    ("weather", "spring", "kevadine", ["spring", "springtime, blossom"]),
    ("weather", "summery", "suvine", ["summery", "a summer day"]),
    ("weather", "autumnal", "sügisene", ["autumnal", "autumn colours"]),
]
# what a picture shows, a second axis: shown as chips under "Subject" and read by the
# free-text search; scored against each other, not against the moods
SUBJECTS = [
    ("subject", "sea", "meri", ["the sea", "a seascape"]),
    ("subject", "lake", "järv", ["a lake", "a lakeside"]),
    ("subject", "river", "jõgi", ["a river", "a stream"]),
    ("subject", "forest", "mets", ["a forest", "woods"]),
    ("subject", "trees", "puud", ["trees", "a tree"]),
    ("subject", "fields", "põllud", ["fields", "farmland and meadows"]),
    ("subject", "garden", "aed", ["a garden", "a park"]),
    ("subject", "mountains", "mäed", ["mountains", "hills and mountains"]),
    ("subject", "sky", "taevas", ["the sky and clouds", "a big sky"]),
    ("subject", "village", "küla", ["a village", "farmhouses"]),
    ("subject", "city", "linn", ["a city street", "town houses"]),
    ("subject", "harbour", "sadam", ["a harbour", "a port with ships"]),
    ("subject", "church", "kirik", ["a church", "a church interior"]),
    ("subject", "interior", "interjöör", ["a room interior", "inside a house"]),
    ("subject", "portrait", "portree", ["a portrait", "a person's face"]),
    ("subject", "children", "lapsed", ["children", "a child"]),
    ("subject", "family", "pere", ["a family", "mother and child"]),
    ("subject", "work", "töö", ["people working", "labour in the fields"]),
    ("subject", "music", "muusika", ["music", "a musician"]),
    ("subject", "dance", "tants", ["dancing", "dancers"]),
    ("subject", "horses", "hobused", ["horses", "a horse"]),
    ("subject", "animals", "loomad", ["animals", "cattle and dogs"]),
    ("subject", "birds", "linnud", ["birds", "a bird"]),
    ("subject", "flowers", "lilled", ["flowers", "a bouquet"]),
    ("subject", "stilllife", "vaikelu", ["a still life", "objects on a table"]),
    ("subject", "boats", "paadid", ["boats", "a sailing boat"]),
]
# moods the chips do not show, for the free-text search to reach
MORE = [
    ("more", "hopeful", "lootusrikas", ["hopeful", "full of hope"]),
    ("more", "cosy", "hubane", ["cosy", "warm and homely"]),
    ("more", "sacred", "püha", ["sacred", "holy and religious"]),
    ("more", "majestic", "majesteetlik", ["majestic", "grand and monumental"]),
    ("more", "fragile", "habras", ["fragile", "delicate"]),
    ("more", "sensual", "meeleline", ["sensual", "sensuous"]),
    ("more", "innocent", "süütu", ["innocent", "pure and naive"]),
    ("more", "energetic", "energiline", ["energetic", "full of energy and movement"]),
    ("more", "proud", "uhke", ["proud", "self-assured"]),
    ("more", "elegant", "elegantne", ["elegant", "refined and graceful"]),
    ("more", "lively", "elav", ["lively", "bustling with people"]),
    ("more", "empty", "tühi", ["empty", "deserted"]),
    ("more", "spiritual", "vaimne", ["spiritual", "transcendent"]),
    ("more", "idyllic", "idülliline", ["idyllic", "pastoral and peaceful"]),
    ("more", "wild", "metsik", ["wild", "untamed nature"]),
    ("more", "harsh", "karm", ["harsh", "hard and severe"]),
    ("more", "angry", "vihane", ["angry", "furious"]),
    ("more", "abstract", "abstraktne", ["abstract", "non-figurative"]),
    ("more", "expressive", "ekspressiivne", ["expressive", "expressionist brushwork"]),
    ("more", "decorative", "dekoratiivne", ["decorative", "ornamental pattern"]),
    ("more", "simple", "lihtne", ["simple", "plain and minimal"]),
    ("more", "ornate", "rikkalik", ["ornate", "richly detailed"]),
    ("more", "rustic", "maalähedane", ["rustic", "peasant life"]),
    ("more", "modern", "modernne", ["modernist", "modern art"]),
]
TEMPLATES = ["a {} painting", "a painting that feels {}", "an artwork: {}", "a {} scene, fine art"]
SUBJECT_TEMPLATES = ["a painting of {}", "a picture of {}", "{}, fine art", "an artwork showing {}"]
# what a visitor can narrow to, by the record's category; objects (jugs, spoons, boxes),
# photographs, albums and printed ephemera answer to no mood and are left out
PAINT = {"Painting", "Watercolour", "Mixed media", "Miniature"}
PAPER = {"Drawing", "Print", "Sketch", "Caricature", "Illustration", "Bookplate", "Koomiks", "Siluett", "Cutting"}
ART = PAINT | PAPER | {"Sculpture"}

def main():
    import torch, open_clip
    d = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
    A, W = d["artists"], d["works"]
    key = lambda w: w.get("k") or re.sub(r"[^A-Z0-9:]", "", (w.get("nu") or "").upper())
    E = np.load(os.path.join(HERE, "embcache", "emb.npy")).astype(np.float32)
    ids = json.load(open(os.path.join(HERE, "embcache", "ids.json")))
    at = {im: n for n, im in enumerate(ids)}
    target = lambda w: str(w.get("im") or "")[:2] in ("m:", "e:") or w.get("kind") == "known"
    # one row per picture; the work that stands for it is the first with it
    E_ = d["vocab"]["e"]
    cat = lambda w: E_[w["e"]] if isinstance(w.get("e"), int) and w["e"] < len(E_) else None
    first = {}
    for i, w in enumerate(W):
        im = w.get("im")
        if im and im in at and target(w) and im not in first and (cat(w) in ART or w.get("kind") == "known"): first[im] = i
    rows = sorted(first); X = E[[at[im] for im in rows]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    wi = [first[im] for im in rows]
    print(f"{len(rows):,} museum pictures with an embedding", flush=True)

    model, _, _ = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    tok = open_clip.get_tokenizer("ViT-B-32"); model.eval()
    def embed(vocab, templates):
        T = []
        with torch.no_grad():
            for _, en, _, words in vocab:
                ph = [t.format(x) for x in words for t in templates]
                f = model.encode_text(tok(ph)).float(); f = f / f.norm(dim=-1, keepdim=True)
                m = f.mean(0); T.append((m / m.norm()).numpy())
        return np.stack(T)                                # words x 512
    scale = []
    def zscores(T):
        S = X @ T.T                                       # pictures x words
        S = S - S.mean(axis=1, keepdims=True)             # what a picture is more than anything else in its set
        scale.append((T, S.mean(axis=0), S.std(axis=0) + 1e-9))
        return (S - S.mean(axis=0)) / (S.std(axis=0) + 1e-9)   # words on one scale
    # moods against moods, subjects against subjects: a picture's subject does not
    # decide its mood, nor the reverse
    Z = np.concatenate([zscores(embed(VOCAB + MORE, TEMPLATES)), zscores(embed(SUBJECTS, SUBJECT_TEMPLATES))], axis=1)
    ALL = VOCAB + MORE + SUBJECTS
    # the words and the museum pictures' scale, for stock_moods.py: a gallery's picture
    # is scored on the same scale without the museum embeddings (CI has none)
    (T1, m1, s1), (T2, m2, s2) = scale
    np.savez_compressed(os.path.join(HERE, "mood_words.npz"), T=np.concatenate([T1, T2]).astype(np.float32),
                        mu=np.concatenate([m1, m2]), sd=np.concatenate([s1, s2]), split=len(T1),
                        words=np.array([en for _, en, _, _ in ALL]))

    tnorm = lambda w: re.sub(r"[^a-zõäöüšž0-9]+", " ", (w.get("t") or "").lower()).strip()
    kinds = {"all": lambda w: True,
             "paint": lambda w: cat(w) in PAINT or w.get("kind") == "known",
             "paper": lambda w: cat(w) in PAPER}
    out = {"words": [{"g": g, "en": en, "et": et} for g, en, et, _ in ALL]}
    for kn, ok in kinds.items():
        out[kn] = {}
        for j, (_, en, _, _) in enumerate(ALL):
            order = np.argsort(-Z[:, j]); picked, seen, per = [], set(), {}
            for r in order:
                w = W[wi[r]]
                if not ok(w): continue
                tk = (w["a"], tnorm(w))
                if tk in seen: continue
                if len(picked) < SHOWN and per.get(w["a"], 0) >= PER_ARTIST: continue
                seen.add(tk); per[w["a"]] = per.get(w["a"], 0) + 1
                picked.append([key(w), round(float(Z[r, j]), 2)])       # by the work's key: positions move at every merge
                if len(picked) == KEEP: break
            out[kn][en] = picked
    json.dump(out, open(os.path.join(HERE, "moods.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"moods.json: {len(ALL)} words x {len(kinds)} kinds, {KEEP} works each", flush=True)

if __name__ == "__main__":
    main()
