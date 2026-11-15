"""Capture a folder of square, fixed-crop PNGs from a camera.

    python -m perception.capture --out data/good --brick 3 --n 12 --cam 0
    python -m perception.capture --out data/defective --brick 7 --n 12 --cam /dev/v4l/by-id/... --crop 400,120,480

The same crop must be used for every folder (and on the demo table), or the model learns the crop.
--brick tags every image with the physical brick it shows, so evaluation can hold out whole bricks.
"""

import argparse
import re
import time
from pathlib import Path

import cv2
import numpy as np

SIZE = 256


def square_crop(frame: np.ndarray, box: tuple[int, int, int] | None = None, size: int = SIZE) -> np.ndarray:
    """Crop `box` = (x, y, side), or the centred square when None, then resize to `size`."""
    h, w = frame.shape[:2]
    if box is None:
        side = min(h, w)
        x, y = (w - side) // 2, (h - side) // 2
    else:
        x, y, side = box
        if x < 0 or y < 0 or x + side > w or y + side > h:
            raise ValueError(f"crop {box} does not fit a {w}x{h} frame")
    return cv2.resize(frame[y : y + side, x : x + side], (size, size), interpolation=cv2.INTER_AREA)


def brick_id(path: Path) -> str:
    """The physical brick an image shows: 'b07' for b07_0012.png; an untagged image counts as its own brick."""
    match = re.match(r"(b\d+)_", path.name)
    return match.group(1) if match else path.stem


def open_camera(cam: str, fourcc: str | None = None) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(int(cam) if cam.isdigit() else cam)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open camera {cam}")
    if fourcc:  # the Sonix wrist camera sends no frames in its default YUYV, only in MJPG
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    return cap


def capture(out: Path, n: int, cam: str, box: tuple[int, int, int] | None, interval_s: float, brick: int | None = None,
            fourcc: str | None = None) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    start = len(list(out.glob("*.png")))
    cap = open_camera(cam, fourcc)
    saved = []
    try:
        for _ in range(5):  # first frames are often dark while auto-exposure settles
            cap.read()
        while len(saved) < n:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("camera stopped returning frames")
            index = start + len(saved)
            path = out / (f"b{brick:02d}_{index:04d}.png" if brick is not None else f"{index:04d}.png")
            cv2.imwrite(str(path), square_crop(frame, box))
            saved.append(path)
            time.sleep(interval_s)
    finally:
        cap.release()
    return saved


def parse_box(text: str | None) -> tuple[int, int, int] | None:
    if not text:
        return None
    x, y, side = (int(v) for v in text.split(","))
    return x, y, side


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--cam", default="0", help="camera index or /dev/v4l/by-id path")
    ap.add_argument("--crop", help="x,y,side in pixels; default = centred square")
    ap.add_argument("--interval", type=float, default=0.3, help="seconds between shots (move or swap the object)")
    ap.add_argument("--fourcc", help="e.g. MJPG for the wrist camera")
    ap.add_argument("--brick", type=int, help="physical brick number shown in these images (for brick-level evaluation)")
    args = ap.parse_args()
    saved = capture(args.out, args.n, args.cam, parse_box(args.crop), args.interval, args.brick, args.fourcc)
    print(f"saved {len(saved)} images to {args.out}")


if __name__ == "__main__":
    main()
