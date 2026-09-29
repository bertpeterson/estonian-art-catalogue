# -*- coding: utf-8 -*-
"""Is there a person in it? The Lihtsad Kipskassid photographs -> kipskassid_photos.json

kipskassid.py shows a photograph only once it has been looked at here and shows no one.
Each new or changed photograph (its 640 px copy) is looked at twice: Apple's Vision
framework, for faces and human figures (macOS; a small Swift tool, compiled here), and
CLIP, for "a photo of a person" against a plaster cat on its own. Either one seeing a
person hides it. Both err: Vision took painted cat faces and a toy monkey for people, and
CLIP missed people holding their cats close -- together, on the 316 photographs of
September 2026, they missed none that a look by eye found. A verdict can be corrected by
hand in kipskassid_photos.json ("ok" / "people").

    python3 kipskassid_check.py        (from data/, on the Mac; then kipskassid.py again)
"""
import json, os, subprocess, tempfile, urllib.request, time, sys
UA = "EstonianArtCatalogue/1.0 (museaal.ee; contact info@museaal.ee)"
OUT = "kipskassid_photos.json"
SWIFT = r'''
import Foundation
import Vision
import ImageIO
for path in CommandLine.arguments.dropFirst() {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print("\(path)\t-1\t-1"); continue }
    let faces = VNDetectFaceRectanglesRequest(), humans = VNDetectHumanRectanglesRequest()
    humans.upperBodyOnly = false
    do { try VNImageRequestHandler(cgImage: img, options: [:]).perform([faces, humans]) } catch { print("\(path)\t-1\t-1"); continue }
    let f = (faces.results ?? []).filter { $0.confidence >= 0.5 }.count, h = (humans.results ?? []).count
    print("\(path)\t\(f)\t\(h)")
}
'''

def main():
    seen = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    recs = [r for r in json.load(open("gallery_records.json", encoding="utf-8")) if r["gid"].startswith("kipskass-") and r.get("photo")]
    todo = {r["photo"]: r["photo_url"] for r in recs if r["photo"] not in seen and r.get("photo_url")}
    print(f"{len(todo)} photographs to look at ({len(seen)} looked at before)")
    if not todo: return
    tmp = tempfile.mkdtemp()
    files = {}
    for n, (photo, url) in enumerate(todo.items()):
        p = os.path.join(tmp, f"{n}.img")
        try:
            open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read())
            files[photo] = p
        except Exception as e:
            print("  could not read", photo, repr(e)[:60])
        time.sleep(0.5)
    # Vision
    tool = os.path.join(tmp, "people")
    open(tool + ".swift", "w").write(SWIFT)
    subprocess.run(["swiftc", "-O", tool + ".swift", "-o", tool], check=True, capture_output=True)
    out = subprocess.run([tool, *files.values()], capture_output=True, text=True).stdout
    vision = {}
    for line in out.splitlines():
        path, f, h = line.split("\t")
        vision[path] = int(f) > 0 or int(h) > 0
    # CLIP, where the venv has it
    clip = {}
    try:
        import torch, open_clip
        from PIL import Image
        model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k"); model.eval()
        tok = open_clip.get_tokenizer("ViT-B-32")
        P = ["a photo of a person", "a photo of a man", "a photo of a woman", "a person holding a small statue", "people at an event", "a portrait photo of a human face", "a child"]
        N = ["a painted plaster cat figurine", "a ceramic cat statue on a table", "a cat figurine on a shelf", "a small painted cat sculpture", "a cat statue next to flowers", "a mannequin and a cat figurine"]
        with torch.no_grad():
            T = model.encode_text(tok(P + N)).float(); T /= T.norm(dim=-1, keepdim=True)
            for photo, p in files.items():
                x = model.encode_image(pre(Image.open(p).convert("RGB")).unsqueeze(0)).float(); x /= x.norm(dim=-1, keepdim=True)
                l = (100 * x @ T.T)[0]
                pp = torch.softmax(torch.stack([l[:len(P)].max(), l[len(P):].max()]), 0)[0].item()
                clip[photo] = pp >= 0.3
    except ImportError:
        print("  CLIP not here (run with .venv-clip/bin/python for both checks); Vision alone")
    for photo, p in files.items():
        seen[photo] = "people" if vision.get(p) or clip.get(photo) else "ok"
    json.dump(dict(sorted(seen.items())), open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"looked at {len(files)}: {sum(1 for p in files if seen[p] == 'people')} with a person, hidden; the rest shown")

if __name__ == "__main__":
    main()
