import pandas as pd

from runner_lib import tables


def _jp_df(n_rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "チャネル": [f"メディア{i}" for i in range(n_rows)],
            "判定": ["✅ PASS"] * n_rows,
            "推奨アクション": ["サンプル数を増やして再推定してください。" * 3] * n_rows,
        }
    )


def test_save_table_image_creates_png(tmp_path):
    out = tables.save_table_image(_jp_df(), tmp_path / "t.png", title="テスト表")
    assert out.exists()
    assert out.stat().st_size > 2000


def test_save_table_image_truncates_long_tables(tmp_path):
    out = tables.save_table_image(_jp_df(100), tmp_path / "long.png", max_rows=10)
    assert out.exists()


def test_save_table_image_empty_df(tmp_path):
    out = tables.save_table_image(pd.DataFrame(columns=["a", "b"]), tmp_path / "empty.png")
    assert out.exists()


def test_save_table_csv_and_image(tmp_path):
    saved = tables.save_table_csv_and_image(_jp_df(), tmp_path / "base", title="表")
    names = {p.name for p in saved}
    assert "base.csv" in names
    assert "base.png" in names
    # CSV は Excel で開けるよう BOM 付き UTF-8
    raw = (tmp_path / "base.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")


def test_setup_japanese_fonts_registers_without_changing_default():
    import matplotlib

    before = list(matplotlib.rcParams["font.family"])
    tables.setup_japanese_fonts()
    tables.setup_japanese_fonts()  # 2回呼んでも例外にならない
    # 既定フォント(rcParams)は変更しない — 既存グラフの見た目を変えない契約
    assert list(matplotlib.rcParams["font.family"]) == before
    # IPAexGothic は「利用可能なフォント」として登録されている
    from matplotlib import font_manager

    assert any(f.name == tables.JP_FONT for f in font_manager.fontManager.ttflist)
