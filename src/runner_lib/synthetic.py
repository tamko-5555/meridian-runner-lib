"""テスト・ローカル検証用の合成 MMM データ生成(実データ不要で全機能を検証するため)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from meridian.data import data_frame_input_data_builder as dfb
from meridian.model import model, spec
from meridian.schema.serde import meridian_serde
from mmm.v1 import mmm_pb2 as mmm_pb
from mmm.v1.model import mmm_kernel_pb2 as kernel_pb


def make_synthetic_df(
    n_geos: int = 2,
    n_weeks: int = 52,
    seed: int = 0,
    duplicate_channels: bool = False,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-07", periods=n_weeks, freq="W-SUN").strftime("%Y-%m-%d")
    rows = []
    for g in range(n_geos):
        base = 1000 + 200 * g
        m1 = rng.gamma(2.0, 100, n_weeks)
        m2 = m1.copy() if duplicate_channels else rng.gamma(2.0, 80, n_weeks)
        s1 = m1 * rng.uniform(0.4, 0.6, n_weeks)
        s2 = s1.copy() if duplicate_channels else m2 * rng.uniform(0.5, 0.7, n_weeks)
        org = rng.gamma(2.0, 50, n_weeks)
        promo = (rng.uniform(0, 1, n_weeks) > 0.7).astype(float)
        ctrl = rng.normal(0, 1, n_weeks)
        kpi = (
            base
            + 0.3 * m1
            + 0.2 * m2
            + 0.1 * org
            + 30 * promo
            + 10 * ctrl
            + rng.normal(0, 30, n_weeks)
        )
        for t in range(n_weeks):
            rows.append(
                {
                    "geo": f"geo_{g}",
                    "time": dates[t],
                    "kpi": kpi[t],
                    "population": 1_000_000 * (g + 1),
                    "ch1_impr": m1[t],
                    "ch2_impr": m2[t],
                    "ch1_spend": s1[t],
                    "ch2_spend": s2[t],
                    "organic_ch": org[t],
                    "promo": promo[t],
                    "temperature": ctrl[t],
                }
            )
    return pd.DataFrame(rows)


def build_unfitted_model(df: pd.DataFrame) -> model.Meridian:
    input_data = (
        dfb.DataFrameInputDataBuilder(kpi_type="revenue")
        .with_kpi(df)
        .with_population(df)
        .with_media(
            df,
            media_cols=["ch1_impr", "ch2_impr"],
            media_spend_cols=["ch1_spend", "ch2_spend"],
            media_channels=["ch1", "ch2"],
        )
        .with_organic_media(
            df, organic_media_cols=["organic_ch"], organic_media_channels=["organic_ch"]
        )
        .with_non_media_treatments(df, non_media_treatment_cols=["promo"])
        .with_controls(df, control_cols=["temperature"])
        .build()
    )
    return model.Meridian(input_data=input_data, model_spec=spec.ModelSpec(max_lag=2, knots=4))


def write_setup_binpb(mmm: model.Meridian, path: Path, wrap_in_mmm: bool = False) -> Path:
    path = Path(path)
    if not wrap_in_mmm:
        meridian_serde.save_meridian(mmm, str(path))
        return path
    kernel = meridian_serde.MeridianSerde().serialize(mmm)
    assert isinstance(kernel, kernel_pb.MmmKernel)
    path.write_bytes(mmm_pb.Mmm(mmm_kernel=kernel).SerializeToString())
    return path
