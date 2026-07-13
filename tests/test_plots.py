from runner_lib import plots


def test_safe_filename():
    assert plots.safe_filename("ab/c d:e") == "ab_c_d_e"


def test_save_all_for_dir_creates_chart_files(posterior_dir):
    plots.save_all_for_dir(posterior_dir, use_kpi=True)
    checks_dir = posterior_dir / "checks"
    files = {p.name for p in checks_dir.iterdir()}
    # 主要チャートの存在をスモーク確認(HTML は必ず出る)
    assert any("model_fit" in f for f in files)
    assert any("roi_bar" in f for f in files)
    assert any("contribution_waterfall" in f for f in files)
    assert any("adstock_decay" in f for f in files)
    assert any(f.endswith("_media_summary_table.csv") for f in files)
    assert any("trace_beta_m" in f and f.endswith(".png") for f in files)
