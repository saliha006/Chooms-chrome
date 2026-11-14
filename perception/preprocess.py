"""Move the colour flip, scaling and layout change into the OpenVINO graph (Intel slide: pre/post-processing).

The exported graph then takes the resized camera frame as it is: 1x256x256x3 uint8, BGR. Resizing stays
on the CPU with INTER_AREA: OpenVINO's resize modes differ, and a different resize would shift the scores
that t_low and t_high were measured with. The static shape is kept for the NPU (decisions.md D8).
"""

from pathlib import Path

import openvino as ov
from openvino.preprocess import ColorFormat, PrePostProcessor

PPP_SUFFIX = "_ppp"


def with_preprocessing(xml: Path) -> Path:
    """Write <name>_ppp.xml beside `xml` and return it; the original IR is left as it is."""
    model = ov.Core().read_model(xml)
    side = model.inputs[0].get_shape()[2:]
    ppp = PrePostProcessor(model)
    tensor = ppp.input(0).tensor()
    tensor.set_element_type(ov.Type.u8).set_layout(ov.Layout("NHWC")).set_color_format(ColorFormat.BGR)
    tensor.set_shape([1, *side, 3])
    ppp.input(0).model().set_layout(ov.Layout("NCHW"))
    ppp.input(0).preprocess().convert_element_type(ov.Type.f32).convert_color(ColorFormat.RGB).scale(255.0)
    out = xml.with_name(f"{xml.stem}{PPP_SUFFIX}.xml")
    ov.save_model(ppp.build(), out, compress_to_fp16=False)  # already FP16 or INT8: do not re-compress
    return out
