import json

import pandas as pd
from meridian.schema.processors import model_fit_processor
from mmm.v1 import mmm_pb2 as mmm_pb

from runner_lib import full_binpb, io, periods  # noqa: F401


def test_build_geo_records(fitted_mmm):
    dates = pd.to_datetime(fitted_mmm.input_data.time.values)
    selected = [d.strftime("%Y-%m-%d") for d in dates]
    records = full_binpb.build_geo_records(fitted_mmm, selected)
    assert {r["geo"] for r in records} == {"geo_0", "geo_1"}
    channels = {r["channel"] for r in records}
    assert "total" in channels and "All Paid Channels" not in channels
    assert all(set(r) == {"geo", "channel", "incremental", "roi"} for r in records)


def test_generate_full_artifacts_minimal_specs(tmp_path, fitted_mmm):
    result = full_binpb.generate_full_artifacts(
        fitted_mmm,
        "s1",
        tmp_path,
        specs_override=[model_fit_processor.ModelFitSpec()],
    )
    binpb = io.full_binpb_path(tmp_path, "s1")
    assert result["binpb"] == binpb and binpb.exists()

    proto = mmm_pb.Mmm.FromString(binpb.read_bytes())
    assert proto.HasField("mmm_kernel")
    assert proto.HasField("model_fit")

    geo_json = io.geo_json_path(tmp_path, "s1")
    assert result["geo_json"] == geo_json and geo_json.exists()
    records = json.loads(geo_json.read_text())
    assert len(records) > 0


def test_generate_full_artifacts_overwrites(tmp_path, fitted_mmm):
    kwargs = dict(specs_override=[model_fit_processor.ModelFitSpec()])
    full_binpb.generate_full_artifacts(fitted_mmm, "s1", tmp_path, **kwargs)
    first_mtime = io.full_binpb_path(tmp_path, "s1").stat().st_mtime_ns
    full_binpb.generate_full_artifacts(fitted_mmm, "s1", tmp_path, **kwargs)
    assert io.full_binpb_path(tmp_path, "s1").stat().st_mtime_ns >= first_mtime
