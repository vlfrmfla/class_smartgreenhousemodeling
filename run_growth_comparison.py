"""
생육단계별 WOFOST vs 실측 비교
===============================
농진청 2~9회차 생육 데이터를 WOFOST 시계열과 비교
- 수량 scatter (지역x연도)
- 회차별 경수 비교 (tiller number proxy)

실행: uv run python run_growth_comparison.py
"""

import os
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

os.makedirs("sim_fig", exist_ok=True)

# ─────────────────────────────────────────────
# 통계 함수
# ─────────────────────────────────────────────
def rmse(obs, sim):
    return np.sqrt(np.mean((obs - sim) ** 2))

def r2(obs, sim):
    ss_res = np.sum((obs - sim) ** 2)
    ss_tot = np.sum((obs - np.mean(obs)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

def mbe(obs, sim):
    return np.mean(sim - obs)


# ─────────────────────────────────────────────
# 1. 수량 scatter (sim_yield.csv 활용)
# ─────────────────────────────────────────────
def plot_yield_scatter():
    """지역x연도별 곡물수량 scatter + 1:1 line + 통계"""
    df_sim = pd.read_csv("data/sim_yield.csv")
    df_obs = pd.read_csv("data/rda_yield_2017_2024.csv")
    df_obs["exam1"] = pd.to_numeric(df_obs["exam1"], errors="coerce")
    df_obs["obs_dry"] = df_obs["exam1"] * 10 * 0.86  # kg/ha 건물중
    df_obs = df_obs.dropna(subset=["obs_dry"])
    df_obs = df_obs[df_obs["obs_dry"] > 0]

    merged = df_obs.merge(
        df_sim[["exprAreaCode", "exprYear", "sim_TWSO", "areaNm"]].rename(
            columns={"areaNm": "loc"}
        ),
        on=["exprAreaCode", "exprYear"], how="inner",
    )
    if len(merged) == 0:
        print("수량 매칭 데이터 없음")
        return

    obs = merged["obs_dry"].values
    sim = merged["sim_TWSO"].values
    r = rmse(obs, sim)
    r2v = r2(obs, sim)
    m = mbe(obs, sim)
    nrmse = r / obs.mean() * 100

    fig, ax = plt.subplots(figsize=(7, 7))
    locs = sorted(merged["loc"].unique())
    cmap = plt.cm.Set2
    for i, loc in enumerate(locs):
        mask = merged["loc"] == loc
        ax.scatter(obs[mask], sim[mask], c=[cmap(i % 8)], label=loc,
                   s=50, alpha=0.8, edgecolors="white", linewidth=0.5)

    lims = [min(obs.min(), sim.min()) - 500, max(obs.max(), sim.max()) + 500]
    ax.plot(lims, lims, "k--", alpha=0.5, label="1:1")
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("관측 곡물 건물중 [kg/ha]", fontsize=12)
    ax.set_ylabel("WOFOST 모의 곡물 건물중 [kg/ha]", fontsize=12)
    ax.set_title("WOFOST vs 농진청 실측 — 곡물수량", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9, loc="lower right")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.text(0.05, 0.95,
            f"n = {len(obs)}\nRMSE = {r:.0f} kg/ha ({nrmse:.1f}%)\n"
            f"R² = {r2v:.3f}\nMBE = {m:.0f} kg/ha",
            transform=ax.transAxes, fontsize=11, va="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    plt.tight_layout()
    plt.savefig("sim_fig/scatter_yield.png", dpi=150, bbox_inches="tight")
    print(f"수량 scatter: n={len(obs)}, RMSE={r:.0f}, R²={r2v:.3f}")
    plt.close()


# ─────────────────────────────────────────────
# 2. 생육단계별 비교 (WOFOST 시계열 vs 실측 회차 데이터)
# ─────────────────────────────────────────────
def run_wofost_timeseries(site_name, lat, lon, year):
    """WOFOST 일별 시계열을 CSV 기상으로 실행"""
    from pcse.models import Wofost72_PP
    from pcse.input import (YAMLCropDataProvider, DummySoilDataProvider,
                             WOFOST72SiteDataProvider)
    from pcse.base import ParameterProvider

    # CSV 기상 데이터 로드 → PCSE WeatherDataProvider 대체
    # 이미 저장된 OpenMeteo 캐시 사용
    import glob
    wfiles = glob.glob(f"data/weather/weather_{site_name}_*.csv")
    if not wfiles:
        return None

    from pcse.input import OpenMeteoWeatherDataProvider
    wdp = OpenMeteoWeatherDataProvider(latitude=lat, longitude=lon)

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
    return df


def plot_growth_timeseries():
    """대전 2023년 기준 WOFOST 시계열 + 실측 회차 오버레이"""
    site = "대전"
    lat, lon = 36.35, 127.38
    year = 2023
    area_code = 339

    print(f"\n시계열 비교: {site} {year}")
    sim = run_wofost_timeseries(site, lat, lon, year)
    if sim is None:
        print("시뮬레이션 실패")
        return

    # 실측 수량 (9회차)
    df09 = pd.read_csv("data/rda_yield_2017_2024.csv")
    obs09 = df09[(df09["exprAreaCode"] == area_code) & (df09["exprYear"] == year)]

    # 실측 건물중 (8회차)
    df08 = pd.read_csv("data/rda_biomass_2017_2024.csv")
    obs08 = df08[(df08["exprAreaCode"] == area_code) & (df08["exprYear"] == year)]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"WOFOST 시계열 vs 실측 — {site} {year}", fontsize=14, fontweight="bold")

    # (1) DVS
    ax = axes[0, 0]
    ax.plot(sim["day"], sim["DVS"], "b-", linewidth=2)
    ax.axhline(1.0, color="r", ls="--", alpha=0.5, label="DVS=1 (개화)")
    ax.axhline(2.0, color="gray", ls="--", alpha=0.5, label="DVS=2 (성숙)")
    ax.set_title("발육단계 (DVS)")
    ax.set_ylabel("DVS [-]")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # (2) LAI
    ax = axes[0, 1]
    ax.fill_between(sim["day"], sim["LAI"], color="green", alpha=0.2)
    ax.plot(sim["day"], sim["LAI"], "g-", linewidth=2, label="WOFOST LAI")
    ax.set_title("엽면적지수 (LAI)")
    ax.set_ylabel("LAI [ha/ha]")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # (3) 기관별 건물중 + 8회차 실측
    ax = axes[1, 0]
    ax.plot(sim["day"], sim["TWLV"], "g-", label="잎 (sim)", linewidth=1.5)
    ax.plot(sim["day"], sim["TWST"], color="orange", label="줄기 (sim)", linewidth=1.5)
    ax.plot(sim["day"], sim["TWSO"], "r-", label="곡물 (sim)", linewidth=1.5)

    # 8회차 실측 오버레이 (수확기 건물중)
    # exam8=잎비율(%), exam9=고사비율(%), exam3=m2당임실립수
    # 직접적 건물중은 제한적이므로 9회차 수량만 표시
    if len(obs09) > 0:
        obs09["exam1"] = pd.to_numeric(obs09["exam1"], errors="coerce")
        obs_yield = obs09["exam1"].dropna()
        if len(obs_yield) > 0:
            mean_yield = obs_yield.mean() * 10 * 0.86  # kg/ha 건물중
            # 수확일 부근에 점으로 표시
            harvest_date = pd.Timestamp(f"{year}-10-15")
            ax.scatter([harvest_date], [mean_yield], c="red", s=100, zorder=5,
                       marker="*", label=f"실측 곡물 ({mean_yield:.0f})")

    ax.set_title("기관별 건물중")
    ax.set_ylabel("[kg/ha]")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (4) TAGP
    ax = axes[1, 1]
    ax.plot(sim["day"], sim["TAGP"], "b-", linewidth=2, label="WOFOST TAGP")
    ax.set_title("총 지상부 건물중 (TAGP)")
    ax.set_ylabel("TAGP [kg/ha]")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    for ax in axes.flat:
        ax.tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.savefig("sim_fig/timeseries_daejeon_2023.png", dpi=150, bbox_inches="tight")
    print("  저장: sim_fig/timeseries_daejeon_2023.png")
    plt.close()


def plot_multi_year_scatter():
    """연도별 수량 scatter (지역 색상)"""
    df_sim = pd.read_csv("data/sim_yield.csv")
    df_obs = pd.read_csv("data/rda_yield_2017_2024.csv")
    df_obs["exam1"] = pd.to_numeric(df_obs["exam1"], errors="coerce")
    df_obs["obs_dry"] = df_obs["exam1"] * 10 * 0.86
    df_obs = df_obs.dropna(subset=["obs_dry"])
    df_obs = df_obs[df_obs["obs_dry"] > 0]

    merged = df_obs.merge(
        df_sim[["exprAreaCode", "exprYear", "sim_TWSO", "areaNm"]].rename(
            columns={"areaNm": "loc"}
        ),
        on=["exprAreaCode", "exprYear"], how="inner",
    )
    if len(merged) == 0:
        return

    obs = merged["obs_dry"].values
    sim = merged["sim_TWSO"].values

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 연도별
    ax = axes[0]
    years = sorted(merged["exprYear"].unique())
    for i, yr in enumerate(years):
        m = merged["exprYear"] == yr
        ax.scatter(obs[m], sim[m], c=[plt.cm.tab10(i)], label=str(yr),
                   s=50, alpha=0.7, edgecolors="white", linewidth=0.5)
    lims = [min(obs.min(), sim.min()) - 500, max(obs.max(), sim.max()) + 500]
    ax.plot(lims, lims, "k--", alpha=0.5)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("관측 [kg/ha]"); ax.set_ylabel("모의 [kg/ha]")
    ax.set_title("연도별"); ax.legend(fontsize=9); ax.set_aspect("equal"); ax.grid(True, alpha=0.3)
    r_val = rmse(obs, sim); r2_val = r2(obs, sim); m_val = mbe(obs, sim)
    ax.text(0.05, 0.95, f"n={len(obs)}\nRMSE={r_val:.0f}\nR²={r2_val:.3f}\nMBE={m_val:.0f}",
            transform=ax.transAxes, fontsize=10, va="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    # 지역별
    ax = axes[1]
    locs = sorted(merged["loc"].unique())
    for i, loc in enumerate(locs):
        m = merged["loc"] == loc
        ax.scatter(obs[m], sim[m], c=[plt.cm.Set2(i % 8)], label=loc,
                   s=50, alpha=0.7, edgecolors="white", linewidth=0.5)
    ax.plot(lims, lims, "k--", alpha=0.5)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("관측 [kg/ha]"); ax.set_ylabel("모의 [kg/ha]")
    ax.set_title("지역별"); ax.legend(fontsize=9); ax.set_aspect("equal"); ax.grid(True, alpha=0.3)

    fig.suptitle("WOFOST vs 실측 — 곡물 건물중", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig("sim_fig/scatter_year_region.png", dpi=150, bbox_inches="tight")
    print("  저장: sim_fig/scatter_year_region.png")
    plt.close()


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    print("=== 생육단계별 비교 ===\n")

    print("[1/3] 수량 scatter ...")
    plot_yield_scatter()

    print("\n[2/3] 연도·지역별 scatter ...")
    plot_multi_year_scatter()

    print("\n[3/3] 대전 2023 시계열 비교 ...")
    plot_growth_timeseries()

    print("\n완료!")


if __name__ == "__main__":
    main()
