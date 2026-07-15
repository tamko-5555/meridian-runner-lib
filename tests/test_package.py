import re


def test_version():
    import runner_lib

    # バージョン値そのものはリリースごとに変わるため固定しない。
    # パッケージングが機能していること(semver形式のバージョンが取れること)だけを検証する。
    assert re.fullmatch(r"\d+\.\d+\.\d+", runner_lib.__version__)


def test_meridian_dependency_importable():
    from meridian.model.eda import meridian_eda  # noqa: F401
    from meridian.schema.serde import meridian_serde  # noqa: F401
