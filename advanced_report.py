
import pandas as pd


def make_advanced_report(df, period_a, period_b, year_a, year_b):
    """경제지표의 상세 통계와 두 기간의 비교 리포트 생성"""

    indicators = {
        "base_rate": ("한국 기준금리", "%", "%p"),
        "inflation": ("물가상승률", "%", "%p"),
        "usd_krw": ("원/달러 환율", "원", "원")
    }

    lines = [
        "MoneyScope Korea — 심화 경제 분석 리포트",
        "=" * 45,
        "",
        "1. 선택 기간의 상세 통계",
        ""
    ]

    df = df.sort_values("date")

    for col, (name, unit, change_unit) in indicators.items():
        data = df[["date", col]].dropna()

        if data.empty:
            lines.append(f"{name}: 데이터 없음")
            continue

        maximum = data.loc[data[col].idxmax()]
        minimum = data.loc[data[col].idxmin()]

        lines.append(f"[{name}]")
        lines.append(f"평균: {data[col].mean():,.2f}{unit}")
        lines.append(
            f"최고: {maximum[col]:,.2f}{unit} "
            f"({maximum['date']:%Y-%m})"
        )
        lines.append(
            f"최저: {minimum[col]:,.2f}{unit} "
            f"({minimum['date']:%Y-%m})"
        )

        # 월별 변화의 표본 표준편차
        monthly_data = data.set_index("date")[col].asfreq("MS")

        if col == "usd_krw":
            changes = monthly_data.pct_change(
                fill_method=None
            ) * 100
            volatility_unit = "%"
        else:
            changes = monthly_data.diff()
            volatility_unit = "%p"

        volatility = changes.dropna().std()

        if pd.notna(volatility):
            lines.append(
                f"월별 변화량 표준편차: "
                f"{volatility:.2f}{volatility_unit}"
            )
        else:
            lines.append("월별 변화량 표준편차: 자료 부족")

        lines.append("")

    lines.extend([
        "2. 과거 경제 국면 비교",
        f"비교 기간 A: {year_a}년",
        f"비교 기간 B: {year_b}년",
        ""
    ])

    for col, (name, unit, change_unit) in indicators.items():

        a = period_a[col].dropna()
        b = period_b[col].dropna()

        lines.append(f"[{name}]")
        lines.append(
            f"관측 개월 수: {year_a}년 {len(a)}개월, "
            f"{year_b}년 {len(b)}개월"
        )

        if a.empty or b.empty:
            lines.append("비교할 데이터가 부족합니다.")
            lines.append("")
            continue

        avg_a = a.mean()
        avg_b = b.mean()
        difference = avg_b - avg_a

        lines.append(f"{year_a}년 평균: {avg_a:,.2f}{unit}")
        lines.append(f"{year_b}년 평균: {avg_b:,.2f}{unit}")
        lines.append(
            f"평균 차이({year_b}-{year_a}): "
            f"{difference:+,.2f}{change_unit}"
        )

        if len(a) < 12 or len(b) < 12:
            lines.append(
                "주의: 일부 기간의 관측 월이 12개월보다 적습니다."
            )

        lines.append("")

    lines.extend([
        "3. 분석 시 유의사항",
        "- 본 리포트는 관측값에 대한 기술통계입니다.",
        "- 지표 간 인과관계를 입증하거나 미래를 예측하지 않습니다.",
        "- 환율은 일별 관측값을 월평균으로 변환했습니다.",
        "- 각 지표의 발표 시점과 관측 기간이 다를 수 있습니다.",
        "- 출처: 한국은행 경제통계시스템(ECOS)"
    ])

    return "\n".join(lines)
