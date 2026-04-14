"""
WOFOST vs 농촌진흥청 실측 데이터 검증
=====================================
data/ 폴더의 CSV를 읽어서 scatter plot + RMSE/R² 비교

- 시뮬레이션 결과가 data/sim_yield.csv에 없으면 자동 생성
- 이미 있으면 바로 비교만 수행 (빠름)

실행: uv run python run_validation.py
"""

import os
import time
import json
import yaml
import numpy as np
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
# 지역코드 → 위경도
# ─────────────────────────────────────────────
AREA_COORDS = {
    310: (37.26, 127.00, "화서"),
    325: (35.95, 127.00, "익산"),
    327: (35.49, 128.75, "밀양"),
    328: (37.26, 126.99, "수원"),
    329: (36.41, 128.16, "상주"),
    330: (35.73, 127.73, "운봉"),
    331: (38.15, 127.31, "철원"),
    332: (37.20, 126.82, "화성"),
    333: (37.88, 127.73, "춘천"),
    334: (36.64, 127.49, "청원"),
    335: (35.18, 128.07, "진주"),
    336: (37.65, 128.73, "진부"),
    337: (37.13, 128.19, "제천"),
    338: (36.43, 129.40, "영덕"),
    339: (36.35, 127.38, "대전"),
    340: (35.87, 128.60, "대구"),
    342: (35.14, 126.91, "광산"),
    343: (35.76, 126.69, "계화"),
    344: (37.75, 128.88, "강릉"),
    349: (37.28, 127.44, "이천"),
    350: (36.68, 126.85, "예산"),
    351: (36.57, 128.73, "안동"),
    352: (35.01, 126.72, "나주"),
}


# ─────────────────────────────────────────────
# 통계
# ─────────────────────────────────────────────
def calc_rmse(obs, sim):
    return np.sqrt(np.mean((obs - sim) ** 2))

def calc_r2(obs, sim):
    ss_res = np.sum((obs - sim) ** 2)
    ss_tot = np.sum((obs - np.mean(obs)) ** 2)
    return 1 - ss_res / ss_tot

def calc_mbe(obs, sim):
    return np.mean(sim - obs)


# ─────────────────────────────────────────────
# 시뮬레이션 결과 생성 (없을 때만)
# ─────────────────────────────────────────────
def generate_sim_csv():
    """지역x연도 조합별 WOFOST TWSO를 CSV로 저장"""
    from pcse.models import Wofost72_PP
    from pcse.input import (
        YAMLCropDataProvider, OpenMeteoWeatherDataProvider,
        DummySoilDataProvider, WOFOST72SiteDataProvider,
    )
    from pcse.base import ParameterProvider

    years = [2017, 2018, 2021, 2023, 2024]
    weather_cache = {}
    results = []

    # 1) 기상 데이터 수집
    areas = list(AREA_COORDS.items())
    print(f"  기상 데이터 로딩 ({len(areas)}개 지점) ...")
    for i, (code, (lat, lon, name)) in enumerate(areas):
        for attempt in range(5):
            try:
                weather_cache[(lat, lon)] = OpenMeteoWeatherDataProvider(
                    latitude=lat, longitude=lon
                )
                print(f"    [{i+1}/{len(areas)}] {name}: OK")
                break
            except Exception:
                if attempt < 4:
                    wait = 10 * (attempt + 1)
                    print(f"    [{i+1}/{len(areas)}] {name}: 재시도 ({wait}초) ...")
                    time.sleep(wait)
                else:
                    print(f"    [{i+1}/{len(areas)}] {name}: 실패 (건너뜀)")
        if i < len(areas) - 1:
            time.sleep(8)

    # 2) 시뮬레이션
    print(f"\n  시뮬레이션 실행 ...")
    for code, (lat, lon, name) in areas:
        wdp = weather_cache.get((lat, lon))
        if wdp is None:
            continue
        for year in years:
            try:
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
                s = model.get_summary_output()[0]
                results.append({
                    "exprAreaCode": code, "areaNm": name,
                    "exprYear": year, "lat": lat, "lon": lon,
                    "sim_TWSO": s["TWSO"], "sim_TAGP": s["TAGP"],
                    "sim_LAIMAX": s["LAIMAX"],
                })
                print(f"    {name} {year}: TWSO={s['TWSO']:.0f}")
            except Exception as e:
                print(f"    {name} {year}: 실패 ({e})")

    df_sim = pd.DataFrame(results)
    df_sim.to_csv("data/sim_yield.csv", index=False, encoding="utf-8-sig")
    print(f"\n  저장: data/sim_yield.csv ({len(df_sim)}건)")
    return df_sim


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    sim_path = "data/sim_yield.csv"

    # 시뮬레이션 결과 준비
    if os.path.exists(sim_path):
        print("[1/2] 시뮬레이션 결과 로드 (data/sim_yield.csv) ...")
        df_sim = pd.read_csv(sim_path)
        print(f"  {len(df_sim)}건 로드됨")
    else:
        print("[1/2] 시뮬레이션 결과 생성 (최초 1회, 수 분 소요) ...")
        df_sim = generate_sim_csv()

    # 실측 데이터 로드
    print("\n[2/2] 실측 데이터 로드 & 비교 ...")
    df_obs = pd.read_csv("data/rda_yield_2017_2024.csv")
    df_obs["exam1"] = pd.to_numeric(df_obs["exam1"], errors="coerce")
    df_obs["obs_yield_dry"] = df_obs["exam1"] * 10 * 0.86
    df_obs = df_obs.dropna(subset=["obs_yield_dry"])
    df_obs = df_obs[df_obs["obs_yield_dry"] > 0]

    # 병합 (지역 + 연도 기준)
    merged = df_obs.merge(
        df_sim[["exprAreaCode", "exprYear", "sim_TWSO", "areaNm"]].rename(
            columns={"areaNm": "sim_areaNm"}
        ),
        on=["exprAreaCode", "exprYear"],
        how="inner",
    )
    print(f"  매칭: {len(merged)}건 (관측 {len(df_obs)}건 x 시뮬 {len(df_sim)}건)")

    if len(merged) == 0:
        print("  매칭 데이터 없음. 종료.")
        return

    obs = merged["obs_yield_dry"].values
    sim = merged["sim_TWSO"].values

    rmse = calc_rmse(obs, sim)
    r2 = calc_r2(obs, sim)
    mbe = calc_mbe(obs, sim)
    nrmse = rmse / obs.mean() * 100

    print(f"\n{'='*55}")
    print(f"  검증 통계 (n={len(obs)})")
    print(f"{'='*55}")
    print(f"  RMSE   = {rmse:.0f} kg/ha ({nrmse:.1f}%)")
    print(f"  R²     = {r2:.3f}")
    print(f"  MBE    = {mbe:.0f} kg/ha ({'과대' if mbe>0 else '과소'}추정)")
    print(f"  관측 평균 = {obs.mean():.0f} kg/ha")
    print(f"  모의 평균 = {sim.mean():.0f} kg/ha")
    print(f"{'='*55}")

    # ── scatter plot ──
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # (1) 연도별
    ax = axes[0]
    years = sorted(merged["exprYear"].unique())
    cmap = plt.cm.tab10
    for i, yr in enumerate(years):
        m = merged["exprYear"] == yr
        ax.scatter(obs[m], sim[m], c=[cmap(i)], label=str(yr),
                   alpha=0.7, s=40, edgecolors="white", linewidth=0.5)

    lims = [min(obs.min(), sim.min()) - 500, max(obs.max(), sim.max()) + 500]
    ax.plot(lims, lims, "k--", alpha=0.5, label="1:1 line")
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("관측 곡물 건물중 [kg/ha]")
    ax.set_ylabel("WOFOST 모의 곡물 건물중 [kg/ha]")
    ax.set_title("연도별 비교")
    ax.legend(fontsize=9)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.text(0.05, 0.95,
            f"n = {len(obs)}\nRMSE = {rmse:.0f} kg/ha ({nrmse:.1f}%)\n"
            f"R² = {r2:.3f}\nMBE = {mbe:.0f} kg/ha",
            transform=ax.transAxes, fontsize=10, va="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    # (2) 지역별
    ax = axes[1]
    area_names = sorted(merged["sim_areaNm"].dropna().unique())
    cmap2 = plt.cm.Set2
    for i, name in enumerate(area_names):
        m = merged["sim_areaNm"] == name
        ax.scatter(obs[m], sim[m], c=[cmap2(i % 8)], label=name,
                   alpha=0.7, s=40, edgecolors="white", linewidth=0.5)

    ax.plot(lims, lims, "k--", alpha=0.5)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("관측 곡물 건물중 [kg/ha]")
    ax.set_ylabel("WOFOST 모의 곡물 건물중 [kg/ha]")
    ax.set_title("지역별 비교")
    ax.legend(fontsize=8, ncol=2, loc="lower right")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("sim_fig/result_validation_scatter.png", dpi=150, bbox_inches="tight")
    print("\n그래프 저장: sim_fig/result_validation_scatter.png")
    plt.show()


if __name__ == "__main__":
    main()
