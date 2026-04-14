"""
PCSE (Python Crop Simulation Environment) 사용 예제
===================================================
대전 지역 벼(Rice) 재배 시뮬레이션 (WOFOST 모델, Potential Production)

실행: uv run python run_pcse_example.py
"""

import datetime as dt
import yaml
import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd

# 한글 폰트 설정
import platform
if platform.system() == "Darwin":
    mpl.rcParams["font.family"] = "Apple SD Gothic Neo"
elif platform.system() == "Windows":
    mpl.rcParams["font.family"] = "Malgun Gothic"
else:
    mpl.rcParams["font.family"] = "NanumGothic"
mpl.rcParams["axes.unicode_minus"] = False

from pcse.models import Wofost72_PP
from pcse.input import (
    YAMLCropDataProvider,
    OpenMeteoWeatherDataProvider,
    DummySoilDataProvider,
    WOFOST72SiteDataProvider,
)
from pcse.base import ParameterProvider

# ─────────────────────────────────────────────
# 1. 기상자료 (OpenMeteo API - 대전)
# ─────────────────────────────────────────────
print("[1/5] 기상자료 로딩 (대전, 36.35°N 127.38°E) ...")
wdp = OpenMeteoWeatherDataProvider(latitude=36.35, longitude=127.38)
print(f"      기간: {wdp.first_date} ~ {wdp.last_date}")

# ─────────────────────────────────────────────
# 2. 작물 파라미터 (내장 벼 품종)
# ─────────────────────────────────────────────
print("[2/5] 작물 파라미터 로딩 (Rice_501) ...")
cropd = YAMLCropDataProvider()
cropd.set_active_crop("rice", "Rice_501")

# ─────────────────────────────────────────────
# 3. 토양 & 사이트 설정
# ─────────────────────────────────────────────
print("[3/5] 토양/사이트 설정 ...")
soild = DummySoilDataProvider()                # Potential Production에서는 토양 영향 없음
sited = WOFOST72SiteDataProvider(WAV=100)      # 초기 토양수분 (사용되지 않음)

params = ParameterProvider(cropdata=cropd, soildata=soild, sitedata=sited)

# ─────────────────────────────────────────────
# 4. 재배관리 (Agromanagement)
# ─────────────────────────────────────────────
print("[4/5] 재배관리 설정 ...")
agro_yaml = """
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
"""
agro = yaml.safe_load(agro_yaml)

# ─────────────────────────────────────────────
# 5. 모델 실행
# ─────────────────────────────────────────────
print("[5/5] WOFOST 72 (Potential Production) 실행 ...")
wofost = Wofost72_PP(params, wdp, agro)
wofost.run_till_terminate()

# 결과 추출
output = wofost.get_output()
df = pd.DataFrame(output)
df = df.dropna(subset=["DVS"])  # 출현 전 행 제거
df["day"] = pd.to_datetime(df["day"])
df = df.set_index("day")

summary = wofost.get_summary_output()[0]

# ─────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────
print("\n" + "=" * 50)
print("  시뮬레이션 결과 요약")
print("=" * 50)
print(f"  출현일 (DOE):       {summary['DOE']}")
print(f"  개화일 (DOA):       {summary['DOA']}")
print(f"  성숙일 (DOM):       {summary['DOM']}")
print(f"  수확일 (DOH):       {summary['DOH']}")
print(f"  최대 LAI:           {summary['LAIMAX']:.2f} ha/ha")
print(f"  총 지상부 건물중:   {summary['TAGP']:.0f} kg/ha")
print(f"  곡물 수량 (TWSO):   {summary['TWSO']:.0f} kg/ha")
print(f"  잎 건물중 (TWLV):   {summary['TWLV']:.0f} kg/ha")
print(f"  줄기 건물중 (TWST): {summary['TWST']:.0f} kg/ha")
print(f"  뿌리 건물중 (TWRT): {summary['TWRT']:.0f} kg/ha")
print("=" * 50)

# ─────────────────────────────────────────────
# 시각화
# ─────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("PCSE/WOFOST 벼 시뮬레이션 — 대전 2025", fontsize=15, fontweight="bold")

# (1) DVS
ax = axes[0, 0]
ax.plot(df.index, df["DVS"], "b-", linewidth=2)
ax.axhline(y=1.0, color="r", linestyle="--", alpha=0.5, label="DVS=1 (개화)")
ax.axhline(y=2.0, color="gray", linestyle="--", alpha=0.5, label="DVS=2 (성숙)")
ax.set_title("발육단계 (DVS)")
ax.set_ylabel("DVS [-]")
ax.legend()
ax.grid(True, alpha=0.3)

# (2) LAI
ax = axes[0, 1]
ax.fill_between(df.index, df["LAI"], color="green", alpha=0.3)
ax.plot(df.index, df["LAI"], "g-", linewidth=2)
ax.set_title("엽면적지수 (LAI)")
ax.set_ylabel("LAI [ha ha⁻¹]")
ax.grid(True, alpha=0.3)

# (3) 기관별 건물중
ax = axes[1, 0]
ax.plot(df.index, df["TWLV"], "g-", label="잎 (TWLV)", linewidth=1.5)
ax.plot(df.index, df["TWST"], "orange", label="줄기 (TWST)", linewidth=1.5)
ax.plot(df.index, df["TWSO"], "r-", label="곡물 (TWSO)", linewidth=1.5)
ax.plot(df.index, df["TWRT"], "brown", label="뿌리 (TWRT)", linewidth=1.5)
ax.set_title("기관별 건물중")
ax.set_ylabel("건물중 [kg ha⁻¹]")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# (4) TAGP
ax = axes[1, 1]
ax.plot(df.index, df["TAGP"], "b-", linewidth=2)
ax.set_title("총 지상부 건물중 (TAGP)")
ax.set_ylabel("TAGP [kg ha⁻¹]")
ax.grid(True, alpha=0.3)

for ax in axes.flat:
    ax.tick_params(axis="x", rotation=30)

plt.tight_layout()
plt.savefig("sim_fig/result_rice_daejeon_2025.png", dpi=150, bbox_inches="tight")
print("\n그래프 저장: result_rice_daejeon_2025.png")
plt.show()
