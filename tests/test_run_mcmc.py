import subprocess
import sys

from runner_lib import constants, io, run_mcmc

TINY_ARGS = [
    "--n-chains",
    "2",
    "--n-adapt",
    "10",
    "--n-burnin",
    "10",
    "--n-keep",
    "10",
    "--seed",
    "1",
    "--eda-draws",
    "10",
]


def test_main_success_creates_posterior_and_eda(tmp_path, setup_dir):
    rc = run_mcmc.main(
        [
            "--input",
            str(setup_dir / "setup_normal.binpb"),
            "--output-dir",
            str(tmp_path),
            "--setup-name",
            "setup_normal",
            *TINY_ARGS,
        ]
    )
    assert rc == constants.EXIT_OK
    assert io.posterior_path(tmp_path, "setup_normal").exists()
    assert io.eda_json_path(tmp_path, "setup_normal").exists()
    assert io.eda_html_path(tmp_path, "setup_normal").exists()


def test_main_eda_error_skips_mcmc(tmp_path, setup_dir):
    rc = run_mcmc.main(
        [
            "--input",
            str(setup_dir / "setup_broken.binpb"),
            "--output-dir",
            str(tmp_path),
            "--setup-name",
            "setup_broken",
            *TINY_ARGS,
        ]
    )
    assert rc == constants.EXIT_EDA_ERROR
    assert not io.posterior_path(tmp_path, "setup_broken").exists()
    assert io.eda_json_path(tmp_path, "setup_broken").exists()  # 理由は記録される


def test_main_missing_input_returns_failure(tmp_path):
    rc = run_mcmc.main(
        [
            "--input",
            str(tmp_path / "nope.binpb"),
            "--output-dir",
            str(tmp_path),
            "--setup-name",
            "nope",
            *TINY_ARGS,
        ]
    )
    assert rc == constants.EXIT_FAILURE


def test_module_invocation_via_subprocess(tmp_path, setup_dir):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "runner_lib.run_mcmc",
            "--input",
            str(setup_dir / "setup_broken.binpb"),
            "--output-dir",
            str(tmp_path),
            "--setup-name",
            "setup_broken",
            *TINY_ARGS,
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == constants.EXIT_EDA_ERROR
