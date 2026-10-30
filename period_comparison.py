import pandas as pd


def compare_periods(df, start_a, end_a, start_b, end_b):
    """두 기간의 경제지표 데이터를 반환한다."""

    period_a = df[
        (df["date"] >= pd.to_datetime(start_a))
        & (df["date"] <= pd.to_datetime(end_a))
    ].copy()

    period_b = df[
        (df["date"] >= pd.to_datetime(start_b))
        & (df["date"] <= pd.to_datetime(end_b))
    ].copy()

    return period_a, period_b