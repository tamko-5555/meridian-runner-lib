import pytest

from runner_lib import io, orchestrator

TINY = dict(n_chains=2, n_adapt=10, n_burnin=10, n_keep=10, seed=1, eda_draws=10)


def test_setup_table(tmp_path, setup_dir):
    df = orchestrator.setup_table(setup_dir, tmp_path)
    assert list(df.columns) == ["setup", "status"]
    assert set(df["setup"]) == {"setup_normal", "setup_broken"}


def test_setup_table_missing_input_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        orchestrator.setup_table(tmp_path / "missing", tmp_path)


def test_run_all_mcmc_missing_input_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        orchestrator.run_all_mcmc(tmp_path / "missing", tmp_path, **TINY)


def test_run_all_mcmc_mixed_results_and_resume(tmp_path, setup_dir):
    df = orchestrator.run_all_mcmc(setup_dir, tmp_path, **TINY)
    results = dict(zip(df["setup"], df["result"]))
    assert results == {"setup_normal": "success", "setup_broken": "eda_error"}
    assert io.posterior_path(tmp_path, "setup_normal").exists()
    assert not io.posterior_path(tmp_path, "setup_broken").exists()

    # 再実行: normal は skip される(EDAエラーのものは毎回再判定される)
    df2 = orchestrator.run_all_mcmc(setup_dir, tmp_path, **TINY)
    results2 = dict(zip(df2["setup"], df2["result"]))
    assert results2["setup_normal"] == "skipped_exists"
    assert results2["setup_broken"] == "eda_error"
