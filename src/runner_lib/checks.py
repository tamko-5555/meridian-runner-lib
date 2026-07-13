"""posterior 済みモデル群の比較チェック(rhat / R² / MAPE / reviewer / 係数)."""

from __future__ import annotations

import json
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd
from meridian.analysis import visualizer
from meridian.analysis.review import reviewer
from meridian.model import model

from runner_lib import constants, io

TARGET_PARAMS = (
    ("beta_m", "media係数"),
    ("beta_om", "organic media係数"),
    ("eta_m", "Hill半飽和点"),
    ("slope_m", "Hill傾き"),
    ("alpha_m", "Adstock decay"),
    ("gamma_c", "controls係数"),
    ("gamma_n", "non_media_treatments係数"),
    ("sigma", "残差標準偏差"),
    ("tau_g_excl_baseline", "geo random effect"),
)

RHAT_THRESHOLD = 1.05


def _dim_labels(posterior, param: str, n_cols: int) -> list[str]:
    param_dims = list(posterior[param].dims[2:])
    if param_dims and param_dims[0] in posterior.coords:
        return [str(v) for v in posterior.coords[param_dims[0]].values]
    if n_cols == 1:
        return [""]
    return [str(i) for i in range(n_cols)]


def coefficient_table(mmm: model.Meridian) -> pd.DataFrame:
    posterior = mmm.inference_data.posterior
    try:
        rhat_vals = az.rhat(posterior)
    except Exception:
        rhat_vals = None

    rows = []
    for param, desc in TARGET_PARAMS:
        if param not in posterior:
            continue
        val = posterior[param].values
        flat = val.reshape(val.shape[0] * val.shape[1], -1)
        rhat_arr = rhat_vals[param].values if rhat_vals is not None and param in rhat_vals else None
        for i, label in enumerate(_dim_labels(posterior, param, flat.shape[1])):
            col = flat[:, i]
            rh = float(rhat_arr.flat[i]) if rhat_arr is not None else np.nan
            rows.append(
                {
                    "parameter": param,
                    "description": desc,
                    "channel/dim": label,
                    "mean": round(float(col.mean()), 5),
                    "sd": round(float(col.std()), 5),
                    "2.5%": round(float(np.percentile(col, 2.5)), 5),
                    "97.5%": round(float(np.percentile(col, 97.5)), 5),
                    "r_hat": round(rh, 4) if np.isfinite(rh) else rh,
                }
            )
    return pd.DataFrame(rows)


def model_config_summary(mmm: model.Meridian) -> dict:
    idata = mmm.input_data
    ms = mmm.model_spec
    return {
        "paid_channels": [str(c) for c in idata.media_channel.values]
        if idata.media is not None
        else [],
        "organic_channels": [str(c) for c in idata.organic_media_channel.values]
        if idata.organic_media is not None
        else [],
        "non_media_treatments": [str(c) for c in idata.non_media_channel.values]
        if idata.non_media_treatments is not None
        else [],
        "controls": [str(c) for c in idata.control_variable.values]
        if idata.controls is not None
        else [],
        "knots": ms.knots,
        "max_lag": ms.max_lag,
        "unique_sigma_for_each_geo": ms.unique_sigma_for_each_geo,
    }


def review_model(mmm: model.Meridian) -> tuple[str, float]:
    summary = reviewer.ModelReviewer(
        model_context=mmm.model_context, inference_data=mmm.inference_data
    ).run()
    return summary.overall_status.name, float(summary.health_score)


def _accuracy(mmm: model.Meridian) -> tuple[float | None, float | None]:
    try:
        acc = visualizer.ModelDiagnostics(mmm).predictive_accuracy_table()
        r2 = acc.loc[acc["metric"] == "R_Squared", "value"]
        mape = acc.loc[acc["metric"] == "MAPE", "value"]
        return (
            float(r2.iloc[0]) if not r2.empty else None,
            float(mape.iloc[0]) if not mape.empty else None,
        )
    except Exception:
        return None, None


def _iter_posteriors(output_dir: str | Path):
    prefix = constants.POSTERIOR_PREFIX
    for p in sorted(Path(output_dir).glob(f"{prefix}*.binpb")):
        yield p.stem[len(prefix) :], io.load_meridian_flexible(p)


def summary_table(output_dir: str | Path) -> pd.DataFrame:
    rows = []
    for name, mmm in _iter_posteriors(output_dir):
        coef = coefficient_table(mmm)
        rhat_max = float(coef["r_hat"].max()) if coef["r_hat"].notna().any() else np.nan
        r2, mape = _accuracy(mmm)
        try:
            status, score = review_model(mmm)
        except Exception as e:
            status, score = f"error: {type(e).__name__}", np.nan
        cfg = model_config_summary(mmm)
        rows.append(
            {
                "setup": name,
                "rhat_max": round(rhat_max, 4) if np.isfinite(rhat_max) else rhat_max,
                "rhat_ok": "✅" if np.isfinite(rhat_max) and rhat_max <= RHAT_THRESHOLD else "⚠️",
                "R2": round(r2, 3) if r2 is not None else np.nan,
                "MAPE": round(mape, 3) if mape is not None else np.nan,
                "health_score": score,
                "review_status": status,
                "knots": cfg["knots"],
                "max_lag": cfg["max_lag"],
                "paid_ch": ", ".join(cfg["paid_channels"]),
                "organic_ch": ", ".join(cfg["organic_channels"]),
                "nmt": ", ".join(cfg["non_media_treatments"]),
                "controls": ", ".join(cfg["controls"]),
            }
        )
    return pd.DataFrame(rows)


def _checks_dir(output_dir: str | Path) -> Path:
    d = Path(output_dir) / constants.CHECKS_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_model_summaries_json(output_dir: str | Path) -> Path:
    payload = {}
    for name, mmm in _iter_posteriors(output_dir):
        r2, mape = _accuracy(mmm)
        payload[name] = {
            "config": model_config_summary(mmm),
            "R2": r2,
            "MAPE": mape,
            "coefficients": coefficient_table(mmm).to_dict(orient="records"),
        }
    out = _checks_dir(output_dir) / "model_summaries.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return out


def export_coefficients_csv(output_dir: str | Path) -> Path:
    frames = []
    for name, mmm in _iter_posteriors(output_dir):
        df = coefficient_table(mmm)
        df.insert(0, "setup", name)
        frames.append(df)
    out = _checks_dir(output_dir) / "all_models_coefficients.csv"
    pd.concat(frames, ignore_index=True).to_csv(out, index=False, encoding="utf-8-sig")
    return out
