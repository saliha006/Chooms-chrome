"""The deployed PatchCore IR on the saved real-brick photos, through Inspector (run from the main checkout,
where the git-ignored data/ and runs/ live; skipped elsewhere)."""

from pathlib import Path

import pytest

from bench.real_photos import DATA, THRESHOLDS, XML, score_photos

ROOT = Path(__file__).resolve().parents[2]

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(not (ROOT / XML).exists() or not (ROOT / DATA / "defective").is_dir(),
                                 reason="needs the deployed IR and the real photos")]


def test_good_photos_below_t_high_and_defective_above_t_low():
    rows = score_photos(ROOT / DATA, ROOT / XML, ROOT / THRESHOLDS)
    good = [r for r in rows if r["truth"] == "good"]
    defective = [r for r in rows if r["truth"] == "defective"]
    assert good and defective
    assert all(r["score"] < r["t_high"] for r in good)
    assert all(r["score"] > r["t_low"] for r in defective)
