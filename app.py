"""MoneyScope Korea 2.4 — 실제 한국은행 경제지표 통합 대시보드."""
from datetime import date
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from data_loader import load_all
from analysis import combine_monthly, normalized_to_100, compare_to_previous, monthly_changes
from report import build_report
from descriptive_stats import summary_statistics
from period_comparison import compare_periods
from advanced_report import make_advanced_report

st.set_page_config(page_title="MoneyScope Korea", page_icon="📈", layout="wide")
st.title("📈 MoneyScope Korea 2.4")
st.caption("한국은행 ECOS 실제 데이터로 살펴보는 기준금리 · 물가상승률 · 원/달러 환율")

try:
    key = st.secrets["ECOS_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("API 인증키를 찾지 못했습니다. .streamlit/secrets.toml에 ECOS_API_KEY를 설정해 주세요.")
    st.stop()

with st.spinner("한국은행 경제 데이터를 불러오는 중..."):
    try:
        rates, fx_daily, cpi = load_all(key)
        monthly = combine_monthly(rates, fx_daily, cpi)
    except Exception as exc:
        st.error(f"데이터 조회 실패: {exc}")
        st.info("인증키, ECOS 통계 코드 및 인터넷 연결을 확인해 주세요.")
        st.stop()

if monthly.empty:
    st.warning("세 지표가 모두 존재하는 공통 월이 없습니다. 조회 기간을 확인하세요.")
    st.stop()

month_labels = monthly["date"].dt.strftime("%Y-%m").tolist()
start, end = st.sidebar.select_slider(
    "분석 기간 (공통 관측 월)", options=month_labels,
    value=(month_labels[0], month_labels[-1]))
filtered = monthly[monthly["date"].dt.strftime("%Y-%m").between(start, end)].copy()

st.sidebar.caption("출처: 한국은행 경제통계시스템(ECOS)")
st.sidebar.caption("환율은 일별 매매기준율의 월 산술평균입니다.")
st.sidebar.caption("마지막 달은 일부 일별 관측값만 포함될 수 있습니다.")

# 지표 카드에는 '각 지표의 최신 관측'을 사용하여 발표 시차를 숨기지 않는다.
latest_rate = rates.dropna(subset=["base_rate"]).iloc[-1]
latest_fx = fx_daily.dropna(subset=["usd_krw"]).iloc[-1]
valid_cpi = cpi.dropna(subset=["inflation"])

# 최신 관측치 기준 변화량. 서로 다른 발표일을 숨기지 않는다.
rate_delta = compare_to_previous(rates, "base_rate")
fx_delta = compare_to_previous(fx_daily, "usd_krw", percent=True)

# 물가상승률 자체의 전월 변화는 %p 단위로 나타낸다.
# 날짜 인덱스를 월별로 맞춘 후 비교하므로 누락된 달을 무시하지 않는다.
cpi_monthly = cpi.sort_values("date").set_index("date").asfreq("MS")
inflation_delta = None
if len(cpi_monthly) >= 2:
    last_two = cpi_monthly["inflation"].iloc[-2:]
    if last_two.notna().all():
        inflation_delta = last_two.iloc[-1] - last_two.iloc[-2]

c1, c2, c3 = st.columns(3)
c1.metric("한국 기준금리", f"{latest_rate['base_rate']:.2f}%",
          delta=f"{rate_delta:+.2f}%p (전월 대비)" if rate_delta is not None else None,
          delta_color="off")
c1.caption(f"관측 월 {latest_rate['date']:%Y-%m}")
if not valid_cpi.empty:
    cpi_last = valid_cpi.iloc[-1]
    c2.metric("전년 동월 대비 물가상승률", f"{cpi_last['inflation']:.2f}%",
              delta=f"{inflation_delta:+.2f}%p (전월 대비)" if inflation_delta is not None else None,
              delta_color="off")
    c2.caption(f"관측 월 {cpi_last['date']:%Y-%m}")
else:
    c2.metric("전년 동월 대비 물가상승률", "자료 부족")
c3.metric("원/달러 매매기준율", f"{latest_fx['usd_krw']:,.2f}원",
          delta=f"{fx_delta:+.2f}% (이전 관측일 대비)" if fx_delta is not None else None,
          delta_color="off")
c3.caption(f"관측일 {latest_fx['date']:%Y-%m-%d} · 실시간 환율 아님")
st.caption("변화량은 관측 기준: 금리와 물가상승률은 %p, 환율은 이전 거래 관측일 대비 %입니다. 화살표는 좋고 나쁨을 뜻하지 않습니다.")

st.divider()
st.subheader("📊 경제지표 비교")
labels = {"base_rate": "기준금리 (%)", "inflation": "물가상승률 (%, 전년 동월 대비)",
          "usd_krw": "원/달러 환율 (월평균, 원)"}
selected = st.multiselect("비교할 지표", list(labels),
                          default=["base_rate", "inflation"], format_func=lambda key: labels[key])
mode = st.radio("그래프 방식", ["원래 단위", "시작 시점을 100으로 정규화"], horizontal=True)
if selected:
    if mode == "원래 단위" and "usd_krw" in selected and len(selected) > 1:
        st.info("환율은 원 단위이므로 다른 지표와 같은 축에서는 비교가 어렵습니다. 정규화 방식을 추천해요.")
    plotted = (normalized_to_100(filtered, selected) if mode != "원래 단위"
               else filtered[["date"] + selected])
    st.line_chart(plotted.set_index("date"), use_container_width=True)
    if mode != "원래 단위":
        st.caption("정규화는 각 지표의 첫 값을 100으로 맞춘 것입니다. 이는 금리·물가의 경제적 단위가 같다는 뜻은 아닙니다.")
else:
    st.info("그래프에 표시할 지표를 하나 이상 선택해 주세요.")

st.subheader("🔎 금리와 물가상승률의 상관관계")
if len(filtered) >= 3 and filtered["base_rate"].nunique() > 1 and filtered["inflation"].nunique() > 1:
    corr = filtered["base_rate"].corr(filtered["inflation"])
    st.metric("선택 기간의 피어슨 상관계수", f"{corr:.2f}")
else:
    st.info("상관계수를 계산하려면 서로 다른 값이 있는 공통 관측 월이 3개 이상 필요합니다.")
st.caption("상관계수는 인과관계를 뜻하지 않습니다. 추세가 있는 시계열의 수준값 상관계수는 과대해석하면 안 됩니다.")

st.divider()
st.subheader("🧩 월별 변화 상관관계 히트맵")
st.caption("기준금리·물가상승률은 전월 대비 %p 변화, 환율은 전월 대비 % 변화율로 비교합니다. 상관관계는 인과관계를 뜻하지 않습니다.")
changes = monthly_changes(filtered)
if len(changes) >= 3:
    # 상수값이나 결측치가 있을 경우 상관계수가 계산되지 않을 수 있다.
    corr_matrix = changes.corr(min_periods=3)
    valid_columns = [col for col in corr_matrix if pd.notna(corr_matrix.loc[col, col])]
    if len(valid_columns) >= 2:
        view = corr_matrix.loc[valid_columns, valid_columns]
        st.dataframe(view.style.format("{:.2f}").background_gradient(
            cmap="RdBu_r", vmin=-1, vmax=1), use_container_width=True)
        st.caption(f"분석 기간 월별 변화 관측치: 최대 {len(changes)}개. 히트맵은 기술통계이며 예측이나 인과 효과가 아닙니다.")
    else:
        st.info("상관관계 히트맵에 필요한 변동성 있는 지표가 2개 이상이어야 합니다.")
else:
    st.info("히트맵은 월별 변화량이 최소 3개 이상일 때 표시합니다. 분석 기간을 넓혀 주세요.")
with st.expander("월별 변화량 데이터 보기"):
    st.dataframe(changes.reset_index(), hide_index=True, use_container_width=True)

st.divider()
st.subheader("📐 심화 통계 분석")
st.caption("선택한 공통 관측 월을 기준으로 최고·최저 발생 월, 평균, 월별 변화의 표본 표준편차를 계산합니다.")
stat_table = summary_statistics(filtered)
if stat_table.empty:
    st.info("분석할 데이터가 없습니다.")
else:
    st.dataframe(stat_table, hide_index=True, use_container_width=True)
    st.caption("금리와 물가상승률의 월별 변화는 %p, 환율의 월별 변화는 %입니다. "
               "표준편차는 변동 폭을 나타낼 뿐 위험이나 인과관계를 직접 설명하지 않습니다. "
               "변화 표본이 2개 미만이면 계산하지 않습니다.")

st.divider()
st.subheader("📝 자동 경제 분석 리포트")
st.caption("선택한 기간의 시작과 끝 값을 규칙에 따라 비교합니다. 생성형 AI나 경제 예측 모델은 사용하지 않습니다.")
report_text = build_report(filtered)
st.text(report_text)
st.download_button(
    "분석 리포트 TXT 다운로드",
    data=report_text.encode("utf-8-sig"),
    file_name="moneyscope_report.txt",
    mime="text/plain",
)

with st.expander("📋 월별 통합 데이터 보기"):
    st.dataframe(filtered, hide_index=True, use_container_width=True)
st.download_button("선택 기간 실제 데이터 CSV 다운로드",
                   filtered.to_csv(index=False).encode("utf-8-sig"),
                   file_name="moneyscope_actual_monthly.csv", mime="text/csv")

with st.expander("📈 원본 데이터·산출 방식 보기"):
    st.write("**기준금리** — ECOS 722Y001 / 0101000 (월별)")
    st.dataframe(rates, hide_index=True)
    st.write("**환율** — ECOS 731Y001 / 0000001 (일별 매매기준율)")
    st.dataframe(fx_daily, hide_index=True)
    st.write("**소비자물가지수** — ECOS 901Y009 / 0 (월별)")
    st.dataframe(cpi, hide_index=True)
    st.caption("물가상승률 = (이번 달 CPI / 12개월 전 CPI - 1) × 100")

st.warning("공식 지표의 발표 시점이 서로 다릅니다. 월평균 환율의 첫·끝 달은 불완전할 수 있습니다. 투자 판단의 단독 근거로 삼지 마세요.")

# ─────────────────────────────────────────────
# 2.4: 기준금리 변경 월과 전후 환율 탐색
# ─────────────────────────────────────────────
from event_analysis import analyze_rate_fx

st.divider()
st.subheader("🗓️ 기준금리 변경 월과 환율 비교")
st.caption(
    "월별 기준금리가 직전 월과 달라진 월을 자동 탐지합니다. "
    "이는 실제 정책 결정일이 아닙니다. 변경 월의 전월과 다음 달의 "
    "일별 원/달러 매매기준율 월평균을 비교하며, 변경 월은 제외합니다."
)
event_table = analyze_rate_fx(rates, fx_daily)
if event_table.empty:
    st.info("조회된 기간에 기준금리 변경 월을 찾지 못했습니다.")
else:
    choices = event_table["금리 변화 월"].tolist()
    selected_month = st.selectbox("분석할 금리 변경 월", choices, index=len(choices) - 1)
    chosen = event_table.loc[event_table["금리 변화 월"] == selected_month].iloc[0]
    st.write(
        f"**{selected_month}** 기준금리: "
        f"{chosen['전월 기준금리 (%)']:.2f}% → {chosen['변경 월 기준금리 (%)']:.2f}% "
        f"({chosen['기준금리 변화 (%p)']:+.2f}%p)"
    )
    if pd.isna(chosen["전후 환율 변화율 (%)"]):
        st.info("전월 또는 다음 달 환율 자료가 부족하여 전후 비교를 할 수 없습니다.")
    else:
        c_before, c_after, c_pct = st.columns(3)
        c_before.metric("변경 월 전월의 환율 평균", f"{chosen['전월 환율 평균 (원)']:,.2f}원")
        c_after.metric("변경 월 다음 달의 환율 평균", f"{chosen['다음 달 환율 평균 (원)']:,.2f}원")
        c_pct.metric("전후 환율 변화율", f"{chosen['전후 환율 변화율 (%)']:+.2f}%")
        # Plotly를 사용해 축 범위와 한글 라벨을 명확하게 표시한다.
        before_fx = float(chosen["전월 환율 평균 (원)"])
        after_fx = float(chosen["다음 달 환율 평균 (원)"])
        periods = ["변경 전월", "변경 다음 달"]
        values = [before_fx, after_fx]

        fig = go.Figure(
            data=[go.Bar(
                x=periods,
                y=values,
                text=[f"{value:,.2f}원" for value in values],
                textposition="outside",
                marker_color=["#64B5F6", "#FFB74D"],
                hovertemplate="%{x}<extra></extra><br>월평균 환율: %{y:,.2f}원",
            )]
        )
        fig.update_layout(
            title="기준금리 변경 전후 월평균 환율",
            xaxis_title=None,
            yaxis_title="원/달러 환율 (원)",
            yaxis=dict(range=[0, max(values) * 1.18], tickformat=",.0f"),
            height=440,
            margin=dict(l=20, r=20, t=65, b=35),
            showlegend=False,
            bargap=0.5,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"전월 관측일 {int(chosen['전월 환율 관측일수'])}일 / "
            f"다음 달 관측일 {int(chosen['다음 달 환율 관측일수'])}일. "
            "환율이 일별로 발표되므로 주말·휴일은 제외될 수 있습니다. "
            "다음 달이 진행 중이면 월평균은 잠정적인 부분 기간 값입니다."
        )
    with st.expander("전체 금리 변경 월 및 환율 비교표"):
        st.dataframe(event_table, hide_index=True, use_container_width=True)
    st.download_button(
        "금리 변경 월 분석 CSV 다운로드",
        event_table.to_csv(index=False).encode("utf-8-sig"),
        "rate_fx_events.csv", "text/csv",
    )
st.warning(
    "금리 변경 월 탐지는 월별 통계의 변화 시점만 보여줍니다. "
    "환율의 변화가 금리 정책 때문에 발생했다는 뜻은 아닙니다. "
    "미국 금리, 시장 위험 선호, 무역·환율정책 등 여러 요인이 영향을 줄 수 있습니다."
)


# ==========================================
# 2.5 과거 경제 국면 비교
# ==========================================

st.divider()
st.subheader("📊 과거 경제 국면 비교")

st.caption(
    "서로 다른 두 기간의 경제지표를 비교합니다."
)

# 비교 가능한 연도 가져오기
years = sorted(monthly["date"].dt.year.unique().tolist())

col1, col2 = st.columns(2)

with col1:
    year_a = st.selectbox(
        "비교 기간 A",
        years,
        index=0
    )

with col2:
    year_b = st.selectbox(
        "비교 기간 B",
        years,
        index=min(1, len(years) - 1)
    )

# 선택한 연도의 데이터 추출
period_a, period_b = compare_periods(
    monthly,
    f"{year_a}-01-01",
    f"{year_a}-12-31",
    f"{year_b}-01-01",
    f"{year_b}-12-31"
)

# 비교할 경제지표
indicator = st.selectbox(
    "비교할 경제지표",
    ["base_rate", "inflation", "usd_krw"],
    format_func=lambda x: {
        "base_rate": "기준금리",
        "inflation": "물가상승률",
        "usd_krw": "원/달러 환율"
    }[x]
)

# 월 정보 추가
period_a["month"] = period_a["date"].dt.month
period_b["month"] = period_b["date"].dt.month

# 같은 월을 기준으로 데이터 합치기
comparison = pd.merge(
    period_a[["month", indicator]],
    period_b[["month", indicator]],
    on="month",
    how="outer",
    suffixes=("_a", "_b")
).sort_values("month")

comparison = comparison.rename(columns={
    f"{indicator}_a": f"{year_a}년",
    f"{indicator}_b": f"{year_b}년"
})

comparison = comparison.set_index("month")

# 그래프 표시
st.line_chart(comparison)

# 비교 데이터 표
st.subheader("기간별 비교 데이터")
st.dataframe(comparison, use_container_width=True)

st.caption(
    "동일한 달을 기준으로 비교하며, "
    "자료가 없는 달은 빈 값으로 표시합니다."
)

# ==========================================
# 2.5 기간별 상세 통계 비교
# ==========================================

st.subheader("📋 기간별 상세 통계 비교")

def get_period_stats(df, indicator):
    values = df[indicator].dropna()

    if values.empty:
        return None

    return {
        "평균": values.mean(),
        "최고": values.max(),
        "최저": values.min(),
        "시작값": values.iloc[0],
        "종료값": values.iloc[-1],
        "전체 변화량": values.iloc[-1] - values.iloc[0]
    }


stats_a = get_period_stats(period_a, indicator)
stats_b = get_period_stats(period_b, indicator)

if stats_a is not None and stats_b is not None:

    stats_table = pd.DataFrame({
        f"{year_a}년": stats_a,
        f"{year_b}년": stats_b
    })

    st.dataframe(
        stats_table.style.format("{:,.2f}"),
        use_container_width=True
    )

    st.caption(
        "전체 변화량은 종료값에서 시작값을 뺀 값입니다. "
        "기준금리와 물가상승률의 차이는 %p, "
        "환율의 차이는 원 단위입니다."
    )

else:
    st.warning("선택한 기간의 통계 데이터가 부족합니다.")


# ==========================================
# 2.6 심화 경제 분석 리포트
# ==========================================

st.divider()
st.subheader("📑 심화 경제 분석 리포트")

advanced_text = make_advanced_report(
    filtered,
    period_a,
    period_b,
    year_a,
    year_b
)

st.text(advanced_text)

st.download_button(
    "심화 분석 리포트 TXT 다운로드",
    data=advanced_text.encode("utf-8-sig"),
    file_name="moneyscope_advanced_report.txt",
    mime="text/plain"
)