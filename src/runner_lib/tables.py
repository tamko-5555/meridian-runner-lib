"""表形式データの画像出力と日本語フォント設定."""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

JP_FONT = "IPAexGothic"

MAX_ROWS = 60
_WRAP_WIDTH = 36
_FONT_SIZE = 9

_fonts_ready = False


def setup_japanese_fonts() -> None:
    """matplotlib と Altair PNG 出力(vl-convert)の両方で日本語を描画可能にする.

    japanize-matplotlib 同梱の IPAexGothic を matplotlib に登録して既定フォントにし、
    同じフォントファイルを vl-convert にも登録する(PNG のグリフフォールバックに使われる)。
    冪等なので何度呼んでもよい。
    """
    global _fonts_ready
    if _fonts_ready:
        return
    import japanize_matplotlib

    try:
        import vl_convert as vlc

        vlc.register_font_directory(str(Path(japanize_matplotlib.__file__).parent / "fonts"))
    except Exception as e:
        # vl-convert 側の登録に失敗しても HTML 出力と matplotlib 出力には影響しない
        print(f"  ⚠ Altair PNG の日本語フォント登録をスキップ: {type(e).__name__}")
    _fonts_ready = True


# IPAexGothic に無い絵文字の代替表記(PNG での豆腐化防止。CSV は原文のまま)
_EMOJI_FALLBACK = {"✅": "OK", "⚠️": "注意", "⚠": "注意", "❌": "NG"}


def _cell_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    for emoji, alt in _EMOJI_FALLBACK.items():
        text = text.replace(emoji, alt)
    if len(text) > _WRAP_WIDTH:
        text = textwrap.fill(text, width=_WRAP_WIDTH)
    return text


def save_table_image(
    df: pd.DataFrame,
    out_path: str | Path,
    title: str | None = None,
    max_rows: int = MAX_ROWS,
) -> Path:
    """DataFrame を表形式の PNG として保存する(行数が多い場合は先頭 max_rows 行のみ)."""
    setup_japanese_fonts()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    truncated = len(df) > max_rows
    shown = df.head(max_rows)
    cells = [[_cell_text(v) for v in row] for row in shown.itertuples(index=False)]
    if not cells:
        cells = [["(データなし)"] + [""] * (len(df.columns) - 1)] if len(df.columns) else [[""]]

    # 列ごとの想定幅(全角を2として概算)から図の大きさを決める
    def _disp_width(text: str) -> float:
        return max(
            (sum(2 if ord(ch) > 0x7F else 1 for ch in line) for line in text.split("\n")),
            default=1,
        )

    col_widths = []
    for i, col in enumerate(df.columns):
        cell_max = max((_disp_width(c[i]) for c in cells), default=1)
        col_widths.append(max(_disp_width(str(col)), cell_max, 4))
    fig_w = min(max(sum(col_widths) * 0.11, 4.0), 24.0)
    row_heights = [max(c.count("\n") + 1 for c in row) for row in cells]
    fig_h = min(max((sum(row_heights) + 2) * 0.32, 1.6), 40.0)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    try:
        ax.axis("off")
        tbl = ax.table(
            cellText=cells,
            colLabels=[str(c) for c in df.columns],
            loc="center",
            cellLoc="left",
            colLoc="left",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(_FONT_SIZE)
        total_w = sum(col_widths)
        for (row, col), cell in tbl.get_celld().items():
            cell.set_width(col_widths[col] / total_w)
            if row == 0:
                cell.set_text_props(weight="bold")
                cell.set_facecolor("#e8eef7")
            else:
                cell.set_height(0.9 * row_heights[row - 1] / max(sum(row_heights), 1))
        if title:
            note = f"(先頭{max_rows}行のみ表示。全{len(df)}行はCSVを参照)" if truncated else ""
            ax.set_title(f"{title}{note}", fontsize=12, pad=12)
        elif truncated:
            note = f"(先頭{max_rows}行のみ表示。全{len(df)}行はCSVを参照)"
            ax.set_title(note, fontsize=10, pad=12)
        fig.savefig(out_path, bbox_inches="tight", dpi=150)
    finally:
        plt.close(fig)
    return out_path


def save_table_csv_and_image(
    df: pd.DataFrame,
    out_base: str | Path,
    title: str | None = None,
    max_rows: int = MAX_ROWS,
) -> list[Path]:
    """CSV(utf-8-sig)と表画像 PNG を同名ベースで保存する."""
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    csv_path = out_base.with_suffix(".csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    saved = [csv_path]
    try:
        saved.append(save_table_image(df, out_base.with_suffix(".png"), title, max_rows))
    except Exception as e:
        print(f"  ⚠ 表画像の保存をスキップ: {type(e).__name__}: {e}")
    return saved
