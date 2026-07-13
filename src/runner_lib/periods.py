"""分析期間(直近1年・先月末まで)と期間内予算の計算."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


def default_analysis_period(
    available_dates: pd.DatetimeIndex,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """データ実在日に補正した「先月末までの直近1年」を返す."""
    last = available_dates.max()
    ideal_end = datetime(last.year, last.month, 1) - timedelta(days=1)
    ideal_start = ideal_end - timedelta(days=364)

    end_candidates = available_dates[available_dates <= ideal_end]
    if len(end_candidates) == 0:
        raise ValueError(
            f"先月末({ideal_end:%Y-%m-%d})以前のデータが存在しません。データ期間が短すぎます。"
        )
    end = end_candidates.max()

    start_candidates = available_dates[available_dates >= ideal_start]
    start = start_candidates.min()
    if start > end:
        raise ValueError(f"期間が成立しません: start={start} > end={end}")
    return start, end


def period_date_strings(
    available_dates: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp
) -> list[str]:
    in_range = available_dates[(available_dates >= start) & (available_dates <= end)]
    return [d.strftime("%Y-%m-%d") for d in in_range]


def _sliced_spend(input_data, start, end):
    media_spend = input_data.media_spend
    if media_spend is None:
        raise ValueError("media_spend data not available in model")
    if start is not None:
        media_spend = media_spend.sel(time=slice(start.strftime("%Y-%m-%d"), None))
    if end is not None:
        media_spend = media_spend.sel(time=slice(None, end.strftime("%Y-%m-%d")))
    return media_spend


def total_spend(
    input_data, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None
) -> float:
    return float(_sliced_spend(input_data, start, end).sum().values)


def spend_by_channel(
    input_data, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None
) -> dict[str, float]:
    media_spend = _sliced_spend(input_data, start, end)
    return {
        str(ch): float(media_spend.sel(media_channel=ch).sum().values)
        for ch in media_spend.coords["media_channel"].values
    }
