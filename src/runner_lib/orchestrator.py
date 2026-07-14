"""ノートブックから呼ぶ高レベル関数(一括実行・進捗表示)."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from runner_lib import constants, io

_STATUS_LABELS = {"pending": "⏳ 未実行", "done": "✅ 完了", "eda_error": "🚫 EDAエラー"}


def setup_table(input_dir: str | Path, output_dir: str | Path) -> pd.DataFrame:
    if not Path(input_dir).is_dir():
        raise FileNotFoundError(f"INPUT_DIR が存在しません: {input_dir}")
    rows = [
        {"setup": s.name, "status": _STATUS_LABELS[s.status]}
        for s in io.list_setups(input_dir, output_dir)
    ]
    return pd.DataFrame(rows, columns=["setup", "status"])


def _print_stderr_tail(stderr: str, n_chars: int = 500) -> None:
    if stderr:
        print(stderr[-n_chars:], flush=True)


def run_all_mcmc(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    n_chains: int = 3,
    n_adapt: int = 500,
    n_burnin: int = 750,
    n_keep: int = 1000,
    seed: int | None = None,
    eda_draws: int = 500,
    python_executable: str | None = None,
) -> pd.DataFrame:
    if not Path(input_dir).is_dir():
        raise FileNotFoundError(f"INPUT_DIR が存在しません: {input_dir}")
    py = python_executable or sys.executable
    setups = io.list_setups(input_dir, output_dir)
    print(f"対象: {len(setups)}件")
    rows = []
    for s in setups:
        t0 = time.time()
        if s.status == "done":
            print(f"⏭ skip(完了済): {s.name}")
            rows.append({"setup": s.name, "result": "skipped_exists", "elapsed_sec": 0.0})
            continue

        print(f"\n🚀 start: {s.name}")
        cmd = [
            py,
            "-m",
            "runner_lib.run_mcmc",
            "--input",
            str(s.input_path),
            "--output-dir",
            str(output_dir),
            "--setup-name",
            s.name,
            "--n-chains",
            str(n_chains),
            "--n-adapt",
            str(n_adapt),
            "--n-burnin",
            str(n_burnin),
            "--n-keep",
            str(n_keep),
            "--eda-draws",
            str(eda_draws),
        ]
        if seed is not None:
            cmd += ["--seed", str(seed)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout.strip())

        if proc.returncode == constants.EXIT_OK:
            result = "success"
            print(f"✅ 完了: {s.name}")
        elif proc.returncode == constants.EXIT_EDA_ERROR:
            result = "eda_error"
            print(f"🚫 EDAエラーによりスキップ: {s.name}(詳細: eda/{s.name}_eda.html)")
        else:
            result = "failed"
            print(f"❌ 失敗: {s.name} (returncode={proc.returncode})")
            _print_stderr_tail(proc.stderr)
        rows.append({"setup": s.name, "result": result, "elapsed_sec": round(time.time() - t0, 1)})

    df = pd.DataFrame(rows, columns=["setup", "result", "elapsed_sec"])
    counts = df["result"].value_counts().to_dict()
    print(f"\n🏁 全セットアップ処理完了: {counts}")
    return df


def _parse_targets(target_setups: str, output_dir: str | Path) -> list[str]:
    if target_setups.strip().lower() == "all":
        prefix = constants.POSTERIOR_PREFIX
        return sorted(p.stem[len(prefix) :] for p in Path(output_dir).glob(f"{prefix}*.binpb"))
    return [t.strip() for t in target_setups.split(",") if t.strip()]


def run_full_generation(
    target_setups: str,
    output_dir: str | Path,
    *,
    cost_rate: float = 0.0,
    python_executable: str | None = None,
) -> pd.DataFrame:
    if not 0.0 <= cost_rate < 1.0:
        raise ValueError(
            f"エラー: cost_rate は 0 以上 1 未満で指定してください(例: 30% なら 0.3)。"
            f" 指定値: {cost_rate}"
        )
    py = python_executable or sys.executable
    targets = _parse_targets(target_setups, output_dir)
    print(f"完全版生成 対象: {len(targets)}件 (cost_rate={cost_rate})")
    rows = []
    for name in targets:
        t0 = time.time()
        if not io.posterior_path(output_dir, name).exists():
            print(f"❌ posterior が見つかりません: {name}")
            rows.append({"setup": name, "result": "not_found", "elapsed_sec": 0.0})
            continue
        print(f"\n🚀 start: {name}")
        proc = subprocess.run(
            [
                py,
                "-m",
                "runner_lib.run_full",
                "--setup-name",
                name,
                "--output-dir",
                str(output_dir),
                "--cost-rate",
                str(cost_rate),
            ],
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.returncode == constants.EXIT_OK:
            result = "success"
            print(f"✅ 完了: full/{name}_full.binpb")
        else:
            result = "failed"
            print(f"❌ 失敗: {name} (returncode={proc.returncode})")
            _print_stderr_tail(proc.stderr)
        rows.append({"setup": name, "result": result, "elapsed_sec": round(time.time() - t0, 1)})
    df = pd.DataFrame(rows, columns=["setup", "result", "elapsed_sec"])
    print(f"\n🏁 完全版生成完了: {df['result'].value_counts().to_dict()}")
    return df
