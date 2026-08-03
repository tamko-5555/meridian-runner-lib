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


def test_setup_scoped_paths(tmp_path):
    assert io.setup_dir(tmp_path, "s1") == tmp_path / "s1"
    assert io.eda_json_path(tmp_path, "s1") == tmp_path / "s1" / "eda" / "s1_eda.json"
    assert io.eda_html_path(tmp_path, "s1") == tmp_path / "s1" / "eda" / "s1_eda.html"
    assert io.full_binpb_path(tmp_path, "s1") == tmp_path / "s1" / "full" / "s1_full.binpb"
    assert io.geo_json_path(tmp_path, "s1") == tmp_path / "s1" / "full" / "s1_geo.json"
    assert io.checks_dir(tmp_path, "s1") == tmp_path / "s1" / "checks"
    assert io.health_dir(tmp_path, "s1") == tmp_path / "s1" / "checks" / "health"
    assert io.optimization_dir(tmp_path, "s1") == tmp_path / "s1" / "optimization"
    assert io.all_dir(tmp_path) == tmp_path / "_all"
    assert io.summary_dir(tmp_path) == tmp_path / "summary"
    # posterior はルート直下のまま(スキップ判定の契約)
    assert io.posterior_path(tmp_path, "s1") == tmp_path / "posterior_s1.binpb"


def test_setup_dir_sanitizes_name(tmp_path):
    assert io.setup_dir(tmp_path, "a/b c") == tmp_path / "a_b_c"
    assert io.safe_filename("ab/c d:e") == "ab_c_d_e"


def test_list_setups_status(tmp_path):
    inp = tmp_path / "in"
    out = tmp_path / "out"
    inp.mkdir()
    out.mkdir()
    (inp / "setup_a.binpb").write_bytes(b"x")
    (inp / "setup_b.binpb").write_bytes(b"x")
    (inp / "setup_c.binpb").write_bytes(b"x")
    # INPUT_DIR == OUTPUT_DIR 誤設定時などに紛れ込む posterior ファイルはセットアップとして扱わない
    (inp / f"{constants.POSTERIOR_PREFIX}stray.binpb").write_bytes(b"x")
    # a: posterior 済み
    (out / "posterior_setup_a.binpb").write_bytes(b"x")
    # b: EDA エラー記録あり（セットアップスコープ構造）
    eda_path = io.eda_json_path(out, "setup_b")
    eda_path.parent.mkdir(parents=True, exist_ok=True)
    eda_path.write_text(json.dumps({"has_error": True}))
    statuses = {s.name: s.status for s in io.list_setups(inp, out)}
    assert statuses == {"setup_a": "done", "setup_b": "eda_error", "setup_c": "pending"}
