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

Where there is no Vision (the weekly run, on Linux), OpenCV's YuNet face detector takes its
place (models/face_detection_yunet_2023mar.onnx, from opencv/opencv_zoo, sha256 below),
at a score of 0.8, with CLIP as before. Tried on the 312 photographs looked at by eye it
found all 35 with a person and hid 57 without one: new photographs err on the hidden side.
`--todo` only says whether there is anything to look at (exit 0 if there is).
"""
import json, os, subprocess, tempfile, urllib.request, time, sys, hashlib, shutil
YUNET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "face_detection_yunet_2023mar.onnx")
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
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
    if "--todo" in sys.argv: sys.exit(0 if todo else 1)
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
    vision = {}
    if shutil.which("swiftc"):                                    # the Mac: Apple's Vision
        tool = os.path.join(tmp, "people")
        open(tool + ".swift", "w").write(SWIFT)
        subprocess.run(["swiftc", "-O", tool + ".swift", "-o", tool], check=True, capture_output=True)
        out = subprocess.run([tool, *files.values()], capture_output=True, text=True).stdout
        for line in out.splitlines():
            path, f, h = line.split("\t")
            vision[path] = int(f) > 0 or int(h) > 0
    else:                                                         # elsewhere: OpenCV's YuNet
        if hashlib.sha256(open(YUNET, "rb").read()).hexdigest() != YUNET_SHA256: sys.exit("the face model is not the one tested")
        import cv2, numpy as np
        from PIL import Image
        det = cv2.FaceDetectorYN.create(YUNET, "", (320, 320), 0.8, 0.3, 5000)
        for p in files.values():
            img = cv2.cvtColor(np.array(Image.open(p).convert("RGB")), cv2.COLOR_RGB2BGR)
            det.setInputSize((img.shape[1], img.shape[0])); _, f = det.detect(img)
            vision[p] = f is not None and len(f) > 0
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
