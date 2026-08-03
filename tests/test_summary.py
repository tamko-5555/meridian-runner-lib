from runner_lib import summary


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
