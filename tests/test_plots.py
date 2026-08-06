import json

import altair as alt
import pandas as pd

from runner_lib import plots, tables


def test_safe_filename():
    assert plots.safe_filename("ab/c d:e") == "ab_c_d_e"


def _chart_with_google_fonts() -> alt.Chart:
    """meridian と同様に Google Sans Display / Roboto を明示指定したチャート."""
    return (
        alt.Chart(pd.DataFrame({"x": [1, 2], "y": ["a", "b"]}))
        .mark_bar()
        .encode(
            x=alt.X("x:Q", axis=alt.Axis(labelFont="Roboto", titleFont="Roboto")),
            y=alt.Y("y:N", axis=alt.Axis(labelFont="Roboto")),
        )
        .properties(
            title=alt.TitleParams(text="title", font="Google Sans Display", subtitleFont="Roboto")
        )
    )


def test_spec_with_fixed_fonts_replaces_all_font_keys():
    """Colab等に存在しないフォント指定が残っているとテキストが描画されない(退行防止)."""
    spec = plots._spec_with_fixed_fonts(_chart_with_google_fonts(), tables.JP_FONT)
    dumped = json.dumps(spec)
    assert "Roboto" not in dumped
    assert "Google Sans Display" not in dumped
    # 明示指定のないテキストにも既定フォントが効く
    assert spec["config"]["font"] == tables.JP_FONT


def test_save_chart_png_uses_fixed_fonts(tmp_path):
    saved = plots.save_chart(_chart_with_google_fonts(), tmp_path / "c", title="t")
    names = {p.name for p in saved}
    assert "c.png" in names and "c.html" in names
    assert (tmp_path / "c.png").stat().st_size > 1000


def test_save_all_for_dir_creates_chart_files(posterior_dir):
    plots.save_all_for_dir(posterior_dir, use_kpi=True)
    checks_dir = posterior_dir / "setup_normal" / "checks"
    files = {p.name for p in checks_dir.iterdir()}
    # 主要チャートの存在をスモーク確認(HTML は必ず出る)
    assert any("model_fit" in f for f in files)
    assert any("roi_bar" in f for f in files)
    assert any("contribution_waterfall" in f for f in files)
    assert any("adstock_decay" in f for f in files)
    assert any(f.endswith("_media_summary_table.csv") for f in files)
    assert any(f.endswith("_media_summary_table.png") for f in files)  # 表画像も出力される
    assert any("trace_beta_m" in f and f.endswith(".png") for f in files)
