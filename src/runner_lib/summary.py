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

from runner_lib import dorega_tokens, full_binpb, io, periods, plots, tables

_ROI_BREAKEVEN_LABEL = "ROI=1(投資回収ライン)"


def _analysis_period(mmm: model.Meridian) -> tuple[pd.DatetimeIndex, pd.Timestamp, pd.Timestamp]:
    available_dates = pd.to_datetime(mmm.input_data.time.values)
    start, end = periods.default_analysis_period(available_dates)
    return available_dates, start, end


def geo_roi_frame(mmm: model.Meridian) -> pd.DataFrame:
    """geo別の全チャネル合計ROI(分析期間は full binpb と同じ)。ROI降順."""
    available_dates, start, end = _analysis_period(mmm)
    selected = periods.period_date_strings(available_dates, start, end)
    records = full_binpb.build_geo_records(mmm, selected)
    df = pd.DataFrame([r for r in records if r["channel"] == "total"])
    return (
        df[["geo", "roi", "incremental"]].sort_values("roi", ascending=False).reset_index(drop=True)
    )


def _geo_roi_chart(df: pd.DataFrame, setup_name: str, period_label: str) -> alt.LayerChart:
    """横バー。ROI≥1(投資回収済み)の地域を強調し、ROI=1に基準線を引いて回収ラインを示す."""
    bar = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "roi:Q",
                title="ROI(全チャネル合計)",
                axis=alt.Axis(grid=False, domain=False, ticks=False),
            ),
            y=alt.Y(
                "geo:N",
                sort="-x",
                title="地域",
                axis=alt.Axis(grid=True, domain=False, ticks=False, gridColor=dorega_tokens.GRID),
            ),
            color=alt.condition(
                alt.datum.roi >= 1,
                alt.value(dorega_tokens.SERIES[0]),
                alt.value(dorega_tokens.BASELINE_GRAY),
            ),
            tooltip=["geo:N", "roi:Q", "incremental:Q"],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame({"roi": [1]}))
        .mark_rule(strokeDash=[4, 4], color=dorega_tokens.MUTED)
        .encode(x="roi:Q")
    )
    annotation = (
        alt.Chart(pd.DataFrame({"roi": [1], "label": [_ROI_BREAKEVEN_LABEL]}))
        .mark_text(
            align="left",
            dx=4,
            dy=-4,
            font=tables.JP_FONT,
            fontSize=dorega_tokens.AXIS_LABEL_FONT_SIZE,
            color=dorega_tokens.MUTED,
        )
        .encode(x="roi:Q", y=alt.value(0), text="label:N")
    )
    return (bar + rule + annotation).properties(
        height=alt.Step(14),
        title=alt.TitleParams(
            text="地域別ROI: どの地域で広告が効いているか",
            subtitle=f"{period_label} ・ {setup_name}",
            font=tables.JP_FONT,
            subtitleFont=tables.JP_FONT,
            fontSize=dorega_tokens.TITLE_FONT_SIZE,
            fontWeight="bold",
            subtitleFontSize=dorega_tokens.SUBTITLE_FONT_SIZE,
            subtitleColor=dorega_tokens.MUTED,
            anchor="start",
        ),
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
    _, start, end = _analysis_period(mmm)
    period_label = f"{start:%Y-%m-%d}〜{end:%Y-%m-%d}"
    return plots.save_chart(
        _geo_roi_chart(df, setup_name, period_label),
        out_dir / f"{name}_geo_roi",
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
