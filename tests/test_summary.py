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
