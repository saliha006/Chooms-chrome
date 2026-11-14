"""ACT-on-NPU compile probe: our ACT shape (3 cameras 480x640, 6 joints), random weights, exported by Studio.

Weights don't change whether the graph compiles, so this answers 'does ACT run on the NPU' before Nate's IR lands.
Usage: .venv-robot/bin/python bench/act_npu_probe.py runs/act_probe   (needs Studio's library, so the robot environment)
"""

import sys
import time
from pathlib import Path

import numpy as np
import openvino as ov
from physicalai.policies import ACT

out = Path(sys.argv[1])
stats = {
    "observation.state": {"name": "observation.state", "type": "STATE", "shape": (6,), "mean": [0.0] * 6, "std": [1.0] * 6},
    "action": {"name": "action", "type": "ACTION", "shape": (6,), "mean": [0.0] * 6, "std": [1.0] * 6},
}
for cam in ("top", "inspect", "wrist"):
    key = f"observation.images.{cam}"
    stats[key] = {"name": key, "type": "VISUAL", "shape": (3, 480, 640), "mean": [0.0] * 3, "std": [1.0] * 3}

policy = ACT(pretrained_backbone_weights=None, dataset_stats=stats)
policy.eval()
t = time.perf_counter()
policy.export(str(out), backend="openvino")
print(f"exported in {time.perf_counter() - t:.1f} s")
for xml in sorted(out.rglob("*.xml")):
    core = ov.Core()
    model = core.read_model(xml)
    print(xml.relative_to(out), [(i.get_any_name(), str(i.get_partial_shape())) for i in model.inputs])
    for device in core.available_devices:
        try:
            t = time.perf_counter()
            compiled = core.compile_model(model, device)
            compile_s = time.perf_counter() - t
            req = compiled.create_infer_request()
            feeds = {p.get_any_name(): np.random.rand(*p.shape).astype(p.get_element_type().to_dtype()) for p in compiled.inputs}
            req.infer(feeds)
            times = []
            for _ in range(30):
                t = time.perf_counter()
                req.infer(feeds)
                times.append((time.perf_counter() - t) * 1000)
            print(f"  {device}: compiled {compile_s:.1f} s, p50 {np.median(times):.1f} ms over 30 runs")
        except Exception as exc:
            print(f"  {device}: FAILED {str(exc).splitlines()[0][:300]}")
