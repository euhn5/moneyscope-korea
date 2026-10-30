"""서로 다른 주기의 지표를 월 단위로 정렬하고 비교하는 함수."""
import pandas as pd


def monthly_exchange(exchange_daily: pd.DataFrame) -> pd.DataFrame:
    """조회된 일별 관측값의 월 산술평균."""
    return (exchange_daily.set_index("date")["usd_krw"]
            .resample("MS").mean().dropna().rename("usd_krw").reset_index())


def combine_monthly(base_rate: pd.DataFrame, exchange_daily: pd.DataFrame,
                    cpi: pd.DataFrame) -> pd.DataFrame:
    exchange_month = monthly_exchange(exchange_daily)
    joined = (base_rate.merge(exchange_month, on="date", how="inner")
              .merge(cpi[["date", "cpi", "inflation"]], on="date", how="inner"))
    return joined.dropna(subset=["base_rate", "usd_krw", "inflation"]).sort_values("date").reset_index(drop=True)


def normalized_to_100(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """첫 관측치를 100으로 맞춰 상대적인 방향을 비교한다."""
    out = df[["date"]].copy()
    for col in columns:
        base = df[col].iloc[0]
        out[col] = df[col] / base * 100 if base != 0 else float("nan")
    return out


def compare_to_previous(frame: pd.DataFrame, col: str, *, percent: bool = False):
    """최신 두 관측값 차이: 비율이면 %, 아니면 원 단위 수치 차이."""
    valid = frame.dropna(subset=[col]).sort_values("date")
    if len(valid) < 2:
        return None
    current, previous = valid[col].iloc[-1], valid[col].iloc[-2]
    if percent:
        return (current / previous - 1) * 100 if previous != 0 else None
    return current - previous


def monthly_changes(frame: pd.DataFrame) -> pd.DataFrame:
    """월 간격을 유지한 변화량: 금리/인플레이션은 %p, 환율은 %."""
    ordered = frame.sort_values("date").set_index("date").asfreq("MS")
    return pd.DataFrame({
        "기준금리 변화 (%p)": ordered["base_rate"].diff(),
        "물가상승률 변화 (%p)": ordered["inflation"].diff(),
        "환율 변화율 (%)": ordered["usd_krw"].pct_change(fill_method=None) * 100,
    }).dropna(how="all")
