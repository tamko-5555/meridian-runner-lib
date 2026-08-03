"""予算配分最適化の成果物(グラフ・表・公式サマリHTML)を OUTPUT_DIR/optimization/ に保存する.

binpb 内の BudgetOptimizationSpec 群(specs.py)と同じ分析期間・同じ予算倍率・
同じ目標mROI(1/(1-cost_rate))を使い、レポーター側の表示と数字が整合するようにしている。
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
from meridian.analysis import optimizer
from meridian.model import model

from runner_lib import constants, io, periods, plots, specs, tables

# 予算スイープの倍率: binpb 内の固定予算シナリオ(specs.FIXED_BUDGET_RATIOS)+ 現行(1.0)
SWEEP_RATIOS: tuple[float, ...] = tuple(sorted({*specs.FIXED_BUDGET_RATIOS, 1.0}))

_FLEXIBLE_LABEL = "推奨総予算(目標mROI={mroi})"


def _mean_values(ds, var: str) -> np.ndarray:
    """metric 次元(mean/ci_lo/ci_hi)を持つ変数から mean を取り出す."""
    da = ds[var]
    if "metric" in da.dims:
        da = da.sel(metric="mean")
    return np.asarray(da.values, dtype=float)


def allocation_table(results: optimizer.OptimizationResults) -> pd.DataFrame:
    """チャネル別の現在予算 vs 最適予算の比較表."""
    non = results.nonoptimized_data
    opt = results.optimized_data
    cur_spend = _mean_values(non, "spend")
    opt_spend = _mean_values(opt, "spend")
    return pd.DataFrame(
        {
            "チャネル": [str(c) for c in non.channel.values],
            "現在の予算": np.round(cur_spend, 1),
            "最適予算": np.round(opt_spend, 1),
            "増減額": np.round(opt_spend - cur_spend, 1),
            "現在の構成比%": np.round(_mean_values(non, "pct_of_spend") * 100, 1),
            "最適構成比%": np.round(_mean_values(opt, "pct_of_spend") * 100, 1),
            "最適時ROI": np.round(_mean_values(opt, "roi"), 3),
            "最適時 限界ROI": np.round(_mean_values(opt, "mroi"), 3),
        }
    )


def _scenario_row(label: str, results: optimizer.OptimizationResults) -> dict:
    attrs = results.optimized_data.attrs
    return {
        "シナリオ": label,
        "総予算": float(attrs["budget"]),
        "期待増分リターン(最適配分)": float(attrs["total_incremental_outcome"]),
        "総ROI": float(attrs["total_roi"]),
    }


def budget_sweep_table(
    opt: optimizer.BudgetOptimizer,
    base_results: optimizer.OptimizationResults,
    *,
    start_date,
    end_date,
    ideal_mroi: float,
    ratios: tuple[float, ...] = SWEEP_RATIOS,
) -> pd.DataFrame:
    """総予算を現行の各倍率に振った場合と目標mROI達成予算の期待リターン表.

    「追加でいくら費やすといくら返るか」は、現行予算行との差分
    (現行比の追加予算・追加リターン)と、1つ下の予算シナリオとの差分から求めた
    限界ROI で読み取れるようにしている。
    """
    base_budget = float(base_results.optimized_data.attrs["budget"])
    rows = []
    for ratio in ratios:
        if np.isclose(ratio, 1.0):
            rows.append({**_scenario_row("現行予算(100%)", base_results), "種別": "固定予算"})
            continue
        res = opt.optimize(start_date=start_date, end_date=end_date, budget=base_budget * ratio)
        rows.append({**_scenario_row(f"現行の{int(ratio * 100)}%", res), "種別": "固定予算"})
        print(f"  ✔ 予算シナリオ {int(ratio * 100)}% を計算")

    flex = opt.optimize(
        start_date=start_date, end_date=end_date, fixed_budget=False, target_mroi=ideal_mroi
    )
    rows.append(
        {
            **_scenario_row(_FLEXIBLE_LABEL.format(mroi=ideal_mroi), flex),
            "種別": "目標mROI",
        }
    )
    print(f"  ✔ 目標mROI={ideal_mroi} の推奨総予算を計算")

    df = pd.DataFrame(rows).sort_values("総予算").reset_index(drop=True)
    base_outcome = float(base_results.optimized_data.attrs["total_incremental_outcome"])
    df["現行比の追加予算"] = df["総予算"] - base_budget
    df["現行比の追加リターン"] = df["期待増分リターン(最適配分)"] - base_outcome
    marginal = [np.nan]
    for i in range(1, len(df)):
        d_budget = df.loc[i, "総予算"] - df.loc[i - 1, "総予算"]
        d_outcome = (
            df.loc[i, "期待増分リターン(最適配分)"] - df.loc[i - 1, "期待増分リターン(最適配分)"]
        )
        marginal.append(d_outcome / d_budget if d_budget > 0 else np.nan)
    df["限界ROI(1つ下の予算比)"] = np.round(marginal, 3)
    for col in ("総予算", "期待増分リターン(最適配分)", "現行比の追加予算", "現行比の追加リターン"):
        df[col] = df[col].round(1)
    df["総ROI"] = df["総ROI"].round(3)
    return df[
        [
            "シナリオ",
            "種別",
            "総予算",
            "現行比の追加予算",
            "期待増分リターン(最適配分)",
            "現行比の追加リターン",
            "総ROI",
            "限界ROI(1つ下の予算比)",
        ]
    ]


def _combined_allocation_chart(results: optimizer.OptimizationResults, setup_name: str):
    """現在(左)と最適化後(右)の配分ドーナツを1枚に並べる.

    Altair は config 付きチャートの連結を許さないため、config を親チャートへ移す。
    """
    current = results.plot_budget_allocation(optimized=False)
    optimized = results.plot_budget_allocation(optimized=True)
    config = current.config
    current.config = alt.Undefined
    optimized.config = alt.Undefined
    combined = alt.hconcat(
        current.properties(title="現在の予算配分"),
        optimized.properties(title="最適化後の予算配分"),
        title=alt.TitleParams(
            text=f"予算配分: 現在 vs 最適化後({setup_name})",
            font=tables.JP_FONT,
            fontSize=16,
            anchor="middle",
        ),
    )
    combined.config = config
    return combined


def _sweep_chart(sweep: pd.DataFrame, setup_name: str):
    base = alt.Chart(sweep).encode(
        x=alt.X("総予算:Q", title="総予算"),
        y=alt.Y("期待増分リターン(最適配分):Q", title="期待増分リターン(最適配分時)"),
    )
    line = base.transform_filter(alt.datum["種別"] == "固定予算").mark_line(point=True)
    flex_point = base.transform_filter(alt.datum["種別"] == "目標mROI").mark_point(
        size=160, shape="diamond", filled=True, color="#d62728"
    )
    labels = base.mark_text(dy=-12, font=tables.JP_FONT).encode(text="シナリオ:N")
    return (line + flex_point + labels).properties(width=560, height=360)


def save_optimization_artifacts(
    mmm: model.Meridian,
    setup_name: str,
    output_dir: str | Path,
    *,
    cost_rate: float = 0.0,
    currency: str = "¥",
    display: bool = False,
) -> dict:
    """予算最適化の成果物一式を OUTPUT_DIR/<setup>/optimization/ に保存する."""
    tables.setup_japanese_fonts()
    out_dir = io.optimization_dir(output_dir, setup_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = plots.safe_filename(setup_name)
    saved: list[Path] = []

    available_dates = pd.to_datetime(mmm.input_data.time.values)
    start, end = periods.default_analysis_period(available_dates)
    start_d, end_d = start.date(), end.date()
    ideal_mroi = round(1.0 / (1.0 - cost_rate), 4)

    opt = optimizer.BudgetOptimizer(mmm)
    print(f"  ✔ 分析期間 {start_d} 〜 {end_d} で最適化を実行")
    base_results = opt.optimize(start_date=start_d, end_date=end_d)

    guarded = plots._guarded

    guarded("予算配分(現在 vs 最適化後)")(
        lambda: saved.extend(
            plots.save_chart(
                _combined_allocation_chart(base_results, setup_name),
                out_dir / f"{name}_budget_allocation",
                display=display,
            )
        )
    )()
    guarded("チャネル別予算の増減額")(
        lambda: saved.extend(
            plots.save_chart(
                base_results.plot_spend_delta(currency=currency),
                out_dir / f"{name}_spend_delta",
                title=f"チャネル別予算の増減額(最適化後 − 現在): {setup_name}",
                display=display,
            )
        )
    )()
    guarded("最適化による増分リターン")(
        lambda: saved.extend(
            plots.save_chart(
                base_results.plot_incremental_outcome_delta(),
                out_dir / f"{name}_outcome_delta",
                title=f"予算最適化による増分リターンの内訳: {setup_name}",
                display=display,
            )
        )
    )()
    guarded("応答曲線と最適スペンド")(
        lambda: saved.extend(
            plots.save_chart(
                base_results.plot_response_curves(),
                out_dir / f"{name}_response_curves",
                title=f"応答曲線と現在→最適スペンド: {setup_name}",
                display=display,
            )
        )
    )()

    @guarded("チャネル別配分表")
    def _alloc_table():
        saved.extend(
            tables.save_table_csv_and_image(
                allocation_table(base_results),
                out_dir / f"{name}_optimized_allocation",
                title=f"チャネル別予算配分: 現在 vs 最適({setup_name})",
            )
        )

    _alloc_table()

    @guarded("公式最適化サマリHTML")
    def _official():
        filename = f"{name}_optimization_summary.html"
        base_results.output_optimization_summary(filename, str(out_dir), currency=currency)
        saved.append(out_dir / filename)

    _official()

    sweep = budget_sweep_table(
        opt, base_results, start_date=start_d, end_date=end_d, ideal_mroi=ideal_mroi
    )
    saved.extend(
        tables.save_table_csv_and_image(
            sweep,
            out_dir / f"{name}_budget_scenarios",
            title=f"予算シナリオ別の期待リターン({start_d} 〜 {end_d}): {setup_name}",
        )
    )
    guarded("予算スイープグラフ")(
        lambda: saved.extend(
            plots.save_chart(
                _sweep_chart(sweep, setup_name),
                out_dir / f"{name}_budget_scenarios_chart",
                title=f"総予算と期待リターン(最適配分時): {setup_name}",
                display=display,
            )
        )
    )()

    return {"dir": out_dir, "files": saved, "sweep": sweep}


_DISPLAY_ITEMS = (
    ("budget_allocation", "予算配分(左: 現在 / 右: 最適化後)"),
    ("spend_delta", "チャネル別の予算増減額"),
    ("outcome_delta", "最適化による増分リターンの内訳"),
    ("response_curves", "応答曲線と現在→最適スペンド"),
)


def display_saved(output_dir: str | Path, setup_name: str | None = None) -> None:
    """<setup>/optimization/ に保存済みの成果物をノートブック上で表示する.

    Phase 3(run_full)実行後に呼ぶ。setup_name を省略すると保存済みの
    全セットアップを順に表示する。
    """
    output_dir = Path(output_dir)
    suffix = "_budget_scenarios.csv"
    if setup_name:
        names = [plots.safe_filename(setup_name)]
    else:
        names = sorted(
            p.parent.parent.name
            for p in output_dir.glob(f"*/{constants.OPTIMIZATION_DIRNAME}/*{suffix}")
        )
    found = [n for n in names if any(io.optimization_dir(output_dir, n).glob(f"*{suffix}"))]
    if not found:
        print(f"最適化成果物が見つかりません: {output_dir}/<setup>/optimization/")
        print("Phase 3(完全版生成)を実行すると生成されます。")
        print("実行済みなのに無い場合は、Phase 3 の実行ログを確認してください。")
        return

    try:
        from IPython.display import Image, Markdown, display
    except ImportError:
        for name in found:
            opt_dir = io.optimization_dir(output_dir, name)
            print(f"[{name}] 保存済みファイル:")
            for p in sorted(opt_dir.glob(f"{name}_*")):
                print(f"  {p}")
        return

    for name in found:
        opt_dir = io.optimization_dir(output_dir, name)
        display(Markdown(f"## 最適化結果: {name}"))
        for stem, caption in _DISPLAY_ITEMS:
            png = opt_dir / f"{name}_{stem}.png"
            if png.exists():
                display(Markdown(f"**{caption}**"))
                display(Image(filename=str(png)))
        csv = opt_dir / f"{name}{suffix}"
        if csv.exists():
            display(Markdown("**予算シナリオ別の期待リターン**(表画像・CSVも保存済み)"))
            display(pd.read_csv(csv))
        chart_png = opt_dir / f"{name}_budget_scenarios_chart.png"
        if chart_png.exists():
            display(Image(filename=str(chart_png)))
        table_png = opt_dir / f"{name}_optimized_allocation.png"
        if table_png.exists():
            display(Markdown("**チャネル別予算配分: 現在 vs 最適**"))
            display(Image(filename=str(table_png)))
        html = opt_dir / f"{name}_optimization_summary.html"
        if html.exists():
            display(Markdown(f"公式最適化サマリHTML: `{html}`(ブラウザで開けます)"))
