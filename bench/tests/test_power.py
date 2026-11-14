from pathlib import Path

import pytest

from bench import power
from bench.power import max_temp_c, measure

RAPL = "powercap/intel-rapl-0"  # Windows forbids ':' in folder names; the real path is patched in


@pytest.fixture(autouse=True)
def windows_safe_rapl(monkeypatch):
    monkeypatch.setattr(power, "RAPL_PACKAGE", RAPL)


def fake_sysfs(root: Path, energy_uj: int, temps_mc: list[int], max_range: int = 1_000_000) -> Path:
    rapl = root / RAPL
    rapl.mkdir(parents=True)
    (rapl / "energy_uj").write_text(str(energy_uj))
    (rapl / "max_energy_range_uj").write_text(str(max_range))
    for i, t in enumerate(temps_mc):
        zone = root / f"thermal/thermal_zone{i}"
        zone.mkdir(parents=True)
        (zone / "temp").write_text(str(t))
    return root


def test_measures_energy_and_temperature(tmp_path):
    root = fake_sysfs(tmp_path, 1_000_000, [45000, 61500])
    with measure(root) as r:
        (root / RAPL / "energy_uj").write_text("3500000")
    assert r.joules == 2.5
    assert r.watts is not None and r.watts > 0
    assert r.max_c == 61.5


def test_handles_counter_wrap(tmp_path):
    root = fake_sysfs(tmp_path, 900_000, [40000], max_range=1_000_000)
    with measure(root) as r:
        (root / RAPL / "energy_uj").write_text("100000")
    assert r.joules == 0.2


def test_missing_sysfs_gives_none(tmp_path):
    with measure(tmp_path) as r:
        pass
    assert r.joules is None and r.watts is None and r.max_c is None
    assert max_temp_c(tmp_path) is None
