"""Synthetic stand-in bricks for Block A scaffolding only.

Draws a Duplo-like brick (body + 2x4 studs) with jittered position, angle and lighting;
defective ones get a dark marker stroke. Real photos replace this on Saturday, and no
number measured on these images is ever reported (decisions.md D5).

    python -m perception.synth --root data --colours red,blue
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

SIZE = 256
COLOURS = {"red": (40, 40, 200), "blue": (190, 90, 30), "yellow": (40, 200, 230), "green": (60, 160, 50)}


def brick(rng: np.random.Generator, colour: tuple[int, int, int], defective: bool) -> np.ndarray:
    img = np.full((SIZE, SIZE, 3), 70, np.uint8)
    img += rng.integers(0, 8, img.shape, dtype=np.uint8)  # sensor noise

    cx, cy = SIZE // 2 + rng.integers(-6, 7), SIZE // 2 + rng.integers(-6, 7)
    angle = rng.uniform(-4, 4)
    body = cv2.boxPoints(((float(cx), float(cy)), (150.0, 80.0), angle)).astype(np.int32)
    cv2.fillPoly(img, [body], colour)

    rot = cv2.getRotationMatrix2D((float(cx), float(cy)), -angle, 1.0)
    stud_colour = tuple(min(255, c + 25) for c in colour)
    for sx in (-52, -17, 17, 52):
        for sy in (-18, 18):
            px, py = rot @ np.array([cx + sx, cy + sy, 1.0])
            cv2.circle(img, (int(px), int(py)), 11, stud_colour, -1)

    if defective:
        start = rng.integers([cx - 60, cy - 30], [cx + 30, cy + 20])
        points = [start + rng.integers(-35, 36, 2) for _ in range(rng.integers(2, 4))]
        stroke = np.array([start, *points], np.int32)
        cv2.polylines(img, [stroke], False, (25, 25, 25), int(rng.integers(3, 7)))

    gain = rng.uniform(0.92, 1.08)
    return np.clip(img.astype(np.float32) * gain, 0, 255).astype(np.uint8)


def generate(root: Path, colours: list[str], n_good: int = 150, n_defective: int = 40, n_val_good: int = 30, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    for folder, n, defective in (("good", n_good, False), ("defective", n_defective, True), ("val_good", n_val_good, False)):
        out = root / folder
        out.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            cv2.imwrite(str(out / f"{i:04d}.png"), brick(rng, COLOURS[colours[i % len(colours)]], defective))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data"))
    ap.add_argument("--colours", default="red", help=f"comma list from {sorted(COLOURS)}")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    generate(args.root, args.colours.split(","), seed=args.seed)
    print(f"synthetic stand-in data in {args.root}/(good, defective, val_good)")


if __name__ == "__main__":
    main()
