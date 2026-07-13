"""meridian 1.7 EDA の実行と ERROR ゲート判定."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable
from pathlib import Path

from meridian.model import model
from meridian.model.eda import eda_outcome, meridian_eda

from runner_lib import io

# critical 以外で収集する check outcome のプロパティ名
_EXTRA_OUTCOME_PROPS = (
    "geo_cost_per_media_unit_check_outcome",
    "national_cost_per_media_unit_check_outcome",
    "geo_pairwise_correlation_check_outcome",
    "national_pairwise_correlation_check_outcome",
    "geo_stdev_check_outcome",
    "national_stdev_check_outcome",
)


@dataclasses.dataclass
class FindingRecord:
    check_type: str
    severity: str  # "INFO" | "ATTENTION" | "ERROR"
    cause: str
    explanation: str


@dataclasses.dataclass
class EDAResult:
    setup_name: str
    findings: list[FindingRecord]
    severity_counts: dict[str, int]
    has_error: bool


def has_error_findings(findings: Iterable[FindingRecord]) -> bool:
    return any(f.severity == eda_outcome.EDASeverity.ERROR.name for f in findings)


def _collect_outcomes(eda: meridian_eda.MeridianEDA) -> list:
    crit = eda.critical_outcomes
    outcomes = [crit.kpi_invariability, crit.multicollinearity, crit.pairwise_correlation]
    for prop in _EXTRA_OUTCOME_PROPS:
        try:
            outcomes.append(getattr(eda, prop))
        except Exception as e:  # national専用モデル等で一部チェックが成立しない場合
            print(f"  (EDA check {prop} unavailable: {type(e).__name__})")
    return [o for o in outcomes if o is not None]


def run_eda(
    mmm: model.Meridian,
    setup_name: str,
    n_draws_prior: int = 500,
    seed: int = 0,
) -> tuple[meridian_eda.MeridianEDA, EDAResult]:
    eda = meridian_eda.MeridianEDA(mmm, n_draws_prior=n_draws_prior, seed=seed)
    findings = [
        FindingRecord(
            check_type=o.check_type.name,
            severity=f.severity.name,
            cause=f.finding_cause.name,
            explanation=f.explanation,
        )
        for o in _collect_outcomes(eda)
        for f in o.findings
    ]
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return eda, EDAResult(
        setup_name=setup_name,
        findings=findings,
        severity_counts=counts,
        has_error=has_error_findings(findings),
    )


def save_eda_artifacts(
    eda: meridian_eda.MeridianEDA,
    result: EDAResult,
    output_dir: str | Path,
) -> tuple[Path, Path]:
    json_path = io.eda_json_path(output_dir, result.setup_name)
    html_path = io.eda_html_path(output_dir, result.setup_name)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "setup": result.setup_name,
        "has_error": result.has_error,
        "severity_counts": result.severity_counts,
        "findings": [dataclasses.asdict(f) for f in result.findings],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    eda.generate_and_save_report(html_path.name, str(html_path.parent))
    return json_path, html_path
