import numpy as np
import pytest

from runner_lib import constants, optimization, specs


def test_sweep_ratios_match_binpb_specs():
    """スイープ倍率は binpb 内の固定予算シナリオ + 現行(1.0)と一致する契約."""
    assert set(optimization.SWEEP_RATIOS) == {*specs.FIXED_BUDGET_RATIOS, 1.0}
    assert list(optimization.SWEEP_RATIOS) == sorted(optimization.SWEEP_RATIOS)


@pytest.fixture(scope="module")
def opt_artifacts(fitted_mmm, tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("opt_out")
    result = optimization.save_optimization_artifacts(
        fitted_mmm, "setup_normal", out_dir, cost_rate=0.2
    )
    return out_dir, result


def test_save_optimization_artifacts_files(opt_artifacts):
    out_dir, result = opt_artifacts
    opt_dir = out_dir / "setup_normal" / constants.OPTIMIZATION_DIRNAME
    files = {p.name for p in opt_dir.iterdir()}
    for stem in (
        "setup_normal_budget_allocation",
        "setup_normal_spend_delta",
        "setup_normal_outcome_delta",
        "setup_normal_response_curves",
        "setup_normal_budget_scenarios_chart",
    ):
        assert f"{stem}.html" in files, f"missing {stem}.html"
    assert "setup_normal_optimization_summary.html" in files
    assert "setup_normal_optimized_allocation.csv" in files
    assert "setup_normal_budget_scenarios.csv" in files
    assert "setup_normal_budget_scenarios.png" in files
    assert result["dir"] == opt_dir
    assert len(result["files"]) >= 8


def test_budget_sweep_table_contract(opt_artifacts):
    _, result = opt_artifacts
    sweep = result["sweep"]
    # 固定予算6シナリオ + 目標mROIの推奨総予算1行
    assert len(sweep) == len(optimization.SWEEP_RATIOS) + 1
    assert (sweep["種別"] == "目標mROI").sum() == 1
    # 総予算の昇順に並び、現行行の追加予算は0
    budgets = sweep["総予算"].to_numpy()
    assert np.all(np.diff(budgets) >= 0)
    base_row = sweep[sweep["シナリオ"] == "現行予算(100%)"].iloc[0]
    assert base_row["現行比の追加予算"] == 0
    assert base_row["現行比の追加リターン"] == 0
    # 限界ROI は先頭行以外で計算される
    assert sweep["限界ROI(1つ下の予算比)"].iloc[1:].notna().all()


def test_display_saved_smoke(opt_artifacts):
    out_dir, _ = opt_artifacts
    optimization.display_saved(out_dir)  # 例外なく表示できる(IPython 有無どちらでも)
    optimization.display_saved(out_dir, "setup_normal")


def test_display_saved_reports_missing(tmp_path, capsys):
    optimization.display_saved(tmp_path)
    out = capsys.readouterr().out
    assert "見つかりません" in out
    assert "Phase 3" in out
