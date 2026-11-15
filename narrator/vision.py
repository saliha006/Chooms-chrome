"""What Pix sees: name the object in front of a camera, locally, so "Hey Pix, what do you see now?" has an answer.

    python -m narrator.vision build                      # once: download CLIP, convert to OpenVINO, embed the names
    python -m narrator.vision check --cam wrist          # live: what it thinks each frame shows (or --image f.jpg)
    python -m narrator.vision capture brick --cam wrist  # ~20 photos of one object into data/objects/brick/
    python -m narrator.vision train                      # train the classifier on data/objects/ (seconds)

CLIP turns an image into a 512-number embedding that sits close to the embedding of a sentence describing it. Our
own objects (brick, plate, the two bowls) are the "regular" ones; anything else is "unknown", with a best guess from
a list of everyday things ("it looks like a mug"). With no photos it matches names (zero-shot); once `train` has run
on our own photos it uses the classifier trained here on the Intel laptop instead (Harry, 2026-11-15).
Only the image encoder runs at demo time (OpenVINO, GPU then CPU); the names are embedded once by `build`.
"""

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

_log = logging.getLogger("narrator.vision")

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "runs" / "vision"  # git-ignored: the converted model and the trained classifier
PHOTOS = ROOT / "data" / "objects"  # git-ignored: our own photos, one folder per object
CLIP = "openai/clip-vit-base-patch32"
SIDE = 224
MEAN = np.array([0.48145466, 0.4578275, 0.40821073], np.float32)  # CLIP's own normalisation
STD = np.array([0.26862954, 0.26130258, 0.27577711], np.float32)

KNOWN = {"brick": "a toy building brick", "plate": "a white plate", "purple bowl": "a purple bowl",
         "orange bowl": "an orange bowl"}
OTHER = ("mug", "cup", "hand", "person", "phone", "cowboy hat", "bottle", "pen", "pair of scissors", "roll of tape",
         "set of keys", "laptop", "sheet of paper", "cable", "pair of glasses", "apple", "banana", "toy car", "box")
KNOWN_MIN = 0.5  # TUNE: the best regular object must take more than this share, or it counts as unknown
PROBE_MIN = 0.6  # TUNE: the same for the trained classifier


@dataclass(frozen=True)
class Sight:
    name: str  # a regular object's name, or "unknown"
    confidence: float
    guess: str | None = None  # for "unknown": the closest everyday thing


def preprocess(bgr: np.ndarray) -> np.ndarray:
    """CLIP's input: shortest side to 224, centre crop, RGB, normalised, 1x3x224x224."""
    h, w = bgr.shape[:2]
    scale = SIDE / min(h, w)
    img = cv2.resize(bgr, (max(SIDE, round(w * scale)), max(SIDE, round(h * scale))), interpolation=cv2.INTER_AREA)
    y, x = (img.shape[0] - SIDE) // 2, (img.shape[1] - SIDE) // 2
    rgb = img[y:y + SIDE, x:x + SIDE, ::-1].astype(np.float32) / 255.0
    return ((rgb - MEAN) / STD).transpose(2, 0, 1)[None]


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def zero_shot(embedding: np.ndarray, names: list[str], text: np.ndarray) -> Sight:
    """Match against every name; a regular object only counts if it clearly wins."""
    probs = _softmax(100.0 * _unit(embedding) @ text.T)  # CLIP's logit scale
    best = int(probs.argmax())
    if names[best] in KNOWN and probs[best] > KNOWN_MIN:  # a tie between two objects is not a clear win
        return Sight(names[best], float(probs[best]))
    others = [i for i, n in enumerate(names) if n not in KNOWN]
    guess = max(others, key=lambda i: probs[i])
    return Sight("unknown", float(1 - sum(probs[i] for i, n in enumerate(names) if n in KNOWN)), names[guess])


def classify(embedding: np.ndarray, probe: dict, names: list[str], text: np.ndarray) -> Sight:
    """The trained classifier; an "unknown" class (if photographed) or low confidence falls back to a guess."""
    probs = _softmax(_unit(embedding) @ probe["w"] + probe["b"])
    best = int(probs.argmax())
    label = str(probe["classes"][best])
    if label != "unknown" and probs[best] >= PROBE_MIN:
        return Sight(label, float(probs[best]))
    return Sight("unknown", float(probs[best]), zero_shot(embedding, names, text).guess)


def train_probe(embeddings: np.ndarray, labels: list[str], steps: int = 500, lr: float = 0.5) -> dict:
    """Softmax regression on the CLIP embeddings: small, fast, and it fits a few dozen photos per object."""
    classes = sorted(set(labels))
    y = np.array([classes.index(label) for label in labels])
    x = _unit(embeddings)
    w = np.zeros((x.shape[1], len(classes)), np.float32)
    b = np.zeros(len(classes), np.float32)
    onehot = np.eye(len(classes), dtype=np.float32)[y]
    for _ in range(steps):
        grad = (_softmax(x @ w * 30.0 + b) - onehot) / len(x)  # 30: cosine scores are small; sharpen them
        w -= lr * 30.0 * x.T @ grad
        b -= lr * grad.sum(axis=0)
    return {"w": w * 30.0, "b": b, "classes": np.array(classes)}


class Recognizer:
    """Loads what `build` (and `train`) wrote; recognise(bgr) -> Sight in tens of milliseconds."""

    def __init__(self, model_dir: Path = MODEL_DIR, devices: tuple[str, ...] = ("GPU", "CPU")):
        import openvino as ov

        core = ov.Core()
        errors = []
        for device in devices:
            if device not in core.available_devices:
                continue
            try:
                self._encode = core.compile_model(model_dir / "clip_image.xml", device)
                self.device = device
                break
            except Exception as exc:  # any compile failure means "try the next device"
                errors.append(f"{device}: {exc}")
        else:
            raise RuntimeError(f"no device could compile the CLIP image encoder: {errors}")
        labels = np.load(model_dir / "labels.npz")
        self.names, self.text = [str(n) for n in labels["names"]], labels["text"]
        probe_path = model_dir / "probe.npz"
        self.probe = dict(np.load(probe_path)) if probe_path.exists() else None

    def embed(self, bgr: np.ndarray) -> np.ndarray:
        return self._encode(preprocess(bgr))[0][0]

    def recognise(self, bgr: np.ndarray) -> Sight:
        e = self.embed(bgr)
        return classify(e, self.probe, self.names, self.text) if self.probe else zero_shot(e, self.names, self.text)


def build(model_dir: Path = MODEL_DIR) -> None:
    import openvino as ov
    import torch
    from transformers import CLIPModel, CLIPTokenizer

    model = CLIPModel.from_pretrained(CLIP).eval().requires_grad_(False)

    class ImageEncoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.clip = model  # a sub-module, so tracing treats its weights as weights, not loose constants

        def forward(self, pixel_values):
            return self.clip.visual_projection(self.clip.vision_model(pixel_values=pixel_values).pooler_output)

    model_dir.mkdir(parents=True, exist_ok=True)
    ov.save_model(ov.convert_model(ImageEncoder(), example_input=torch.zeros(1, 3, SIDE, SIDE)), model_dir / "clip_image.xml")
    names = [*KNOWN, *OTHER]
    prompts = [f"a photo of {KNOWN.get(n, 'a ' + n)}" for n in names]
    tokens = CLIPTokenizer.from_pretrained(CLIP)(prompts, padding=True, return_tensors="pt")
    with torch.no_grad():
        text = model.text_projection(model.text_model(**tokens).pooler_output).numpy()
    np.savez(model_dir / "labels.npz", names=np.array(names), text=_unit(text).astype(np.float32))
    print(f"wrote {model_dir / 'clip_image.xml'} and {len(names)} names")


def photos(folder: Path = PHOTOS) -> list[tuple[Path, str]]:
    return [(p, d.name) for d in sorted(folder.iterdir()) if d.is_dir()
            for p in sorted(d.iterdir()) if p.suffix.lower() in (".jpg", ".jpeg", ".png")]


def train(folder: Path = PHOTOS, model_dir: Path = MODEL_DIR) -> None:
    shots = photos(folder)
    if not shots:
        sys.exit(f"no photos in {folder}: python -m narrator.vision capture <object> --cam wrist")
    rec = Recognizer(model_dir)
    started = time.monotonic()
    x = np.stack([rec.embed(cv2.imread(str(p))) for p, _ in shots])
    labels = [label for _, label in shots]
    held = np.arange(len(shots)) % 5 == 0  # every 5th photo is held out to say how well it does
    probe = train_probe(x[~held], [l for l, h in zip(labels, held) if not h])
    hits = [str(probe["classes"][int(np.argmax(_unit(x[i]) @ probe["w"] + probe["b"]))]) == labels[i]
            for i in np.flatnonzero(held)]
    probe = train_probe(x, labels)  # the final classifier uses every photo
    np.savez(model_dir / "probe.npz", **probe)
    counts = {c: labels.count(c) for c in probe["classes"]}
    print(f"trained on {len(shots)} photos {counts} in {time.monotonic() - started:.1f} s on {rec.device}; "
          f"held-out: {sum(hits)} of {len(hits)} right")


def _camera(cam: str):
    """A camera role from config/cameras.yaml (with its pixel format), or an index for any local camera."""
    from common.capture import OpenCVCamera

    if cam.isdigit():
        return OpenCVCamera(int(cam))
    import yaml

    role = yaml.safe_load((ROOT / "config" / "cameras.yaml").read_text())[cam]
    return OpenCVCamera(role["path"], role.get("fourcc"))


def capture(label: str, cam: str, n: int = 20, every_s: float = 0.5, folder: Path = PHOTOS) -> None:
    out = folder / label
    out.mkdir(parents=True, exist_ok=True)
    camera = _camera(cam)
    print(f"{n} photos of '{label}' in {n * every_s:.0f} s: move the object around a little between shots")
    for _ in range(5):
        camera.read()  # the first frames are dark while the camera settles
    saved = 0
    while saved < n:
        frame = camera.read()
        if frame is not None:
            cv2.imwrite(str(out / f"{label.replace(' ', '_')}-{time.strftime('%H%M%S')}-{saved:02d}.jpg"), frame)
            saved += 1
        time.sleep(every_s)
    camera.release()
    print(f"saved {saved} to {out}")


def check(cam: str | None, image: Path | None) -> None:
    rec = Recognizer()
    print(f"CLIP image encoder on {rec.device}, {'trained classifier' if rec.probe else 'zero-shot names'}")
    if image is not None:
        print(rec.recognise(cv2.imread(str(image))))
        return
    camera = _camera(cam)
    try:
        while True:
            frame = camera.read()
            if frame is not None:
                started = time.perf_counter()
                sight = rec.recognise(frame)
                print(f"{sight.name:12} {sight.confidence:.2f} {sight.guess or '':16} {1000 * (time.perf_counter() - started):.0f} ms")
            time.sleep(0.5)
    except KeyboardInterrupt:
        camera.release()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("train")
    c = sub.add_parser("check")
    c.add_argument("--cam", default="wrist", help="a role in config/cameras.yaml, or a camera index")
    c.add_argument("--image", type=Path)
    p = sub.add_parser("capture")
    p.add_argument("label", help=f"one of {', '.join(KNOWN)}, or 'unknown' for anything else")
    p.add_argument("--cam", default="wrist")
    p.add_argument("-n", type=int, default=20)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.command == "build":
        build()
    elif args.command == "train":
        train()
    elif args.command == "capture":
        capture(args.label, args.cam, args.n)
    else:
        check(args.cam, args.image)


if __name__ == "__main__":
    main()
