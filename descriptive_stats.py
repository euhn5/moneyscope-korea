"""MoneyScope Korea 2.3 — 월별 지표 기술통계."""
import pandas as pd


def summary_statistics(monthly: pd.DataFrame) -> pd.DataFrame:
    """공통 관측 월에 대한 요약. 변동성은 월별 변화의 표본 표준편차."""
    indicators = [
        ("한국 기준금리", "base_rate", "%", "%p"),
        ("물가상승률 (전년 동월 대비)", "inflation", "%", "%p"),
        ("월평균 원/달러 환율", "usd_krw", "원", "%"),
    ]
    df = monthly.sort_values("date").drop_duplicates("date").copy()
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").asfreq("MS")
    rows = []
    for name, column, unit, change_unit in indicators:
        s = pd.to_numeric(df[column], errors="coerce").dropna()
        if s.empty:
            continue
        # 월별 자료의 실제 인접 월 사이 변화만 사용 (결측 월을 건너뛰지 않음).
        full = pd.to_numeric(df[column], errors="coerce")
        changes = (full.pct_change(fill_method=None) * 100 if column == "usd_krw"
                   else full.diff()).replace([float("inf"), -float("inf")], float("nan")).dropna()
        rows.append({
            "지표": name,
            "시작값": f"{s.iloc[0]:,.2f}{unit}",
            "종료값": f"{s.iloc[-1]:,.2f}{unit}",
            "평균": f"{s.mean():,.2f}{unit}",
            "최고": f"{s.max():,.2f}{unit} ({s.idxmax():%Y-%m})",
            "최저": f"{s.min():,.2f}{unit} ({s.idxmin():%Y-%m})",
            "월별 변화 표준편차": (f"{changes.std(ddof=1):,.2f}{change_unit}"
                              if len(changes) >= 2 else "자료 부족"),
            "관측 월 수": len(s),
            "변화 관측 수": len(changes),
        })
    return pd.DataFrame(rows)
