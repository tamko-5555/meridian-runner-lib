"""グラフ一式の生成・保存(Altair は PNG+HTML、matplotlib は PNG)."""

from __future__ import annotations

import re
from pathlib import Path

import altair as alt
import arviz as az
import matplotlib.pyplot as plt
from meridian.analysis import visualizer
from meridian.model import model

from runner_lib import constants, io

alt.data_transformers.disable_max_rows()


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def _display(obj) -> None:
    try:
        from IPython.display import display

        display(obj)
    except Exception:
        pass


def save_chart(
    chart, out_base: Path, title: str | None = None, display: bool = False
) -> list[Path]:
    if chart is None:
        return []
    if title is not None:
        try:
            chart = chart.properties(title=title)
        except Exception:
            pass
    if display:
        _display(chart)
    saved = []
    for suffix in (".png", ".html"):
        path = out_base.with_suffix(suffix)
        try:
            chart.save(str(path))
            saved.append(path)
        except Exception as e:
            print(f"  ⚠ {path.name} の保存をスキップ: {type(e).__name__}")
    return saved


def _save_chart_or_mapping(obj, out_base: Path, title_prefix: str, display: bool = False) -> None:
    if obj is None:
        return
    if isinstance(obj, dict):
        for key, chart in obj.items():
            save_chart(
                chart,
                out_base.with_name(f"{out_base.name}_{safe_filename(str(key))}"),
                title=f"{title_prefix} - {key}",
                display=display,
            )
    else:
        save_chart(obj, out_base, title=title_prefix, display=display)


def _guarded(label: str):
    """個々のチャート失敗で全体を止めないためのデコレータ."""

    def deco(fn):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"  ⏭ {label} をスキップしました: {type(e).__name__}: {e}")

        return wrapper

    return deco


def save_diagnostics(
    mmm: model.Meridian, out_dir: Path, setup_name: str, display: bool = False
) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = safe_filename(setup_name)
    mfit = visualizer.ModelFit(mmm)
    diag = visualizer.ModelDiagnostics(mmm)

    _guarded("Model Fit")(
        lambda: save_chart(
            mfit.plot_model_fit(show_geo_level=False, include_ci=True),
            out_dir / f"{name}_model_fit",
            title=f"Model Fit : {setup_name}",
            display=display,
        )
    )()

    @_guarded("Trace Plot (beta_m)")
    def _trace():
        try:
            az.plot_trace(
                mmm.inference_data,
                var_names=["beta_m"],
                compact=False,
                backend_kwargs={"constrained_layout": True},
            )
            plt.suptitle(f"Trace Plot (beta_m) : {setup_name}", fontsize=14)
            plt.savefig(str(out_dir / f"{name}_trace_beta_m.png"), bbox_inches="tight")
            if display:
                plt.show()
        finally:
            plt.close("all")

    _trace()

    for param in ("roi_m", "beta_om", "gamma_c"):
        _guarded(f"Prior vs Posterior ({param})")(
            lambda p=param: save_chart(
                diag.plot_prior_and_posterior_distribution(parameter=p),
                out_dir / f"{name}_prior_posterior_{p}",
                title=f"Prior vs Posterior ({p}) : {setup_name}",
                display=display,
            )
        )()


def save_media_charts(
    mmm: model.Meridian,
    out_dir: Path,
    setup_name: str,
    use_kpi: bool = True,
    selected_times=None,
    display: bool = False,
) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = safe_filename(setup_name)
    media_summary = visualizer.MediaSummary(mmm, selected_times=selected_times, use_kpi=use_kpi)
    media_effects = visualizer.MediaEffects(mmm, use_kpi=use_kpi)

    chart_makers = [
        (
            "contribution_waterfall",
            "Contribution Waterfall",
            media_summary.plot_contribution_waterfall_chart,
        ),
        (
            "contribution_pie",
            "Contribution Pie",
            media_summary.plot_contribution_pie_chart,
        ),
        (
            "spend_vs_contribution",
            "Spend vs Contribution",
            media_summary.plot_spend_vs_contribution,
        ),
        (
            "roi_bar",
            "ROI by Channel",
            lambda: media_summary.plot_roi_bar_chart(include_ci=True),
        ),
        ("roi_vs_mroi", "ROI vs mROI", media_summary.plot_roi_vs_mroi),
        (
            "response_curves_all",
            "Response Curves All",
            lambda: media_effects.plot_response_curves(
                selected_times=selected_times,
                plot_separately=False,
                include_ci=False,
                num_channels_displayed=None,
            ),
        ),
        (
            "response_curves_separate",
            "Response Curves Separate",
            lambda: media_effects.plot_response_curves(
                selected_times=selected_times, plot_separately=True, include_ci=True
            ),
        ),
        (
            "adstock_decay",
            "Adstock Decay",
            lambda: media_effects.plot_adstock_decay(include_ci=True),
        ),
    ]
    for suffix, title, make in chart_makers:
        _guarded(title)(
            lambda m=make, s=suffix, t=title: save_chart(
                m(),
                out_dir / f"{name}_{s}",
                title=f"{t} : {setup_name}",
                display=display,
            )
        )()

    _guarded("Hill Curves")(
        lambda: _save_chart_or_mapping(
            media_effects.plot_hill_curves(include_prior=True, include_ci=True),
            out_dir / f"{name}_hill_curves",
            title_prefix=f"Hill Curves : {setup_name}",
            display=display,
        )
    )()

    @_guarded("Summary table")
    def _table():
        table = media_summary.summary_table(
            include_prior=False,
            include_posterior=True,
            include_non_paid_channels=True,
        )
        if display:
            _display(table)
        table.to_csv(
            out_dir / f"{name}_media_summary_table.csv",
            index=False,
            encoding="utf-8-sig",
        )

    _table()

    @_guarded("Response curves data")
    def _rc_data():
        data = media_effects.response_curves_data(selected_times=selected_times)
        data.to_dataframe().reset_index().to_csv(
            out_dir / f"{name}_response_curves_data.csv",
            index=False,
            encoding="utf-8-sig",
        )

    _rc_data()


def save_all_for_dir(output_dir, use_kpi: bool = True, display: bool = False) -> None:
    output_dir = Path(output_dir)
    checks_dir = output_dir / constants.CHECKS_DIRNAME
    prefix = constants.POSTERIOR_PREFIX
    for p in sorted(output_dir.glob(f"{prefix}*.binpb")):
        setup_name = p.stem[len(prefix) :]
        print(f"\n{'=' * 50}\n📊 Setup: {setup_name}\n{'=' * 50}")
        try:
            mmm = io.load_meridian_flexible(p)
            save_diagnostics(mmm, checks_dir, setup_name, display=display)
            save_media_charts(mmm, checks_dir, setup_name, use_kpi=use_kpi, display=display)
        except Exception as e:
            print(f"❌ {setup_name} の処理中にエラー: {type(e).__name__}: {e}")
