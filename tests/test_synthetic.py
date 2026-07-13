import numpy as np

from runner_lib import synthetic


def test_make_synthetic_df_shape_and_columns():
    df = synthetic.make_synthetic_df(n_geos=2, n_weeks=52, seed=0)
    assert len(df) == 2 * 52
    assert {
        "geo",
        "time",
        "kpi",
        "ch1_impr",
        "ch2_spend",
        "organic_ch",
        "promo",
        "temperature",
        "population",
    } <= set(df.columns)


def test_make_synthetic_df_deterministic():
    a = synthetic.make_synthetic_df(seed=1)
    b = synthetic.make_synthetic_df(seed=1)
    assert a.equals(b)


def test_duplicate_channels_are_identical():
    df = synthetic.make_synthetic_df(duplicate_channels=True)
    assert np.allclose(df["ch1_impr"], df["ch2_impr"])
    assert np.allclose(df["ch1_spend"], df["ch2_spend"])


def test_build_unfitted_model(synthetic_df):
    mmm = synthetic.build_unfitted_model(synthetic_df)
    assert list(mmm.input_data.media_channel.values) == ["ch1", "ch2"]


def test_write_setup_binpb_both_formats(tmp_path, unfitted_mmm):
    p1 = synthetic.write_setup_binpb(unfitted_mmm, tmp_path / "kernel.binpb")
    p2 = synthetic.write_setup_binpb(unfitted_mmm, tmp_path / "wrapped.binpb", wrap_in_mmm=True)
    assert p1.stat().st_size > 0 and p2.stat().st_size > 0
    assert p1.read_bytes() != p2.read_bytes()
