from bench.benchmark import Row, to_markdown


def test_markdown_table_has_header_and_na_for_missing_power():
    row = Row("padim/int8", "CPU", 12.345, 15.0, 47.0, 1.5, 0.2, None, None, None, None)
    table = to_markdown([row]).splitlines()
    assert table[0].startswith("| model | device | p50_ms")
    assert table[2] == "| padim/int8 | CPU | 12.35 | 15.00 | 47.00 | 1.50 | 0.20 | n/a | n/a | n/a | n/a |"


def test_label_handles_both_layouts(tmp_path):
    from bench.benchmark import label
    assert label(tmp_path / "padim/int8/weights/openvino/model.xml", tmp_path) == "padim/int8"
    assert label(tmp_path / "act/openvino/act.xml", tmp_path) == "act/openvino"
