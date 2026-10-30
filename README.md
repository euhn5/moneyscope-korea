# 📈 MoneyScope Korea 2.0

한국은행 ECOS API를 사용하는 경제 데이터 분석·시각화 프로젝트입니다.

## 주요 기능
- 실제 기준금리, 전년 동월 대비 물가상승률, 최근 원/달러 매매기준율 표시
- 일별 환율의 월평균 계산 후 월별 지표 결합
- 기간 선택, 지표 선택, 기준점 100 정규화 그래프
- 수준값 피어슨 상관계수 및 CSV 다운로드
- 원본 통계와 산출 방식 확인

## Windows 실행 방법
기존 프로젝트의 **가상환경을 활성화한 뒤 이 폴더로 이동**합니다.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

첫 실행 전, `.streamlit/secrets.toml.example` 파일을 참고해 동일 폴더에 `secrets.toml`을 만듭니다.

```toml
ECOS_API_KEY = "본인_API_인증키"
```

**API 인증키를 GitHub에 업로드하지 마세요.** `.gitignore`에 `secrets.toml`이 제외되어 있습니다.

## 코드 구조
- `app.py`: Streamlit 대시보드 UI
- `data_loader.py`: 한국은행 ECOS 데이터 조회 및 자료형 변환
- `analysis.py`: 월평균 환율 계산, 월별 병합, 정규화
- `backup/app_original.py`: 작업 전 기존 앱 코드 백업 (가상 CSV 필요)

## 통계 출처와 방법
- 기준금리: ECOS `722Y001`, `0101000`, 월별
- 원/미국달러 환율: ECOS `731Y001`, `0000001`, 일별
- 소비자물가지수: ECOS `901Y009`, `0`, 월별
- 물가상승률(%) = `(당월 CPI / 전년 동월 CPI - 1) × 100`
- 환율 월평균: 조회된 일별 관측값의 산술평균. 시작·마지막 달의 자료가 불완전할 수 있음
- 월별 비교는 세 지표가 모두 있는 공통 월만 사용
- 최근 카드의 기준일은 각각 달라질 수 있음

## 참고
- ECOS: https://ecos.bok.or.kr/
- Streamlit: https://docs.streamlit.io/

상관관계는 인과관계가 아닙니다. 이 프로젝트는 학습 목적으로 제작되었습니다.

## 2.1 업데이트
- 최신 관측값 변화량 카드 (금리/물가상승률 %p, 환율 이전 관측일 대비 %)
- 월별 변화량 피어슨 상관관계 히트맵, 데이터 표
- 히트맵은 상관관계이며 인과관계 또는 예측이 아님
