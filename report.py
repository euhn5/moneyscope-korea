"""MoneyScope Korea: 선택 기간의 관측값에 기반한 규칙형 요약 리포트."""
import pandas as pd

NAMES = {"base_rate": "한국 기준금리", "inflation": "전년 동월 대비 물가상승률", "usd_krw": "월평균 원/달러 환율"}


def direction(delta: float) -> str:
    if abs(delta) < 1e-9:
        return "변화가 없었습니다"
    return "상승했습니다" if delta > 0 else "하락했습니다"


def build_report(monthly: pd.DataFrame) -> str:
    """관측된 공통 월의 시작/끝 값을 비교한다. 추론이나 인과관계 주장은 하지 않는다."""
    df = monthly.sort_values("date").dropna(subset=list(NAMES)).copy()
    if len(df) < 2:
        return "선택한 기간의 공통 관측 월이 2개 미만이어서 변화량 리포트를 만들 수 없습니다."
    first, last = df.iloc[0], df.iloc[-1]
    begin, end = first["date"].strftime("%Y-%m"), last["date"].strftime("%Y-%m")
    rate_delta = float(last["base_rate"] - first["base_rate"])
    inflation_delta = float(last["inflation"] - first["inflation"])
    fx_delta = float(last["usd_krw"] - first["usd_krw"])
    fx_pct = (float(last["usd_krw"] / first["usd_krw"] - 1) * 100) if first["usd_krw"] != 0 else float("nan")
    lines = [
        "MoneyScope Korea — 경제지표 자동 분석 리포트",
        f"분석 기간: {begin} ~ {end} (공통 관측 월 {len(df)}개)",
        "",
        f"• 한국 기준금리: {first['base_rate']:.2f}% → {last['base_rate']:.2f}% "
        f"({rate_delta:+.2f}%p). 기간 양끝을 비교하면 {direction(rate_delta)}.",
        f"• 전년 동월 대비 물가상승률: {first['inflation']:.2f}% → {last['inflation']:.2f}% "
        f"({inflation_delta:+.2f}%p). 기간 양끝을 비교하면 {direction(inflation_delta)}.",
        f"• 월평균 원/달러 환율: {first['usd_krw']:,.2f}원 → {last['usd_krw']:,.2f}원 "
        f"({fx_delta:+,.2f}원, {fx_pct:+.2f}%). 기간 양끝을 비교하면 {direction(fx_delta)}.",
        "",
        "해석 시 유의사항",
        "• 위 변화는 두 시점 간 관측값 차이이며, 중간 기간의 변동이나 원인을 설명하지 않습니다.",
        "• 금리와 물가상승률의 차이는 %p, 환율의 상대 변화는 %로 계산했습니다.",
        "• 물가상승률은 CPI 지수의 전년 동월 대비 증가율이며, 물가 수준 자체와 다릅니다.",
        "• 환율은 조회된 일별 매매기준율을 월별 산술평균한 값입니다. 첫 달과 마지막 달은 일부 날짜만 포함될 수 있습니다.",
        "• 각 통계의 발표 시점이 다르며, 데이터가 함께 움직였다고 인과관계가 확인되는 것은 아닙니다.",
        "• 출처: 한국은행 경제통계시스템(ECOS). 자동 생성된 기술통계이며 투자 조언이 아닙니다.",
    ]
    return "\n".join(lines)
