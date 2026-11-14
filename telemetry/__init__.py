"""Non-blocking event log (F8): log() only queues; one writer thread appends JSON lines.

The JSONL file is the offline buffer that later syncs to Aiven (A5), so the loop never waits on a network.
"""

import json
import queue
import threading
from pathlib import Path

_rows: queue.Queue = queue.Queue()
_writer: threading.Thread | None = None


def log(**row) -> None:
    # No writer (tests, tools importing the cell) → drop, or the queue grows forever and leaks into the next run.
    if _writer is not None:
        _rows.put(row)


def start(path: Path) -> None:
    global _writer
    _writer = threading.Thread(target=_write_loop, args=(path,), name="telemetry", daemon=True)
    _writer.start()


def stop() -> None:
    """Write everything queued so far, then end the writer."""
    global _writer
    if _writer is None:
        return
    _rows.put(None)
    _writer.join()
    _writer = None


def _write_loop(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        while (row := _rows.get()) is not None:
            f.write(json.dumps(row) + "\n")
            f.flush()  # a crash or e-stop must not lose the trial log
