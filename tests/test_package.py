def test_version():
    import runner_lib

    assert runner_lib.__version__ == "0.1.0"


def test_meridian_dependency_importable():
    from meridian.model.eda import meridian_eda  # noqa: F401
    from meridian.schema.serde import meridian_serde  # noqa: F401
