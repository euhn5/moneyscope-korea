"""한국은행 ECOS에서 경제지표를 조회하는 기능만 모은 파일."""
from datetime import date
import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ecos(api_key: str, code: str, frequency: str, start: str, end: str, item: str) -> pd.DataFrame:
    """ECOS 통계 행을 가져온다. 500건씩 페이지를 조회한다."""
    rows = []
    first = 1
    while True:
        last = first + 499
        url = f"{BASE_URL}/{api_key}/json/kr/{first}/{last}/{code}/{frequency}/{start}/{end}/{item}"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            # 요청 URL에 API 키가 있으므로 원본 예외를 화면에 출력하지 않는다.
            raise RuntimeError("ECOS 통신 오류가 발생했습니다. 인터넷 연결과 API 상태를 확인하세요.") from None
        if "StatisticSearch" not in payload:
            result = payload.get("RESULT", {})
            code_value = result.get("CODE", "")
            # ECOS의 정상적인 빈 결과도 오류로 안내해 정확한 조회 조건을 확인하도록 한다.
            raise ValueError(f"ECOS 데이터 조회 실패 ({code_value}): {result.get('MESSAGE', '통계 코드·기간을 확인하세요.')}")
        body = payload["StatisticSearch"]
        page = body.get("row", [])
        if not page:
            break
        rows.extend(page)
        count = int(body.get("list_total_count", len(rows)))
        if len(rows) >= count:
            break
        first = last + 1
    if not rows:
        raise ValueError("조회된 통계 데이터가 없습니다.")
    return pd.DataFrame(rows)


def prepare_series(raw: pd.DataFrame, value_name: str, date_format: str) -> pd.DataFrame:
    frame = raw[["TIME", "DATA_VALUE"]].copy()
    frame.columns = ["date", value_name]
    frame["date"] = pd.to_datetime(frame["date"], format=date_format, errors="coerce")
    frame[value_name] = pd.to_numeric(
        frame[value_name].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    return (frame.dropna(subset=["date", value_name])
            .drop_duplicates(subset=["date"])
            .sort_values("date").reset_index(drop=True))


def load_base_rate(api_key: str, end_month: str) -> pd.DataFrame:
    raw = fetch_ecos(api_key, "722Y001", "M", "202401", end_month, "0101000")
    return prepare_series(raw, "base_rate", "%Y%m")


def load_exchange_daily(api_key: str, end_day: str) -> pd.DataFrame:
    raw = fetch_ecos(api_key, "731Y001", "D", "20240101", end_day, "0000001")
    return prepare_series(raw, "usd_krw", "%Y%m%d")


def load_cpi(api_key: str, end_month: str) -> pd.DataFrame:
    # 2024년의 전년 동월 대비 증가율을 구하려면 2023년부터 필요하다.
    raw = fetch_ecos(api_key, "901Y009", "M", "202301", end_month, "0")
    cpi = prepare_series(raw, "cpi", "%Y%m").set_index("date").asfreq("MS")
    cpi["inflation"] = (cpi["cpi"] / cpi["cpi"].shift(12) - 1) * 100
    return cpi.reset_index()


def load_all(api_key: str):
    today = date.today()
    end_day = today.strftime("%Y%m%d")
    end_month = today.strftime("%Y%m")
    return (load_base_rate(api_key, end_month),
            load_exchange_daily(api_key, end_day),
            load_cpi(api_key, end_month))
