"""モデルヘルスチェック(meridian 1.7 ModelReviewer)成果物の保存.

health_score だけでなく、公式の Model Health Card HTML と、
チェック別の判定・推奨アクションの表(CSV+表画像)を <setup>/checks/health/ に保存する。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from meridian.analysis.review import results as review_results
from meridian.analysis.review import reviewer
from meridian.model import model

from runner_lib import checks, io, plots, tables

# ModelReviewer.run()(meridian 1.7.0)が実際に実行するチェックのみ列挙する。
# ImplausibleROI / HighVariance / PotentialBias はクラスとして存在するが
# run() の実行バッテリーに含まれていないため、表示対象にしない。
CHECK_LABELS_JA = {
    "ConvergenceCheckResult": "収束(R-hat)",
    "GoodnessOfFitCheckResult": "適合度(R²/MAPE)",
    "BayesianPPPCheckResult": "事後予測チェック(PPP)",
    "BaselineCheckResult": "ベースライン妥当性",
    "PriorPosteriorShiftCheckResult": "事前→事後の分布シフト",
    "ROIConsistencyCheckResult": "ROIの整合性(事前分布比)",
}
SKIPPED_MARK = "—(未実施)"
NOT_CONVERGED_MARK = "—(未収束のためスキップ)"
# ModelReviewer.run() の条件付きスキップ(モデル構成上そもそも対象外のケース)
NOT_APPLICABLE_MARKS = {
    "PriorPosteriorShiftCheckResult": "—(対象外: ROI事前分布を使用していない)",
    "ROIConsistencyCheckResult": "—(対象外: カスタムROI事前分布が未設定)",
}


def run_review(mmm: model.Meridian) -> review_results.ReviewSummary:
    return reviewer.ModelReviewer(
        model_context=mmm.model_context, inference_data=mmm.inference_data
    ).run()


def _is_not_converged(summary: review_results.ReviewSummary) -> bool:
    for r in summary.results:
        if isinstance(r, review_results.ConvergenceCheckResult):
            return r.case is review_results.ConvergenceCases.NOT_CONVERGED
    return False


def _absent_mark(cls_name: str, summary: review_results.ReviewSummary) -> str:
    """results に現れなかったチェックの理由つきマークを返す.

    meridian の ModelReviewer.run() は、(1) 未収束なら収束以外を全てスキップ、
    (2) ROI事前分布の使い方によっては 事前→事後シフト / ROI整合性 を対象外にする。
    """
    if _is_not_converged(summary):
        return NOT_CONVERGED_MARK
    return NOT_APPLICABLE_MARKS.get(cls_name, SKIPPED_MARK)


def health_detail_table(summary: review_results.ReviewSummary) -> pd.DataFrame:
    """1モデル分のチェック別詳細表(先頭行は総合判定)."""
    by_name = {type(r).__name__: r for r in summary.results}
    rows = [
        {
            "チェック": "総合判定",
            "判定": f"{summary.overall_status.name}(スコア {summary.health_score:.1f})",
            "推奨アクション": summary.summary_message,
            "詳細": "",
        }
    ]
    for cls_name, label in CHECK_LABELS_JA.items():
        r = by_name.get(cls_name)
        if r is None:
            rows.append(
                {
                    "チェック": label,
                    "判定": _absent_mark(cls_name, summary),
                    "推奨アクション": "",
                    "詳細": "",
                }
            )
            continue
        rows.append(
            {
                "チェック": label,
                "判定": str(summary.checks_status.get(cls_name, "")),
                "推奨アクション": str(getattr(r, "recommendation", "") or ""),
                "詳細": str(getattr(r, "details", "") or ""),
            }
        )
    return pd.DataFrame(rows)


def _health_dir(output_dir: str | Path, setup_name: str) -> Path:
    d = io.health_dir(output_dir, setup_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_health_artifacts(output_dir: str | Path) -> pd.DataFrame:
    """全 posterior モデルのヘルスチェック成果物を保存し、比較マトリクスを返す.

    保存先:
      - <setup>/checks/health/<setup>_model_health_card.html : meridian 公式ヘルスカード
      - <setup>/checks/health/<setup>_health_checks.csv/.png : チェック別の判定・推奨アクション
      - _all/health_checks_matrix.csv/.png : セットアップ × チェックの判定一覧
    """
    matrix_rows = []
    for name, mmm in checks._iter_posteriors(output_dir):
        safe = plots.safe_filename(name)
        out = _health_dir(output_dir, name)
        try:
            summary = run_review(mmm)
        except Exception as e:
            print(f"❌ {name} のヘルスチェックに失敗: {type(e).__name__}: {e}")
            matrix_rows.append({"setup": name, "総合判定": f"error: {type(e).__name__}"})
            continue

        try:
            summary.output_model_health_card(f"{safe}_model_health_card.html", str(out))
            print(f"  ✔ {safe}_model_health_card.html")
        except Exception as e:
            print(f"  ⚠ {name} のヘルスカードHTML保存をスキップ: {type(e).__name__}: {e}")

        tables.save_table_csv_and_image(
            health_detail_table(summary),
            out / f"{safe}_health_checks",
            title=f"モデルヘルスチェック詳細: {name}",
        )

        row = {
            "setup": name,
            "総合判定": summary.overall_status.name,
            "ヘルススコア": round(float(summary.health_score), 1),
        }
        for cls_name, label in CHECK_LABELS_JA.items():
            row[label] = str(summary.checks_status.get(cls_name, _absent_mark(cls_name, summary)))
        matrix_rows.append(row)

    if not matrix_rows:
        print(f"posterior が見つかりません: {output_dir}")
        return pd.DataFrame()

    matrix = pd.DataFrame(matrix_rows)
    all_out = io.all_dir(output_dir)
    all_out.mkdir(parents=True, exist_ok=True)
    tables.save_table_csv_and_image(
        matrix, all_out / "health_checks_matrix", title="全モデル ヘルスチェック一覧"
    )
    return matrix
