# Week 6 - PCSE 프레임워크를 활용한 WOFOST 작물 시뮬레이션

스마트 온실 모델링 이론과 개발 실습 | CNU 2025

## 수업 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PCSE 프레임워크                              │
│                   (Python Crop Simulation Environment)               │
│                                                                     │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌──────────────┐  │
│  │ OpenMeteo  │   │ 작물 파라 │   │ 토양/사이트│   │  재배관리    │  │
│  │ 기상 API   │   │ (벼/대두) │   │            │   │ (파종~수확)  │  │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘   └──────┬───────┘  │
│        └───────────────┬┴──────────────┘                 │          │
│                        │                                 │          │
│                ┌───────▼─────────┐                       │          │
│                │  WOFOST 모델    │◄──────────────────────┘          │
│                │  7.2 / 7.3 / 8.1│                                  │
│                └───────┬─────────┘                                  │
│                        │                                            │
│                ┌───────▼─────────┐                                  │
│                │  시뮬레이션 결과  │                                  │
│                │ DVS, LAI, TAGP  │                                  │
│                │ TWSO (수량)     │                                  │
│                └───────┬─────────┘                                  │
└────────────────────────┼────────────────────────────────────────────┘
                         │
            ┌────────────▼────────────┐
            │      검증 (Validation)   │
            │  Scatter Plot + RMSE/R²  │
            └────────────┬────────────┘
                         │
          ┌──────────────▼──────────────┐
          │   농촌진흥청 공공데이터 API   │
          │  ┌────────┐   ┌──────────┐  │
          │  │벼 작황  │   │두류 작황  │  │
          │  │9회차 수량│   │4회차 수량 │  │
          │  └────────┘   └──────────┘  │
          └─────────────────────────────┘
```

## 실습 과제 구조

```
  과제 A (기초)              과제 B (응용)
  환경 설정 &                파종일 변경
  기본 시뮬레이션 실행       → 수량 민감도 분석
       │                         │
       ▼                         ▼
  과제 C (심화)              과제 D (심화)
  벼 실측 데이터로           두류 API 직접 수집
  WOFOST 검증                → WOFOST 대두 검증
  (data/ CSV 활용)           → 벼 결과와 비교 고찰
```

## 빠른 시작

```bash
# 1. 클론
git clone https://github.com/vlfrmfla/class_smartgreenhousemodeling.git
cd class_smartgreenhousemodeling

# 2. uv 설치 (없다면)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 의존성 설치
uv sync

# 4. 벼 시뮬레이션 실행
uv run python run_pcse_example.py
```

## 강의자료

브라우저에서 `lecture.html`을 열면 됩니다.

## 파일 구조

```
├── lecture.html                  # 강의용 HTML (브라우저에서 열기)
│
├── 시뮬레이션 스크립트
│   ├── run_pcse_example.py       # 기본 예제: 대전 벼
│   ├── run_compare_versions.py   # WOFOST 7.2/7.3/8.1 버전 비교
│   ├── run_validation.py         # 실측 데이터와 scatter + RMSE/R²
│   ├── run_growth_comparison.py  # 시계열 + 생육단계별 비교
│   └── fetch_rda_data.py         # 농진청 API 호출 유틸
│
├── data/                         # 데이터
│   ├── rda_yield_2017_2024.csv       # 벼 9회차 수량 (606건)
│   ├── rda_biomass_2017_2024.csv     # 벼 8회차 건물중
│   ├── rda_round02~07_*.csv          # 벼 2~7회차 생육
│   ├── rda_planting_2017_2024.csv    # 벼 1회차 파종/이앙
│   ├── sim_yield.csv                 # WOFOST 결과 (7지점x5년)
│   ├── weather/                      # 기상 CSV (7개 지점, 2015~2025)
│   ├── code_areas.json               # 벼 지역코드 매핑
│   └── code_species.json             # 벼 품종코드 매핑
│
├── sim_fig/                      # 그래프 출력
│   ├── result_rice_daejeon_2025.png
│   ├── result_version_comparison.png
│   ├── result_validation_scatter.png
│   ├── scatter_yield.png
│   ├── scatter_year_region.png
│   └── timeseries_daejeon_2023.png
│
├── pyproject.toml                # 프로젝트 의존성 (uv)
└── uv.lock                      # 의존성 잠금 파일
```

## 주요 API

| API | 용도 | 신청 |
|-----|------|------|
| [OpenMeteo](https://open-meteo.com/) | 기상 데이터 (자동 연동) | 불필요 |
| [벼 작황 (data.go.kr)](https://www.data.go.kr/data/15064971/openapi.do) | 벼 실측 수량 | 무료 신청 |
| [두류 작황 (data.go.kr)](https://www.data.go.kr/data/15065006/openapi.do) | 대두 실측 수량 (과제 D) | 무료 신청 |
