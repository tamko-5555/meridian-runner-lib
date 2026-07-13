"""サブプロセス CLI: posterior 済み binpb 1 件から完全版成果物を生成.

exit code: 0=成功 / 2=失敗(constants 参照)
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime

from runner_lib import constants, full_binpb, io


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="runner_lib.run_full")
    p.add_argument("--setup-name", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--cost-rate", type=float, default=0.0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        posterior = io.posterior_path(args.output_dir, args.setup_name)
        if not posterior.exists():
            raise FileNotFoundError(f"posterior binpb not found: {posterior}")

        _log(f"load: {posterior.name}")
        mmm = io.load_meridian_flexible(posterior)

        _log(f"generate full artifacts (cost_rate={args.cost_rate})")
        result = full_binpb.generate_full_artifacts(
            mmm, args.setup_name, args.output_dir, cost_rate=args.cost_rate
        )
        _log(f"saved: {result['binpb'].name} ({result['n_specs']} specs)")
        if result["geo_json"] is not None:
            _log(f"saved: {result['geo_json'].name}")
        return constants.EXIT_OK
    except Exception:
        traceback.print_exc()
        return constants.EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
