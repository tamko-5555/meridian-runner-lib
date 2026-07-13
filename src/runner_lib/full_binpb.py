"""完全版 binpb(全分析結果入り Mmm proto)と geo JSON の生成."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from meridian import constants as meridian_constants
from meridian.analysis import analyzer
from meridian.model import model
from meridian.schema import mmm_proto_generator

from runner_lib import io, periods
from runner_lib import specs as specs_module


def build_geo_records(mmm: model.Meridian, selected_times: list[str]) -> list[dict]:
    azr = analyzer.Analyzer(model_context=mmm.model_context, inference_data=mmm.inference_data)
    geo_summary = azr.summary_metrics(
        selected_times=selected_times, aggregate_geos=False, aggregate_times=True
    )
    inc = geo_summary["incremental_outcome"].sel(distribution="posterior", metric="mean")
    roi = geo_summary["roi"].sel(distribution="posterior", metric="mean")
    df = (
        inc.to_dataframe("incremental")
        .reset_index()
        .merge(roi.to_dataframe("roi").reset_index(), on=["geo", "channel"])
    )
    df["channel"] = df["channel"].replace(meridian_constants.ALL_CHANNELS, "total")
    return df[["geo", "channel", "incremental", "roi"]].to_dict(orient="records")


def generate_full_artifacts(
    mmm: model.Meridian,
    setup_name: str,
    output_dir: str | Path,
    *,
    cost_rate: float = 0.0,
    specs_override: list | None = None,
) -> dict:
    all_specs = (
        specs_override
        if specs_override is not None
        else specs_module.build_analysis_specs(mmm, cost_rate=cost_rate)
    )

    proto = mmm_proto_generator.create_mmm_proto(mmm=mmm, specs=all_specs, model_id=setup_name)
    binpb = io.full_binpb_path(output_dir, setup_name)
    binpb.parent.mkdir(parents=True, exist_ok=True)
    binpb.write_bytes(proto.SerializeToString())

    geo_json: Path | None = None
    if not mmm.model_context.is_national:
        available_dates = pd.to_datetime(mmm.input_data.time.values)
        start, end = periods.default_analysis_period(available_dates)
        selected = periods.period_date_strings(available_dates, start, end)
        records = build_geo_records(mmm, selected)
        geo_json = io.geo_json_path(output_dir, setup_name)
        geo_json.write_text(json.dumps(records, ensure_ascii=False))

    return {"binpb": binpb, "geo_json": geo_json, "n_specs": len(all_specs)}
