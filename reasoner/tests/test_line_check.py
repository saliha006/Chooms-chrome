import cv2
import numpy as np
import pytest

from reasoner.evaluate import evaluate, load_cases, to_markdown

HEADER = "image,label,score,t_low,t_high,bbox\n"


@pytest.fixture
def folder(tmp_path):
    for name in ("a.png", "b.png", "c.png"):
        cv2.imwrite(str(tmp_path / name), np.zeros((8, 8, 3), np.uint8))
    (tmp_path / "cases.csv").write_text(HEADER + "a.png,perfect,0.12,0.2,0.63,\nb.png,defective,0.7,0.2,0.63,10 20 30 40\nc.png,uncertain,0.4,0.2,0.63,\n", encoding="utf-8")
    return tmp_path


def fake(lines):
    it = iter(lines)

    def ask(crop, signal, persona, timeout_s):
        line = next(it)
        if isinstance(line, Exception):
            raise line
        return line, 1000.0
    return ask


def test_counts_consistent_lines_per_label(folder):
    rows = load_cases(folder / "cases.csv")
    r = evaluate(rows, folder, ask=fake(["purple bowl, 0.12", "orange bowl, 0.7", "taking a second look"]))
    assert (r["n"], r["ok"], r["failed"]) == (3, 3, {})
    assert "3 of 3 (100%" in to_markdown(r)


def test_a_contradiction_is_listed_by_image(folder):
    r = evaluate(load_cases(folder / "cases.csv"), folder, ask=fake(["orange bowl", "orange bowl", "take a look"]))
    assert r["ok"] == 2 and r["inconsistent"] == [("a.png", "orange bowl")]
    assert "Contradicted the verdict: a.png" in to_markdown(r)


def test_a_failed_request_is_never_counted_as_consistent(folder):
    r = evaluate(load_cases(folder / "cases.csv"), folder, ask=fake([TimeoutError(), "orange bowl", "second look"]))
    assert (r["n"], r["ok"]) == (3, 2) and r["failed"] == {"TimeoutError: ": 1}
    assert "Failure: TimeoutError" in to_markdown(r)


def test_a_bad_label_is_rejected(tmp_path):
    (tmp_path / "c.csv").write_text(HEADER + "a.png,fine,0.1,0.2,0.6,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="perfect, defective or uncertain"):
        load_cases(tmp_path / "c.csv")


def test_a_missing_image_stops_the_run(folder):
    (folder / "a.png").unlink()
    with pytest.raises(FileNotFoundError):
        evaluate(load_cases(folder / "cases.csv"), folder, ask=fake([]))


def test_no_cases_gives_a_clear_line():
    assert to_markdown(evaluate([], ".")) == "No cases."
