# Week 6 — PCSE/WOFOST 작물 시뮬레이션 실습

스마트 온실 모델링 이론과 개발 실습 | CNU 2026 spring

---

## 수업 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PCSE 프레임워크                              │
│                   (Python Crop Simulation Environment)              │
│                                                                     │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌──────────────┐   │
│  │ OpenMeteo │   │ 작물 파라  │   │ 토양/사이트│   │  재배관리     │   │
│  │ 기상 API  │   │ (벼/대두) │   │             │   │ (파종~수확)  │   │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘   └──────┬───────┘   │
│        └───────────────┬┴──────────────┘                 │          │
│                        │                                 │          │
│                ┌───────▼─────────┐                       │          │
│                │  WOFOST 모델    │◄──────────────────────┘          │
│                │  7.2 / 7.3 / 8.1│                                  │
│                └───────┬─────────┘                                  │
│                        │                                            │
│                ┌───────▼─────────┐                                  │
│                │  시뮬레이션 결과 │                                  │
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
          │   농촌진흥청 공공데이터 API  │
          │  ┌────────┐   ┌──────────┐  │
          │  │벼 작황 │   │두류 작황 │  │
          │  │9회차   │   │4회차     │  │
          │  └────────┘   └──────────┘  │
          └─────────────────────────────┘
```

이 실습은 크게 두 부분으로 구성됩니다.

1. **벼 시뮬레이션 체험**: 제공된 데이터로 PCSE/WOFOST를 돌리고 실측과 비교
2. **두류 직접 수집**: 공공데이터 API로 대두 실측 + 기상을 직접 받아 분석

아래 순서대로 따라오면 됩니다.

---

## 1단계 — 환경 설정

### 1-1. 저장소 클론

```bash
git clone https://github.com/vlfrmfla/class_smartgreenhousemodeling.git
cd class_smartgreenhousemodeling/dev/week6_PCSE
```

### 1-2. `uv` 설치 (처음 사용 시)

macOS / Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### 1-3. 의존성 설치

```bash
uv sync
```

`.venv/` 가상환경이 생성되고 PCSE, matplotlib, pandas 등이 설치됩니다.

---

## 2단계 — 기본 시뮬레이션 (대전, 벼, 2025)

```bash
uv run python run_pcse_example.py
```

**결과물**: `sim_fig/result_rice_daejeon_2025.png`

발육단계(DVS), 엽면적지수(LAI), 기관별 건물중, 총 건물중(TAGP) 4개 그래프가 생성됩니다. 콘솔에 출현일·개화일·성숙일·수확일과 수량(TWSO)이 함께 출력됩니다.

**체크**: DVS가 0→1(개화)→2(성숙) 로 증가하고, LAI가 중반에 피크 후 감소하는지 확인.

---

## 3단계 — WOFOST 버전 비교 (7.2 / 7.3 / 8.1)

```bash
uv run python run_compare_versions.py
```

**결과물**: `sim_fig/result_version_comparison.png`

같은 조건(대전, 벼)을 세 버전으로 각각 시뮬레이션해 DVS·LAI·TAGP·TWSO 시계열과 수량 바 차트를 비교합니다.

**체크**: 동일 입력이어도 모델 버전에 따라 수량이 어떻게 달라지는지 관찰.

---

## 4단계 — 벼 실측 데이터 검증 (제공된 데이터)

저장소에 포함된 농촌진흥청 벼 작황 데이터(`data/rda_*.csv`, 2017~2024) 와 WOFOST 시뮬레이션을 비교합니다.

### 4-1. 시계열 & 회차별 생육 비교

```bash
uv run python run_growth_comparison.py
```

**결과물**:
- `sim_fig/scatter_yield.png` — 지역×연도 실측 vs 시뮬 수량
- `sim_fig/timeseries_daejeon_2023.png` — 대전 2023년 시계열 + 회차별 실측점
- `sim_fig/scatter_year_region.png` — 연도·지역별 상세 비교

### 4-2. RMSE / R² 검증 리포트

```bash
uv run python run_validation.py
```

**결과물**: `sim_fig/result_validation_scatter.png` + `data/validation_result.csv`

시뮬레이션 결과(`data/sim_yield.csv`)가 없으면 자동 생성합니다 (7지점×5년, 5~10분 소요). 이미 있으면 바로 scatter plot + RMSE/R² 계산.

**체크**: `sim_fig/` 의 이미지들을 수업자료와 비교하며 결과를 해석해 보세요.

---

## 5단계 — 공공데이터 API 키 발급 (두류 수집 준비)

5단계부터는 학생이 직접 API를 호출해 데이터를 받습니다.

1. 공공데이터포털 가입: <https://www.data.go.kr>
2. **두류 작황** API에 "활용신청" 클릭 (무료, 대부분 즉시 승인)
   - <https://www.data.go.kr/data/15065006/openapi.do>
3. 마이페이지 → 오픈API → 인증키에서 **Decoding 키**를 복사
4. [fetch_rda_data_bean.py](fetch_rda_data_bean.py) 파일 상단의 `SERVICE_KEY` 값을 본인 키로 교체

```python
SERVICE_KEY = "여기에_본인_Decoding_키_붙여넣기"
```

---

## 6단계 — 두류 실측 데이터 수집

```bash
uv run python fetch_rda_data_bean.py
```

**생성 파일** (`data/` 폴더):
- `bean_code_species.json` — 품종코드 매핑 (만리콩, 대원콩 등 20종)
- `bean_code_areas.json` — 시험 지역코드 매핑 (수원, 밀양, 나주 등 11곳)
- `bean_round01_2017_2025.csv` — 1회차: 파종기, 출현일
- `bean_round02_2017_2025.csv` — 2회차: 초장, 분지수, 개화기
- `bean_round03_2017_2025.csv` — 3회차: 협수, 립수, 건물중
- `bean_round04_2017_2025.csv` — 4회차: 수량, 백립중
- `bean_cultivation_2017_2025.csv` — 재배관리 정보

**소요 시간**: API 호출 약 50회, 1~2분.

---

## 7단계 — 두류 지역 기상 데이터 수집

두류 시험 지역 11곳의 일별 기상 데이터를 OpenMeteo(무료, 키 불필요) 에서 받아옵니다. 기간은 2015년부터 현재까지입니다.

```bash
uv run python fetch_weather_bean.py
```

**생성 파일**: `data/weather/weather_{지역명}_{lat}_{lon}.csv` (최대 11개)

### ⚠️ Rate limit 안내 — 여러 번 실행이 필요할 수 있습니다

OpenMeteo archive API는 IP당 요청 수 제한(HTTP 429) 이 있어 한 번에 11개 지역을 모두 받지 못할 수 있습니다. 스크립트는 아래처럼 동작합니다.

- 지역 간 **18초 대기**, 실패 시 **5회 재시도** (15→30→45→60→75초)
- **성공한 파일은 다음 실행에서 `이미 존재, 건너뜀` 으로 표시**되어 이어받기 가능
- 끝에 실패한 지역 목록이 출력됩니다

**권장**: 한 번 실행한 뒤 실패 목록이 있으면 **5~10분 쉬었다가 다시 실행**하세요. 2~3회 반복하면 대부분 11개 지역을 모두 받을 수 있습니다.

```bash
# 1차 실행
uv run python fetch_weather_bean.py

# (실패 지역이 있으면 5~10분 대기)

# 2차 실행 - 성공한 건 건너뛰고 실패분만 재시도
uv run python fetch_weather_bean.py
```

---

## 8단계 — 두류 데이터 분석 (Jupyter Notebook)

[bean_data_analysis.ipynb](bean_data_analysis.ipynb) 를 VS Code 또는 Jupyter Lab에서 열고, 각 셀을 **Shift+Enter** 로 순서대로 실행합니다.

```bash
# Jupyter Lab 사용 시
uv run jupyter lab bean_data_analysis.ipynb
```

VS Code에서는 `.ipynb` 파일을 열고 커널을 `.venv/bin/python` 으로 선택하면 됩니다.

**셀 구성**:
1. 데이터 로드 (CSV 5개 + JSON 2개)
2. 재배관리 데이터 구조 확인
3. 연도/지역/품종별 분포
4. `ctvt1`~`ctvt8` 컬럼 내용 확인
5. 회차별 `exam` 컬럼 요약
6. 회차별 `head()` 직접 확인
7. **결측률 시각화** (빨강 >50%, 노랑 >20%, 초록 양호)
8. **파종일(DOY) 분포** — 연도별 scatter + 지역별 boxplot
9. **파종일 vs 생육지표** — 초장/수량/협수 scatter (색상=연도)
10. **품종별 수량 boxplot**

각 셀 결과를 관찰하면서 주석을 달아보세요.

---

## 파일 구조

```
week6_PCSE/
├── README.md                    ← 지금 읽고 있는 파일
├── lecture.html                 ← 강의자료 (브라우저에서 열기)
│
├── 시뮬레이션 스크립트
│   ├── run_pcse_example.py           (2단계) 기본 시뮬
│   ├── run_compare_versions.py       (3단계) 버전 비교
│   ├── run_growth_comparison.py      (4-1단계) 시계열 비교
│   └── run_validation.py             (4-2단계) RMSE/R² 검증
│
├── API 수집 스크립트
│   ├── fetch_rda_data_bean.py        (6단계) 두류 작황 수집
│   ├── fetch_weather_bean.py         (7단계) 두류 지역 기상 수집
│   └── fetch_rda_data_rice_and_sim.py  벼 수집 (참고용)
│
├── 분석 노트북
│   └── bean_data_analysis.ipynb      (8단계) 두류 데이터 분석
│
├── data/
│   ├── rda_*.csv                    벼 실측 (제공됨)
│   ├── code_areas.json              벼 지역코드
│   ├── code_species.json            벼 품종코드
│   ├── weather/weather_{벼지역}*.csv  벼 지역 기상 (제공됨, 7개)
│   ├── bean_*                       두류 실측 (학생이 수집)     ← .gitignore
│   └── weather/weather_{두류지역}*.csv 두류 지역 기상 (학생이 수집) ← .gitignore
│
├── sim_fig/                     그래프 출력 (.gitignore)
│
├── pyproject.toml
└── uv.lock
```

---

## 사용 API 요약

| API | 용도 | 신청 | 키 필요 |
|-----|------|------|---------|
| [OpenMeteo](https://open-meteo.com/) | 기상 데이터 | 자동 연동 | 아니오 |
| [두류 작황 (data.go.kr)](https://www.data.go.kr/data/15065006/openapi.do) | 두류 실측 | 무료 | 예 |

---

## 자주 묻는 질문

**Q. `uv sync` 에서 에러가 납니다.**
→ Python 3.10 이상이 필요합니다. `uv python install 3.12` 후 다시 시도하세요.

**Q. 매번 `uv run` 을 붙이는 게 귀찮습니다.**
→ `source .venv/bin/activate` (macOS/Linux) 또는 `.venv\Scripts\activate` (Windows) 로 가상환경을 활성화하면 이후 `python run_xxx.py` 로 실행 가능.

**Q. OpenMeteo rate limit(429)이 자주 걸립니다.**
→ 정상입니다. 7단계 설명대로 여러 번 나눠 실행하세요. 매 실행마다 실패분만 자동으로 이어받습니다.

**Q. 한글 폰트가 깨져요.**
→ macOS/Windows는 시스템 폰트 자동 설정됩니다. Linux는 NanumGothic 설치: `sudo apt install fonts-nanum`

**Q. `bean_data_analysis.ipynb` 에서 FileNotFoundError가 뜹니다.**
→ 6단계(두류 수집)를 먼저 실행했는지 확인하세요.

---

## 참고

- PCSE 공식 문서: <https://pcse.readthedocs.io/>
- WOFOST 모델 설명: <https://www.wur.nl/en/research-results/research-institutes/environmental-research/facilities-tools/software-models-and-databases/wofost.htm>
- OpenMeteo Historical API: <https://open-meteo.com/en/docs/historical-weather-api>
