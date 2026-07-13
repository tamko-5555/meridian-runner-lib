import pandas as pd
import pytest

from runner_lib import periods


def _weekly(start, n):
    return pd.DatetimeIndex(pd.date_range(start, periods=n, freq="W-SUN"))


def test_default_period_ends_before_last_month_end():
    # 2025-06-29 まで週次データ → end は 2025-05-31 以前で最も近い日曜
    # ideal_start = 2025-05-31 - 364日 = 2024-06-01 → 実在する最初の日曜 2024-06-02
    dates = _weekly("2023-01-01", 131)  # 〜2025-06-29
    start, end = periods.default_analysis_period(dates)
    assert end == pd.Timestamp("2025-05-25")
    assert start == pd.Timestamp("2024-06-02")
    assert (end - start).days == 357  # 実在日への補正で364日より短くなる(検算済み)


def test_default_period_clamps_to_available_range():
    dates = _weekly("2025-01-05", 26)  # 半年分しかない
    start, end = periods.default_analysis_period(dates)
    assert start == dates.min()  # 1年前が存在しないので最初の日付に補正
    assert end <= dates.max()


def test_period_date_strings():
    dates = _weekly("2024-01-07", 10)
    strings = periods.period_date_strings(dates, dates[2], dates[5])
    assert strings == [d.strftime("%Y-%m-%d") for d in dates[2:6]]


def test_total_and_channel_spend(unfitted_mmm):
    input_data = unfitted_mmm.input_data
    total = periods.total_spend(input_data)
    by_ch = periods.spend_by_channel(input_data)
    assert set(by_ch) == {"ch1", "ch2"}
    assert total == pytest.approx(sum(by_ch.values()))

    dates = pd.to_datetime(input_data.time.values)
    partial = periods.total_spend(input_data, start=dates[10], end=dates[20])
    assert 0 < partial < total
