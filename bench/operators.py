"""Which operators each device can run (Intel slide: device placement "by operator support").

OpenVINO's query_model lists the operations a plugin can take; the ones it leaves out are what would
fall back to another device or stop the compile. Counted by operator type so the table stays short.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import openvino as ov


@dataclass(frozen=True)
class Support:
    total: int
    unsupported: dict[str, int]  # operator type -> how many

    @property
    def supported(self) -> int:
        return self.total - sum(self.unsupported.values())


def op_support(xml: Path, device: str) -> Support:
    core = ov.Core()
    model = core.read_model(xml)
    runnable = core.query_model(model, device)
    ops = [op for op in model.get_ops() if op.get_type_name() not in ("Parameter", "Result")]
    missing = Counter(op.get_type_name() for op in ops if op.get_friendly_name() not in runnable)
    return Support(len(ops), dict(missing))


def to_markdown(rows: list[tuple[str, str, Support]]) -> str:
    lines = ["| model | device | operators | runnable | not supported (type x count) |", "|---|---|---|---|---|"]
    for model, device, s in rows:
        gaps = ", ".join(f"{t} x{n}" for t, n in sorted(s.unsupported.items())) or "none"
        lines.append(f"| {model} | {device} | {s.total} | {s.supported} | {gaps} |")
    return "\n".join(lines)
