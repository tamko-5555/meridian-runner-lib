"""サブプロセス CLI: 1 setup binpb を EDA ゲート付きで MCMC 実行して保存.

exit code: 0=成功 / 2=失敗 / 3=EDA ERROR スキップ(constants 参照)
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime

from runner_lib import constants, eda, io, sampling


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="runner_lib.run_mcmc")
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--setup-name", required=True)
    p.add_argument("--n-chains", type=int, required=True)
    p.add_argument("--n-adapt", type=int, required=True)
    p.add_argument("--n-burnin", type=int, required=True)
    p.add_argument("--n-keep", type=int, required=True)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--eda-draws", type=int, default=500)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        _log(f"load: {args.input}")
        mmm = io.load_meridian_flexible(args.input)

        _log(f"EDA: n_draws_prior={args.eda_draws}")
        eda_obj, result = eda.run_eda(
            mmm, args.setup_name, n_draws_prior=args.eda_draws, seed=args.seed or 0
        )
        eda.save_eda_artifacts(eda_obj, result, args.output_dir)
        _log(f"EDA findings: {result.severity_counts}")

        if result.has_error:
            errors = [f for f in result.findings if f.severity == "ERROR"]
            for f in errors:
                _log(f"EDA ERROR [{f.check_type}] {f.explanation}")
            _log("skip MCMC due to EDA ERROR")
            return constants.EXIT_EDA_ERROR

        config = sampling.McmcConfig(
            n_chains=args.n_chains,
            n_adapt=args.n_adapt,
            n_burnin=args.n_burnin,
            n_keep=args.n_keep,
            seed=args.seed,
        )
        _log(f"sample_posterior: {config}")
        sampling.fit(mmm, config)

        out = io.save_posterior(mmm, args.output_dir, args.setup_name)
        _log(f"saved: {out.name}")
        return constants.EXIT_OK
    except Exception:
        traceback.print_exc()
        return constants.EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
