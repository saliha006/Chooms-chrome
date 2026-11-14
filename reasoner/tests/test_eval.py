import cv2
import numpy as np

from reasoner.eval import evaluate, load_frames, to_markdown


def manifest(tmp_path):
    cv2.imwrite(str(tmp_path / "a.png"), np.zeros((8, 8, 3), np.uint8))
    (tmp_path / "frames.csv").write_text(
        "image,label,score,t_low,t_high\n"
        "a.png,perfect,0.12,0.20,0.63\n"
        "a.png,defective,0.71,0.20,0.63\n"
        "a.png,defective,0.71,0.20,0.63\n"
        "a.png,uncertain,0.40,0.20,0.63\n")
    return load_frames(tmp_path / "frames.csv")


def test_scores_each_kind_of_answer(tmp_path):
    answers = iter([
        "Clean studs, score 0.12 is under 0.20, purple bowl it is.",   # usable
        "Score 0.95, that's a defect, orange bowl.",                     # invented number
        "Looks fine to me, into the purple bowl.",                       # wrong bowl
        None,                                                            # API failure
    ])

    def ask(crop, signal, persona, timeout_s, system):
        line = next(answers)
        if line is None:
            raise TimeoutError("slow")
        return line, 2000.0

    outcomes = evaluate(manifest(tmp_path), ask=ask, pause_s=0)
    assert [o.usable for o in outcomes] == [True, False, False, False]
    table = to_markdown(outcomes, "current")
    assert "| 4 | 3/4 | 1/4 | 2/4 | 1/4 | 2000 | 2000 |" in table


def test_prompt_revision_reaches_the_call(tmp_path):
    seen = []

    def ask(crop, signal, persona, timeout_s, system):
        seen.append(system)
        return "purple", 1.0

    evaluate(manifest(tmp_path)[:1], system="REVISED", ask=ask, pause_s=0)
    assert seen == ["REVISED"]
