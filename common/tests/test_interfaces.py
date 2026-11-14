from dataclasses import fields

from common.interfaces import DefectSignal, Inspector, Mover

PRD_FIELDS = [
    "brick_id", "view", "label", "score", "t_low", "t_high",
    "bbox", "heatmap_path", "model", "device", "latency_ms",
]
PRD_MOVER_METHODS = ["pick_and_present", "place", "reinspect", "gripper_empty", "home", "estop"]


def test_defect_signal_matches_prd_field_order():
    assert [f.name for f in fields(DefectSignal)] == PRD_FIELDS


def test_mover_conformance_is_checkable():
    class FakeMover:
        def pick_and_present(self): return True
        def place(self, instruction): return True
        def reinspect(self, angle_deg): return True
        def gripper_empty(self): return False
        def home(self): pass
        def estop(self): pass

    class MissingEstop:
        def pick_and_present(self): return True

    assert isinstance(FakeMover(), Mover)
    assert not isinstance(MissingEstop(), Mover)
    assert all(hasattr(Mover, m) for m in PRD_MOVER_METHODS)


def test_inspector_conformance_is_checkable():
    class FakeInspector:
        def inspect(self, frame, view, brick_id):
            return DefectSignal(brick_id, view, "perfect", 0.1, 0.5, 0.9, None, None, "padim", "CPU", 1.0)

    assert isinstance(FakeInspector(), Inspector)
