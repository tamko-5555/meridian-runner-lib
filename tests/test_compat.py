import xarray as xr


def test_bottleneck_dispatch_disabled_after_import():
    import runner_lib.io  # noqa: F401

    assert xr.get_options()["use_bottleneck"] is False
