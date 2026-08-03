import shutil

import pytest

from runner_lib import constants, io, orchestrator, run_full


def test_run_full_main_success(tmp_path, posterior_dir):
    shutil.copy(
        posterior_dir / "posterior_setup_normal.binpb",
        tmp_path / "posterior_setup_normal.binpb",
    )
    rc = run_full.main(
        [
            "--setup-name",
            "setup_normal",
            "--output-dir",
            str(tmp_path),
            "--cost-rate",
            "0.0",
        ]
    )
    assert rc == constants.EXIT_OK
    assert io.full_binpb_path(tmp_path, "setup_normal").exists()
    assert io.geo_json_path(tmp_path, "setup_normal").exists()  # fixtureはgeoモデル
    # 最適化成果物も同時に生成される
    opt_dir = tmp_path / "setup_normal" / constants.OPTIMIZATION_DIRNAME
    assert (opt_dir / "setup_normal_budget_scenarios.csv").exists()
    assert (opt_dir / "setup_normal_optimization_summary.html").exists()
    # summary/ も生成される(waterfall は Phase 2 未実行のため missing でよい)
    summary_dir = tmp_path / "summary"
    assert (summary_dir / "setup_normal_geo_roi.png").exists()  # fixture は geo モデル
    assert (summary_dir / "setup_normal_budget_allocation.png").exists()


def test_run_full_main_missing_posterior(tmp_path):
    rc = run_full.main(["--setup-name", "nope", "--output-dir", str(tmp_path)])
    assert rc == constants.EXIT_FAILURE


def test_run_full_generation_parses_targets(tmp_path, posterior_dir):
    shutil.copy(
        posterior_dir / "posterior_setup_normal.binpb",
        tmp_path / "posterior_setup_normal.binpb",
    )
    df = orchestrator.run_full_generation("setup_normal, ghost", tmp_path, cost_rate=0.0)
    results = dict(zip(df["setup"], df["result"]))
    assert results["setup_normal"] == "success"
    assert results["ghost"] == "not_found"
    assert io.full_binpb_path(tmp_path, "setup_normal").exists()
    # 最適化成果物の有無が結果テーブルで可視化される
    opt_status = dict(zip(df["setup"], df["optimization"]))
    assert opt_status["setup_normal"] == "saved"
    assert opt_status["ghost"] == "-"


def test_run_full_main_rejects_invalid_cost_rate(tmp_path, posterior_dir, capsys):
    shutil.copy(
        posterior_dir / "posterior_setup_normal.binpb",
        tmp_path / "posterior_setup_normal.binpb",
    )
    for cost_rate_value in ["1.0", "30"]:
        rc = run_full.main(
            [
                "--setup-name",
                "setup_normal",
                "--output-dir",
                str(tmp_path),
                "--cost-rate",
                cost_rate_value,
            ]
        )
        assert rc == constants.EXIT_FAILURE
        captured = capsys.readouterr()
        assert "cost_rate は 0 以上 1 未満" in captured.err
        assert "Traceback" not in captured.err


def test_run_full_generation_rejects_invalid_cost_rate(tmp_path):
    for cost_rate_value in [1.0, 1.5, 30]:
        with pytest.raises(ValueError):
            orchestrator.run_full_generation("all", tmp_path, cost_rate=cost_rate_value)
