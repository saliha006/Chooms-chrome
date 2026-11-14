"""Click the pick zone and the two bowls on the top camera, once, at the station (H5).

    python -m ui.click_regions                  # top camera from config/cameras.yaml
    python -m ui.click_regions --cam 0          # any camera index or /dev/v4l/by-id path
    python -m ui.click_regions zone             # redo just one region

For each region click its 4 corners clockwise from top-left. Keys: Backspace undo, R re-grab the frame, Q quit
without saving. Saved into config/scene.yaml in place, keeping its comments.
"""

import argparse
import re
from pathlib import Path

import cv2
import numpy as np
import yaml

from common.capture import OpenCVCamera

CONFIG = Path(__file__).resolve().parents[1] / "config"
REGIONS = ("zone", "bowl_red", "bowl_blue")
CORNERS = ("top-left", "top-right", "bottom-right", "bottom-left")
COLOURS = {"zone": (0, 220, 0), "bowl_red": (40, 40, 230), "bowl_blue": (255, 150, 30)}  # BGR
WINDOW = "Click regions"


class Clicker:
    """Collects 4 corners per region, in order. Kept free of any window so it can be tested."""

    def __init__(self, regions=REGIONS):
        self.regions = list(regions)
        self.points: dict[str, list[tuple[int, int]]] = {name: [] for name in self.regions}

    @property
    def current(self) -> str | None:
        return next((name for name in self.regions if len(self.points[name]) < 4), None)

    def click(self, x: int, y: int) -> None:
        if self.current is not None:
            self.points[self.current].append((int(x), int(y)))

    def undo(self) -> None:
        for name in reversed(self.regions):
            if self.points[name]:
                self.points[name].pop()
                return

    def prompt(self) -> str:
        name = self.current
        return "All done: press Enter to save" if name is None else f"{name}: click {CORNERS[len(self.points[name])]}"

    def draw(self, frame: np.ndarray) -> np.ndarray:
        img = frame.copy()
        for name, pts in self.points.items():
            for p in pts:
                cv2.circle(img, p, 5, COLOURS[name], -1)
            if len(pts) > 1:
                cv2.polylines(img, [np.array(pts, np.int32)], len(pts) == 4, COLOURS[name], 2)
        cv2.putText(img, self.prompt(), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        return img


def grab(camera: OpenCVCamera) -> np.ndarray:
    for _ in range(30):  # the first reads after opening a camera are often empty
        frame = camera.read()
        if frame is not None:
            return frame
    raise RuntimeError("the camera gave no frame")


def save_regions(path: Path, points: dict[str, list[tuple[int, int]]]) -> None:
    text = path.read_text(encoding="utf-8")
    for name, pts in points.items():
        value = "[" + ", ".join(f"[{x}, {y}]" for x, y in pts) + "]"
        text, count = re.subn(rf"^{name}:[^#\n]*", f"{name}: {value}   ", text, count=1, flags=re.M)
        if count == 0:
            text += f"{name}: {value}\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("regions", nargs="*", choices=REGIONS, metavar="region", help=f"default: all of {', '.join(REGIONS)}")
    ap.add_argument("--cam", help="camera index or path (default: the top camera in config/cameras.yaml)")
    ap.add_argument("--file", type=Path, default=CONFIG / "scene.yaml")
    args = ap.parse_args()

    source = args.cam or yaml.safe_load((CONFIG / "cameras.yaml").read_text())["top"]["path"]
    if source is None:
        ap.error("set the top camera path in config/cameras.yaml or pass --cam")
    camera = OpenCVCamera(int(source) if str(source).isdigit() else source)
    clicker = Clicker(args.regions or REGIONS)
    frame = grab(camera)
    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, lambda event, x, y, *_: event == cv2.EVENT_LBUTTONDOWN and clicker.click(x, y))
    try:
        while True:
            cv2.imshow(WINDOW, clicker.draw(frame))
            key = cv2.waitKey(30) & 0xFF
            if key == ord("q"):
                print("Quit without saving.")
                return
            if key == 8:  # Backspace
                clicker.undo()
            elif key == ord("r"):
                frame = grab(camera)
            elif key == 13 and clicker.current is None:  # Enter
                save_regions(args.file, clicker.points)
                print(f"Saved {', '.join(clicker.points)} to {args.file}")
                return
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
