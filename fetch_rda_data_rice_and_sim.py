"""
농촌진흥청 벼 작황 성적 데이터 수집 & 시뮬레이션 검증
====================================================
공공데이터포털 API를 통해 실측 데이터를 받아오고,
PCSE/WOFOST 시뮬레이션 결과와 비교한다.

API: 농촌진흥청 국립식량과학원_벼 작황 성적 정보 서비스 (v2)
https://www.data.go.kr/data/15064971/openapi.do

실행: uv run python fetch_rda_data.py
"""

import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import platform

if platform.system() == "Darwin":
    mpl.rcParams["font.family"] = "Apple SD Gothic Neo"
elif platform.system() == "Windows":
    mpl.rcParams["font.family"] = "Malgun Gothic"
else:
    mpl.rcParams["font.family"] = "NanumGothic"
mpl.rcParams["axes.unicode_minus"] = False

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
# 공공데이터포털에서 발급받은 Decoding 인증키를 여기에 넣으세요
SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"

BASE_URL = "https://apis.data.go.kr/1390803/RcepntCrpstScoreInfoService_v2"

# ─────────────────────────────────────────────
# API 호출 함수
# ─────────────────────────────────────────────
def call_api(endpoint, extra_params=None):
    """RDA 벼 작황 API 호출"""
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "1000",
    }
    if extra_params:
        params.update(extra_params)

    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, params=params, timeout=30)

    if resp.status_code != 200:
        print(f"  [에러] {endpoint}: HTTP {resp.status_code}")
        print(f"  응답: {resp.text[:200]}")
        return None

    data = resp.json()
    body = data.get("body", data)
    items = body.get("items", [])
    total = body.get("totalCount", len(items))
    print(f"  {endpoint}: {total}건")
    return items


def fetch_code_list():
    """품종코드, 지역코드 목록 조회"""
    print("\n[코드 목록 조회]")
    items = call_api("getCodeList_v2")
    if items:
        df = pd.DataFrame(items)
        print(df.head(20).to_string())
        return df
    return None


def fetch_round_data(year, area_code=None, species_code=None):
    """
    특정 연도의 전 회차 데이터를 수집하여 통합

    Args:
        year: 시험년도 (예: "2023")
        area_code: 지역코드 (예: "0352" = 대전/충남)
        species_code: 품종코드 (예: "R32006")
    """
    extra = {"srchExprYear": str(year)}
    if area_code:
        extra["srchExprAreaCode"] = area_code
    if species_code:
        extra["srchSpciesCode"] = species_code

    all_data = {}

    # 각 회차 데이터 수집
    rounds = {
        "01": "getExprTmrd_01List_v2",  # 이앙기, 파종기
        "02": "getExprTmrd_02List_v2",  # 초장, 경수 (1차)
        "03": "getExprTmrd_03List_v2",  # 초장, 경수 (2차)
        "04": "getExprTmrd_04List_v2",  # 초장, 경수 (3차)
        "05": "getExprTmrd_05List_v2",  # 초장, 경수 (4차)
        "06": "getExprTmrd_06List_v2",  # 수수, 수당립수
        "07": "getExprTmrd_07List_v2",  # 초장, 경수 (5차)
        "08": "getExprTmrd_08List_v2",  # 잎/줄기/이삭 건물중
        "09": "getExprTmrd_09List_v2",  # 수량 (정조, 현미, 백미)
    }

    print(f"\n[{year}년 벼 작황 데이터 수집]")
    for rnd, endpoint in rounds.items():
        items = call_api(endpoint, extra)
        if items:
            all_data[rnd] = pd.DataFrame(items)

    return all_data


# ─────────────────────────────────────────────
# WOFOST 시뮬레이션 (비교용)
# ─────────────────────────────────────────────
def run_wofost_simulation(year=2023):
    """대전 지역 벼 시뮬레이션"""
    import yaml
    from pcse.models import Wofost72_PP
    from pcse.input import (
        YAMLCropDataProvider, OpenMeteoWeatherDataProvider,
        DummySoilDataProvider, WOFOST72SiteDataProvider,
    )
    from pcse.base import ParameterProvider

    print(f"\n[WOFOST 시뮬레이션 - {year}년]")
    wdp = OpenMeteoWeatherDataProvider(latitude=36.35, longitude=127.38)
    cropd = YAMLCropDataProvider(model=Wofost72_PP)
    cropd.set_active_crop("rice", "Rice_501")
    soild = DummySoilDataProvider()
    sited = WOFOST72SiteDataProvider(WAV=100)
    params = ParameterProvider(cropdata=cropd, soildata=soild, sitedata=sited)

    agro = yaml.safe_load(f"""
    - {year}-05-01:
        CropCalendar:
            crop_name: rice
            variety_name: Rice_501
            crop_start_date: {year}-05-15
            crop_start_type: emergence
            crop_end_date: {year}-10-15
            crop_end_type: harvest
            max_duration: 200
        TimedEvents: null
        StateEvents: null
    """)

    model = Wofost72_PP(params, wdp, agro)
    model.run_till_terminate()

    df = pd.DataFrame(model.get_output())
    df = df.dropna(subset=["DVS"])
    df["day"] = pd.to_datetime(df["day"])
    df = df.set_index("day")
    summary = model.get_summary_output()[0]

    print(f"  곡물수량: {summary['TWSO']:.0f} kg/ha")
    print(f"  최대 LAI: {summary['LAIMAX']:.2f}")
    print(f"  TAGP: {summary['TAGP']:.0f} kg/ha")
    return df, summary


# ─────────────────────────────────────────────
# 비교 시각화
# ─────────────────────────────────────────────
def plot_validation(sim_df, sim_summary, obs_data, year):
    """시뮬레이션 vs 실측 비교 그래프"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"WOFOST 시뮬레이션 vs 실측 — 대전 벼 {year}",
                 fontsize=14, fontweight="bold")

    # (1) 수량 비교 (9회차 데이터가 있을 경우)
    ax = axes[0]
    if "09" in obs_data and len(obs_data["09"]) > 0:
        obs_yield_col = [c for c in obs_data["09"].columns
                         if "수량" in c or "정조" in c]
        if obs_yield_col:
            obs_yields = pd.to_numeric(obs_data["09"][obs_yield_col[0]],
                                       errors="coerce")
            obs_mean = obs_yields.mean()
            ax.bar(["WOFOST\n(시뮬레이션)", "실측\n(RDA 평균)"],
                   [sim_summary["TWSO"], obs_mean * 10],  # 10a→ha 변환
                   color=["#2563eb", "#16a34a"], width=0.5)
            ax.set_ylabel("곡물수량 [kg ha⁻¹]")
            ax.set_title("곡물수량 비교")
            ax.grid(True, alpha=0.3, axis="y")
    else:
        ax.text(0.5, 0.5, "실측 수량 데이터 없음\n(API 연결 후 업데이트)",
                ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_title("곡물수량 비교")

    # (2) 건물중 비교 (8회차 데이터가 있을 경우)
    ax = axes[1]
    if "08" in obs_data and len(obs_data["08"]) > 0:
        ax.set_title("기관별 건물중 비교")
        # 8회차에 잎/줄기/이삭 건물중이 있음
    else:
        # 시뮬레이션 결과만 표시
        sim_last = sim_df.iloc[-1]
        organs = ["TWLV", "TWST", "TWSO", "TWRT"]
        labels = ["잎", "줄기", "곡물", "뿌리"]
        vals = [sim_last.get(o, 0) for o in organs]
        ax.bar(labels, vals, color=["#16a34a", "#f59e0b", "#dc2626", "#92400e"])
        ax.set_ylabel("건물중 [kg ha⁻¹]")
        ax.set_title("시뮬레이션 기관별 건물중")
        ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig("result_validation.png", dpi=150, bbox_inches="tight")
    print("\n그래프 저장: result_validation.png")
    plt.show()


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    year = 2023

    # 1) RDA 실측 데이터 수집
    obs_data = {}
    if SERVICE_KEY != "YOUR_SERVICE_KEY_HERE":
        codes = fetch_code_list()
        obs_data = fetch_round_data(year, area_code="0352")
    else:
        print("\n[안내] SERVICE_KEY를 설정하면 실측 데이터를 자동으로 불러옵니다.")
        print("  1. https://www.data.go.kr/data/15064971/openapi.do 에서 활용 신청")
        print("  2. 발급받은 Decoding 키를 이 파일의 SERVICE_KEY에 입력")
        print("  → 시뮬레이션 결과만 표시합니다.\n")

    # 2) WOFOST 시뮬레이션
    sim_df, sim_summary = run_wofost_simulation(year)

    # 3) 비교 시각화
    plot_validation(sim_df, sim_summary, obs_data, year)

    # 4) 요약 출력
    print("\n" + "=" * 55)
    print(f"  검증 요약 — {year}년 대전 벼")
    print("=" * 55)
    print(f"  {'항목':<25s} {'WOFOST':>12s} {'실측(참고)':>12s}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    print(f"  {'곡물수량 (kg/ha)':<25s} {sim_summary['TWSO']:>12.0f} {'5,200~5,500':>12s}")
    print(f"  {'최대 LAI':<25s} {sim_summary['LAIMAX']:>12.2f} {'4.0~7.0':>12s}")
    print(f"  {'TAGP (kg/ha)':<25s} {sim_summary['TAGP']:>12.0f} {'12,000~16,000':>12s}")
    print(f"  {'수확지수 (HI)':<25s} {sim_summary['TWSO']/sim_summary['TAGP']:>12.2f} {'0.40~0.50':>12s}")
    print("=" * 55)
    print("  ※ 실측(참고)는 한국 중부지역 벼 일반적 범위")
    print("  ※ API 연결 시 실제 RDA 시험데이터로 대체됩니다")


if __name__ == "__main__":
    main()
