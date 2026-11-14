"""Energy and temperature around a block of work, from Linux sysfs (Intel RAPL + thermal zones).

    with measure() as r:
        run_inference()
    r.joules, r.watts, r.max_c   # None where the counter isn't available (Windows, macOS)

RAPL's energy_uj is root-only on recent kernels; on the Intel laptop run once:
    sudo chmod a+r /sys/class/powercap/intel-rapl:0/energy_uj
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

SYS_CLASS = Path("/sys/class")
RAPL_PACKAGE = "powercap/intel-rapl:0"


@dataclass
class Reading:
    seconds: float = 0.0
    joules: float | None = None
    watts: float | None = None
    max_c: float | None = None


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def max_temp_c(sys_class: Path = SYS_CLASS) -> float | None:
    temps = [t for t in (_read_int(p) for p in sys_class.glob("thermal/thermal_zone*/temp")) if t is not None]
    return max(temps) / 1000 if temps else None


@contextmanager
def measure(sys_class: Path = SYS_CLASS):
    reading = Reading()
    energy = sys_class / RAPL_PACKAGE / "energy_uj"
    start_uj, start_c = _read_int(energy), max_temp_c(sys_class)
    t0 = time.perf_counter()
    try:
        yield reading
    finally:
        reading.seconds = time.perf_counter() - t0
        end_uj, end_c = _read_int(energy), max_temp_c(sys_class)
        if start_uj is not None and end_uj is not None:
            delta = end_uj - start_uj
            if delta < 0:  # the counter wraps at max_energy_range_uj
                delta += _read_int(energy.with_name("max_energy_range_uj")) or 0
            reading.joules = delta / 1e6
            reading.watts = reading.joules / reading.seconds if reading.seconds > 0 else None
        temps = [t for t in (start_c, end_c) if t is not None]
        reading.max_c = max(temps) if temps else None
