"""
WOFOST 버전별 비교 예제
======================
PCSE 프레임워크에서 WOFOST 7.2, 7.3, 8.1 세 버전을
동일 조건(대전, 벼)으로 실행하여 결과를 비교한다.

실행: uv run python run_compare_versions.py
"""

import yaml
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import platform

# 한글 폰트
if platform.system() == "Darwin":
    mpl.rcParams["font.family"] = "Apple SD Gothic Neo"
elif platform.system() == "Windows":
    mpl.rcParams["font.family"] = "Malgun Gothic"
else:
    mpl.rcParams["font.family"] = "NanumGothic"
mpl.rcParams["axes.unicode_minus"] = False

from pcse.models import Wofost72_PP, Wofost73_PP, Wofost81_PP
from pcse.input import (
    YAMLCropDataProvider,
    OpenMeteoWeatherDataProvider,
    DummySoilDataProvider,
    WOFOST72SiteDataProvider,
    WOFOST73SiteDataProvider,
    WOFOST81SiteDataProvider_Classic,
)
from pcse.base import ParameterProvider

# ─────────────────────────────────────────────
# 공통 설정
# ─────────────────────────────────────────────
print("기상자료 로딩 (대전) ...")
wdp = OpenMeteoWeatherDataProvider(latitude=36.35, longitude=127.38)
soild = DummySoilDataProvider()

agro = yaml.safe_load("""
- 2025-05-01:
    CropCalendar:
        crop_name: rice
        variety_name: Rice_501
        crop_start_date: 2025-05-15
        crop_start_type: emergence
        crop_end_date: 2025-10-15
        crop_end_type: harvest
        max_duration: 200
    TimedEvents: null
    StateEvents: null
""")

# ─────────────────────────────────────────────
# 모델별 실행 함수
# ─────────────────────────────────────────────
def run_wofost72():
    cropd = YAMLCropDataProvider(model=Wofost72_PP)
    cropd.set_active_crop("rice", "Rice_501")
    sited = WOFOST72SiteDataProvider(WAV=100)
    params = ParameterProvider(cropdata=cropd, soildata=soild, sitedata=sited)
    m = Wofost72_PP(params, wdp, agro)
    m.run_till_terminate()
    return m

def run_wofost73():
    cropd = YAMLCropDataProvider(model=Wofost73_PP)
    cropd.set_active_crop("rice", "Rice_501")
    sited = WOFOST73SiteDataProvider(WAV=100, CO2=400)
    params = ParameterProvider(cropdata=cropd, soildata=soild, sitedata=sited)
    m = Wofost73_PP(params, wdp, agro)
    m.run_till_terminate()
    return m

def run_wofost81():
    cropd = YAMLCropDataProvider(model=Wofost81_PP)
    cropd.set_active_crop("rice", "Rice_501")
    sited = WOFOST81SiteDataProvider_Classic(
        WAV=100, CO2=400,
        NAVAILI=100, NSOILBASE=50, NSOILBASE_FR=0.025,
    )
    params = ParameterProvider(cropdata=cropd, soildata=soild, sitedata=sited)
    m = Wofost81_PP(params, wdp, agro)
    m.run_till_terminate()
    return m

# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
print("WOFOST 7.2 실행 ...")
m72 = run_wofost72()
print("WOFOST 7.3 실행 (CO2 반응 포함) ...")
m73 = run_wofost73()
print("WOFOST 8.1 실행 (CO2 + 질소 수지) ...")
m81 = run_wofost81()

# 결과 DataFrame
def to_df(model):
    df = pd.DataFrame(model.get_output())
    df = df.dropna(subset=["DVS"])
    df["day"] = pd.to_datetime(df["day"])
    df = df.set_index("day")
    # WOFOST 8.1은 WSO/WLV/WST (7.x는 TWSO/TWLV/TWST) — 통일
    renames = {"WSO": "TWSO", "WLV": "TWLV", "WST": "TWST", "WRT": "TWRT"}
    for old, new in renames.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]
    return df

df72 = to_df(m72)
df73 = to_df(m73)
df81 = to_df(m81)

s72 = m72.get_summary_output()[0]
s73 = m73.get_summary_output()[0]
s81 = m81.get_summary_output()[0]

# ─────────────────────────────────────────────
# 결과 요약
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("  WOFOST 버전별 비교 — 대전 벼 (Rice_501) 2025")
print("=" * 60)
print(f"  {'항목':<20s} {'v7.2':>10s} {'v7.3':>10s} {'v8.1':>10s}")
print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*10}")
print(f"  {'곡물수량 (kg/ha)':<20s} {s72['TWSO']:>10.0f} {s73['TWSO']:>10.0f} {s81['TWSO']:>10.0f}")
print(f"  {'TAGP (kg/ha)':<20s} {s72['TAGP']:>10.0f} {s73['TAGP']:>10.0f} {s81['TAGP']:>10.0f}")
print(f"  {'최대 LAI':<20s} {s72['LAIMAX']:>10.2f} {s73['LAIMAX']:>10.2f} {s81['LAIMAX']:>10.2f}")
print(f"  {'개화일':<20s} {str(s72['DOA']):>10s} {str(s73['DOA']):>10s} {str(s81['DOA']):>10s}")
print(f"  {'성숙일':<20s} {str(s72['DOM']):>10s} {str(s73['DOM']):>10s} {str(s81['DOM']):>10s}")
print("=" * 60)
print("  v7.2: 빛+온도만 고려")
print("  v7.3: + CO2 반응 (400 ppm)")
print("  v8.1: + CO2 + 질소 수지")

# ─────────────────────────────────────────────
# 시각화
# ─────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("WOFOST 버전별 비교 — 대전 벼 2025", fontsize=15, fontweight="bold")

colors = {"7.2": "#2563eb", "7.3": "#16a34a", "8.1": "#ea580c"}

# (1) DVS
ax = axes[0, 0]
ax.plot(df72.index, df72["DVS"], color=colors["7.2"], label="v7.2", linewidth=2)
ax.plot(df73.index, df73["DVS"], color=colors["7.3"], label="v7.3", linewidth=2, linestyle="--")
ax.plot(df81.index, df81["DVS"], color=colors["8.1"], label="v8.1", linewidth=2, linestyle=":")
ax.set_title("발육단계 (DVS)")
ax.set_ylabel("DVS [-]")
ax.legend()
ax.grid(True, alpha=0.3)

# (2) LAI
ax = axes[0, 1]
ax.plot(df72.index, df72["LAI"], color=colors["7.2"], label="v7.2", linewidth=2)
ax.plot(df73.index, df73["LAI"], color=colors["7.3"], label="v7.3", linewidth=2, linestyle="--")
ax.plot(df81.index, df81["LAI"], color=colors["8.1"], label="v8.1", linewidth=2, linestyle=":")
ax.set_title("엽면적지수 (LAI)")
ax.set_ylabel("LAI [ha ha⁻¹]")
ax.legend()
ax.grid(True, alpha=0.3)

# (3) TWSO (곡물)
ax = axes[1, 0]
ax.plot(df72.index, df72["TWSO"], color=colors["7.2"], label="v7.2", linewidth=2)
ax.plot(df73.index, df73["TWSO"], color=colors["7.3"], label="v7.3", linewidth=2, linestyle="--")
ax.plot(df81.index, df81["TWSO"], color=colors["8.1"], label="v8.1", linewidth=2, linestyle=":")
ax.set_title("곡물 건물중 (TWSO)")
ax.set_ylabel("TWSO [kg ha⁻¹]")
ax.legend()
ax.grid(True, alpha=0.3)

# (4) TAGP
ax = axes[1, 1]
ax.plot(df72.index, df72["TAGP"], color=colors["7.2"], label="v7.2", linewidth=2)
ax.plot(df73.index, df73["TAGP"], color=colors["7.3"], label="v7.3", linewidth=2, linestyle="--")
ax.plot(df81.index, df81["TAGP"], color=colors["8.1"], label="v8.1", linewidth=2, linestyle=":")
ax.set_title("총 지상부 건물중 (TAGP)")
ax.set_ylabel("TAGP [kg ha⁻¹]")
ax.legend()
ax.grid(True, alpha=0.3)

for ax in axes.flat:
    ax.tick_params(axis="x", rotation=30)

plt.tight_layout()
plt.savefig("sim_fig/result_version_comparison.png", dpi=150, bbox_inches="tight")
print("\n그래프 저장: result_version_comparison.png")
plt.show()
