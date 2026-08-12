from pathlib import Path

import pandas as pd

from runner_lib import dorega_tokens, summary


def _sample_roi_df():
    return pd.DataFrame(
        {
            "geo": ["tokyo", "osaka", "fukuoka"],
            "roi": [1.5, 0.8, 1.0],
            "incremental": [100.0, 50.0, 30.0],
        }
    )


def _find_layer(spec, mark_type):
    for layer in spec["layer"]:
        if layer["mark"]["type"] == mark_type:
            return layer
    raise AssertionError(f"{mark_type} レイヤーが見つかりません")


def _sample_chart():
    return summary._geo_roi_chart(_sample_roi_df(), "setup_normal", "2024-01-01〜2024-12-31")


def test_geo_roi_chart_colors_roi_at_or_above_1_with_series0():
    color = _find_layer(_sample_chart().to_dict(), "bar")["encoding"]["color"]
    assert color["condition"]["test"] == "(datum.roi >= 1)"
    assert color["condition"]["value"] == dorega_tokens.SERIES[0]
    assert color["value"] == dorega_tokens.BASELINE_GRAY


def test_geo_roi_chart_has_dashed_breakeven_rule():
    rule = _find_layer(_sample_chart().to_dict(), "rule")
    assert rule["mark"]["strokeDash"] == [4, 4]
    assert rule["mark"]["color"] == dorega_tokens.MUTED


def test_geo_roi_chart_has_breakeven_annotation_text():
    spec = _sample_chart().to_dict()
    labels = {
        record.get("label")
        for dataset in spec["datasets"].values()
        for record in dataset
        if "label" in record
    }
    assert "ROI=1(投資回収ライン)" in labels


def test_geo_roi_chart_axis_shows_horizontal_grid_only():
    bar = _find_layer(_sample_chart().to_dict(), "bar")
    x_axis = bar["encoding"]["x"]["axis"]
    y_axis = bar["encoding"]["y"]["axis"]
    assert x_axis["grid"] is False
    assert x_axis["domain"] is False
    assert x_axis["ticks"] is False
    assert y_axis["grid"] is True
    assert y_axis["domain"] is False
    assert y_axis["ticks"] is False


def test_geo_roi_chart_title_and_subtitle_style():
    title = _sample_chart().to_dict()["title"]
    assert title["fontSize"] == dorega_tokens.TITLE_FONT_SIZE
    assert title["fontWeight"] == "bold"
    assert title["subtitleFontSize"] == dorega_tokens.SUBTITLE_FONT_SIZE
    assert "2024-01-01〜2024-12-31" in title["subtitle"]
    assert "setup_normal" in title["subtitle"]


def test_summary_module_has_no_hardcoded_hex_colors():
    source = Path(summary.__file__).read_text(encoding="utf-8")
    assert "#d62728" not in source
    assert "#4c78a8" not in source


def test_geo_roi_frame_has_one_row_per_geo(fitted_mmm):
    df = summary.geo_roi_frame(fitted_mmm)
    assert set(df.columns) == {"geo", "roi", "incremental"}
    assert len(df) == fitted_mmm.n_geos
    assert df["geo"].is_unique
    # ROI降順で返す(グラフの並びと揃える)
    assert df["roi"].is_monotonic_decreasing


def test_save_geo_roi_chart_creates_files(fitted_mmm, tmp_path):
    saved = summary.save_geo_roi_chart(fitted_mmm, "setup_normal", tmp_path)
    names = {p.name for p in saved}
    assert "setup_normal_geo_roi.png" in names or "setup_normal_geo_roi.html" in names
    assert all(p.parent == tmp_path / "summary" for p in saved)


def test_build_summary_copies_key_charts(fitted_mmm, tmp_path):
    name = "setup_normal"
    # 複製元を用意(実物と同名のダミーPNG)
    checks = tmp_path / name / "checks"
    opt = tmp_path / name / "optimization"
    checks.mkdir(parents=True)
    opt.mkdir(parents=True)
    (checks / f"{name}_contribution_waterfall.png").write_bytes(b"png1")
    for stem in (
        "budget_allocation",
        "outcome_delta",
        "budget_scenarios",
        "budget_scenarios_chart",
    ):
        (opt / f"{name}_{stem}.png").write_bytes(b"png2")

    result = summary.build_summary(fitted_mmm, name, tmp_path)

    out = tmp_path / "summary"
    copied = {p.name for p in out.iterdir()}
    assert f"{name}_contribution_waterfall.png" in copied
    assert f"{name}_budget_allocation.png" in copied
    assert f"{name}_outcome_delta.png" in copied
    assert f"{name}_budget_scenarios.png" in copied
    assert f"{name}_budget_scenarios_chart.png" in copied
    assert f"{name}_geo_roi.png" in copied  # fixture は geo モデル
    assert result["missing"] == []


def test_build_summary_reports_missing_sources(fitted_mmm, tmp_path, capsys):
    result = summary.build_summary(fitted_mmm, "setup_normal", tmp_path)
    # 複製元がひとつも無い → 全て missing、ただし例外にはしない
    assert len(result["missing"]) == 5
    assert "contribution_waterfall" in " ".join(result["missing"])
    assert "⚠" in capsys.readouterr().out
