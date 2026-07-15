"""実行環境の互換性対策.

Colab では bottleneck 1.4.2 + numpy 2.x の組み合わせで、xarray が集計を
bottleneck の C 拡張へディスパッチした際に SIGSEGV する(meridian の EDA
レポート生成で最初に踏む)。速度最適化を捨てて安全側に倒す。
"""

from __future__ import annotations

import xarray as xr


def apply() -> None:
    """xarray の bottleneck ディスパッチを無効化する(冪等)."""
    xr.set_options(use_bottleneck=False)


apply()
