"""Mission control (F6): one OpenCV window, readable from 2 m.

The window runs on the main thread and the cell on its own control thread. Keys only set flags that
the control thread acts on, so one thread talks to the motors (decisions.md D21):
S start · P pause/resume · E e-stop · Q finish this brick, home, stop (closes once stopped) · H cowboy hat.
"""

import threading

import cv2
import numpy as np

import narrator
from common import estop

WINDOW = "SortSense mission control"
WIDTH, HEIGHT = 1280, 720
FEED = (20, 90, 840, 580)  # x, y, w, h: leaves the bottom line for the key hints
PANEL_X = 890
BG, TEXT, DIM = (24, 24, 24), (235, 235, 235), (150, 150, 150)
LABEL_COLOURS = {"perfect": (255, 150, 30), "defective": (40, 40, 230), "uncertain": (0, 200, 255)}  # BGR
STATE_COLOURS = {"E-STOP": (0, 0, 255), "STOPPED": (0, 0, 255), "DONE": (80, 200, 80)}
FONT = cv2.FONT_HERSHEY_SIMPLEX
STAGES = ("LOCATE", "PICK", "VERIFY_GRASP", "INSPECT", "DECIDE", "PLACE")


class Control:
    """Runs cell.run() on the control thread once started and keeps its exception for the caller."""

    def __init__(self, cell):
        self.cell = cell
        self.thread: threading.Thread | None = None
        self.error: BaseException | None = None

    def start(self) -> None:
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name="control", daemon=True)
            self.thread.start()

    def _run(self) -> None:
        try:
            self.cell.run()
        except BaseException as exc:  # reported by run(), which owns the exit code
            self.error = exc

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


def handle_key(key: int, control: Control) -> bool:
    """Act on one key press. False means close the window."""
    key = chr(key).lower() if 0 <= key < 256 else ""
    if key == "s":
        control.start()
    elif key == "p":
        paused = control.cell.paused
        if paused.is_set():
            paused.clear()
        else:
            paused.set()
    elif key == "e":
        estop.request()
    elif key == "q":
        if not control.running:
            return False
        control.cell.quit.set()
    elif key == "h":
        narrator.trigger("hat")
    return True


def _text(img, text, org, scale=1.0, colour=TEXT, thickness=2) -> None:
    cv2.putText(img, text, org, FONT, scale, colour, thickness, cv2.LINE_AA)


def _fit(image: np.ndarray, w: int, h: int) -> np.ndarray:
    scale = min(w / image.shape[1], h / image.shape[0])
    return cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))


_heatmaps: dict[str, np.ndarray | None] = {}


def _heatmap(path: str | None) -> np.ndarray | None:
    if path is None:
        return None
    if path not in _heatmaps:
        _heatmaps.clear()  # only the latest brick's heatmap is ever shown
        _heatmaps[path] = cv2.imread(path)
    return _heatmaps[path]


def render(cell, control: Control, feed: np.ndarray | None) -> np.ndarray:
    img = np.full((HEIGHT, WIDTH, 3), BG, np.uint8)

    if control.thread is None:
        banner, colour = "Press S to start", (80, 200, 80)
    elif estop.requested():
        banner, colour = "E-STOP: torque off", (0, 0, 255)
    elif cell.state == "PAUSE_HUMAN" and cell.help_reason is not None:
        banner, colour = f"NEED HELP: {cell.help_reason.value.replace('_', ' ')} (P go on, Q stop)", (0, 140, 255)
    elif cell.state == "HOLD":
        banner, colour = "HOLD: something in the zone", (0, 200, 255)
    elif cell.paused.is_set():
        banner, colour = "PAUSED (P to resume)", (0, 200, 255)
    else:
        banner, colour = cell.state, STATE_COLOURS.get(cell.state, TEXT)
    (w, _), _ = cv2.getTextSize(banner, FONT, 1.6, 3)
    _text(img, banner, (20, 60), min(1.6, 1.6 * (PANEL_X - 40) / w), colour, 3)  # long banners shrink to fit
    _text(img, cell.mode, (PANEL_X, 60), 0.8, DIM)

    x, y, w, h = FEED
    if feed is not None:
        view = _fit(feed, w, h)
        img[y:y + view.shape[0], x:x + view.shape[1]] = view
    else:
        _text(img, "no camera frame", (x + 20, y + 40), 1.0, DIM)

    signal = cell.last_signal
    heat = _heatmap(signal.heatmap_path) if signal else None
    if heat is not None:
        view = _fit(heat, 260, 260)
        img[90:90 + view.shape[0], PANEL_X:PANEL_X + view.shape[1]] = view
    if signal is not None:
        _text(img, signal.label.upper(), (PANEL_X, 400), 1.6, LABEL_COLOURS.get(signal.label, TEXT), 4)
        _text(img, f"score {signal.score:.2f}  ({signal.t_low:.2f} / {signal.t_high:.2f})", (PANEL_X, 440), 0.8)
        _text(img, f"{signal.model} on {signal.device}, {signal.latency_ms:.0f} ms", (PANEL_X, 470), 0.7, DIM)

    _text(img, f"Bricks sorted: {cell.sorted}", (PANEL_X, 525), 1.1)
    for i, stage in enumerate(STAGES):
        y = 560 + i * 26
        _text(img, stage.lower().replace("_", " "), (PANEL_X, y), 0.65, DIM, 1)
        if stage in cell.stage_ms:
            ms = f"{cell.stage_ms[stage]:.0f} ms"
            (w, _), _ = cv2.getTextSize(ms, FONT, 0.65, 1)
            _text(img, ms, (PANEL_X + 300 - w, y), 0.65, DIM, 1)

    _text(img, "S start   P pause   E e-stop   Q quit   H hat", (20, HEIGHT - 10), 0.75, DIM)
    return img


def run(cell, feed_role: str = "inspect") -> BaseException | None:
    """Show the window until Q after the run, then return the control thread's exception, if any."""
    control = Control(cell)
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, WIDTH, HEIGHT)
    feed = None
    try:
        while True:
            try:
                feed = cell.capture.frame(feed_role, timeout_s=0.03)
            except TimeoutError:
                pass  # keep showing the last frame
            cv2.imshow(WINDOW, render(cell, control, feed))
            key = cv2.waitKey(30)
            if key != -1 and not handle_key(key & 0xFF, control):
                break
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                cell.quit.set()  # closed with the mouse: finish this brick, home, then exit below
                break
    except KeyboardInterrupt:
        estop.request()
    finally:
        if control.thread is not None:
            control.thread.join()
        cv2.destroyAllWindows()
    return control.error
