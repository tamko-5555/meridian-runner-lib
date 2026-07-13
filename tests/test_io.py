import json

from runner_lib import constants, io, synthetic


def test_load_flexible_kernel_format(tmp_path, unfitted_mmm):
    p = synthetic.write_setup_binpb(unfitted_mmm, tmp_path / "s.binpb")
    loaded = io.load_meridian_flexible(p)
    assert list(loaded.input_data.media_channel.values) == ["ch1", "ch2"]


def test_load_flexible_mmm_wrapped_format(tmp_path, unfitted_mmm):
    p = synthetic.write_setup_binpb(unfitted_mmm, tmp_path / "s.binpb", wrap_in_mmm=True)
    loaded = io.load_meridian_flexible(p)
    assert list(loaded.input_data.media_channel.values) == ["ch1", "ch2"]


def test_save_posterior_roundtrip(tmp_path, fitted_mmm):
    out = io.save_posterior(fitted_mmm, tmp_path, "s1")
    assert out == tmp_path / "posterior_s1.binpb"
    loaded = io.load_meridian_flexible(out)
    assert hasattr(loaded.inference_data, "posterior")


def test_paths():
    assert io.eda_json_path("/o", "s1").as_posix().endswith("eda/s1_eda.json")
    assert io.eda_html_path("/o", "s1").as_posix().endswith("eda/s1_eda.html")
    assert io.full_binpb_path("/o", "s1").as_posix().endswith("full/s1_full.binpb")
    assert io.geo_json_path("/o", "s1").as_posix().endswith("full/s1_geo.json")


def test_list_setups_status(tmp_path):
    inp = tmp_path / "in"
    out = tmp_path / "out"
    inp.mkdir()
    out.mkdir()
    (inp / "setup_a.binpb").write_bytes(b"x")
    (inp / "setup_b.binpb").write_bytes(b"x")
    (inp / "setup_c.binpb").write_bytes(b"x")
    # a: posterior 済み
    (out / "posterior_setup_a.binpb").write_bytes(b"x")
    # b: EDA エラー記録あり
    (out / constants.EDA_DIRNAME).mkdir()
    (out / constants.EDA_DIRNAME / "setup_b_eda.json").write_text(json.dumps({"has_error": True}))
    statuses = {s.name: s.status for s in io.list_setups(inp, out)}
    assert statuses == {"setup_a": "done", "setup_b": "eda_error", "setup_c": "pending"}
