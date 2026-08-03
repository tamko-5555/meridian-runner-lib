"""意思決定用サマリー(summary/): 主要グラフの複製と地域別ROIバーの生成.

4つのビジネス課題に対応する: ①媒体別の寄与度 ②地域別の広告効果
③最適な予算配分 ④予算増減による期待リターン
"""

from __future__ import annotations

import shutil
from pathlib import Path

import altair as alt
import pandas as pd
from meridian.model import model

from runner_lib import full_binpb, io, periods, plots, tables


def geo_roi_frame(mmm: model.Meridian) -> pd.DataFrame:
    """geo別の全チャネル合計ROI(分析期間は full binpb と同じ)。ROI降順."""
    available_dates = pd.to_datetime(mmm.input_data.time.values)
    start, end = periods.default_analysis_period(available_dates)
    selected = periods.period_date_strings(available_dates, start, end)
    records = full_binpb.build_geo_records(mmm, selected)
    df = pd.DataFrame([r for r in records if r["channel"] == "total"])
    return (
        df[["geo", "roi", "incremental"]].sort_values("roi", ascending=False).reset_index(drop=True)
    )


def _geo_roi_chart(df: pd.DataFrame) -> alt.Chart:
    """横バー。ROI<1(投資未回収)の地域を赤で強調して「感度が低い地域」を示す."""
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("roi:Q", title="ROI(全チャネル合計)"),
            y=alt.Y("geo:N", sort="-x", title="地域"),
            color=alt.condition(alt.datum.roi < 1, alt.value("#d62728"), alt.value("#4c78a8")),
            tooltip=["geo:N", "roi:Q", "incremental:Q"],
        )
        .properties(height=alt.Step(14))
    )


def save_geo_roi_chart(mmm: model.Meridian, setup_name: str, output_dir: str | Path) -> list[Path]:
    """summary/ に地域別ROIバーを保存する。national モデルは対象外(空リスト)."""
    if mmm.model_context.is_national:
        print(f"  ⏭ {setup_name}: national モデルのため地域別ROIグラフは対象外")
        return []
    tables.setup_japanese_fonts()
    out_dir = io.summary_dir(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = plots.safe_filename(setup_name)
    df = geo_roi_frame(mmm)
    return plots.save_chart(
        _geo_roi_chart(df),
        out_dir / f"{name}_geo_roi",
        title=f"地域別ROI: どの地域で広告が効いているか({setup_name})",
    )


# 複製する成果物: (元フォルダ種別, ファイル名stem)。①と③④に対応(②は新規生成)
_COPY_SOURCES = (
    ("checks", "contribution_waterfall"),
    ("optimization", "budget_allocation"),
    ("optimization", "outcome_delta"),
    ("optimization", "budget_scenarios"),
    ("optimization", "budget_scenarios_chart"),
)


def build_summary(mmm: model.Meridian, setup_name: str, output_dir: str | Path) -> dict:
    """summary/ を構築する: 地域別ROIバーの生成 + 主要グラフPNGの複製.

    複製元が無い場合(例: Phase 2 未実行で waterfall が無い)は警告して続行する。
    """
    out_dir = io.summary_dir(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = plots.safe_filename(setup_name)

    files = list(save_geo_roi_chart(mmm, setup_name, output_dir))
    missing: list[str] = []
    src_dirs = {
        "checks": io.checks_dir(output_dir, setup_name),
        "optimization": io.optimization_dir(output_dir, setup_name),
    }
    for kind, stem in _COPY_SOURCES:
        src = src_dirs[kind] / f"{name}_{stem}.png"
        if not src.exists():
            missing.append(f"{kind}/{name}_{stem}.png")
            continue
        dst = out_dir / src.name
        shutil.copy2(src, dst)
        files.append(dst)
    if missing:
        print(f"  ⚠ summary 複製元が見つかりません(スキップ): {', '.join(missing)}")
        if any(m.startswith("checks/") for m in missing):
            print("    → Phase 2(グラフ一式の生成)を実行してから Phase 3 を再実行すると揃います")
    print(f"  ✔ summary/ に {len(files)} ファイル")
    return {"files": files, "missing": missing}
