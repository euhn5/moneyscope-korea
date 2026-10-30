"""월별 기준금리 변화와 주변 월의 원/달러 환율을 기술적으로 비교한다.

중요: 월별 기준금리 자료만으로 실제 금융통화위원회 의결 날짜를 알 수 없다.
또한 금리 변화가 환율 변화를 유발했다고 해석할 수 없다.
"""
import pandas as pd


def detect_rate_change_months(rates: pd.DataFrame) -> pd.DataFrame:
    """직전 달과 기준금리가 다른 월을 찾는다. 누락 월은 연결하지 않는다."""
    ordered = (rates[["date", "base_rate"]].dropna()
               .drop_duplicates("date").sort_values("date")
               .set_index("date").asfreq("MS"))
    previous = ordered["base_rate"].shift(1)
    changes = ordered["base_rate"] - previous
    result = pd.DataFrame({
        "event_month": ordered.index,
        "previous_rate": previous.values,
        "current_rate": ordered["base_rate"].values,
        "change_pp": changes.values,
    })
    return result.loc[result["change_pp"].notna() & result["change_pp"].ne(0)].reset_index(drop=True)


def analyze_rate_fx(rates: pd.DataFrame, fx_daily: pd.DataFrame) -> pd.DataFrame:
    """금리 변화 월의 전월과 다음 달 환율 월평균을 비교한다.

    이벤트가 발생한 월은 비교 대상에서 제외한다. 두 월 모두 존재하는 경우만 계산.
    """
    events = detect_rate_change_months(rates)
    fx = fx_daily[["date", "usd_krw"]].dropna().copy()
    fx["month"] = fx["date"].dt.to_period("M")
    grouped = fx.groupby("month")["usd_krw"].agg(["mean", "count"])
    records = []
    for e in events.itertuples(index=False):
        month = pd.Period(e.event_month, freq="M")
        before = month - 1
        after = month + 1
        before_mean = grouped.loc[before, "mean"] if before in grouped.index else float("nan")
        after_mean = grouped.loc[after, "mean"] if after in grouped.index else float("nan")
        before_count = int(grouped.loc[before, "count"]) if before in grouped.index else 0
        after_count = int(grouped.loc[after, "count"]) if after in grouped.index else 0
        change = ((after_mean / before_mean - 1) * 100
                  if pd.notna(before_mean) and pd.notna(after_mean) and before_mean != 0
                  else float("nan"))
        records.append({
            "금리 변화 월": month.strftime("%Y-%m"),
            "전월 기준금리 (%)": e.previous_rate,
            "변경 월 기준금리 (%)": e.current_rate,
            "기준금리 변화 (%p)": e.change_pp,
            "전월 환율 평균 (원)": before_mean,
            "다음 달 환율 평균 (원)": after_mean,
            "전후 환율 변화율 (%)": change,
            "전월 환율 관측일수": before_count,
            "다음 달 환율 관측일수": after_count,
        })
    return pd.DataFrame(records)
