"""
두류 시험 지역별 기상 데이터 수집 → CSV 저장
================================================
bean_code_areas.json 의 지역 코드마다 OpenMeteo API를 호출해
PCSE 포맷 (IRRAD, TMIN, TMAX, VAP, WIND, RAIN, E0, ES0, ET0) 으로
data/weather/ 에 저장한다.

참고: OpenMeteo archive API는 rate limit (HTTP 429) 이 걸립니다.
- 성공한 파일은 재실행 시 건너뛰므로, 실패한 지역이 남으면 다시 실행하세요.
- 전체 11개 지역을 받는 데 여러 번 실행이 필요할 수 있습니다.

실행: uv run python fetch_weather_bean.py
"""

import datetime as dt
import json
import os
import time
import pandas as pd
from pcse.input import OpenMeteoWeatherDataProvider

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
AREA_JSON = os.path.join(BASE_DIR, "data", "bean_code_areas.json")
OUT_DIR = os.path.join(BASE_DIR, "data", "weather")

# 기상 데이터 수집 기간 (기존 벼 지역 파일과 동일: 2015~현재)
START_DATE = dt.date(2015, 1, 1)

# 지역 간 대기 시간 (초) — rate limit 회피
SLEEP_BETWEEN = 18

# 두류 시험 지역 코드 → (위도, 경도) 매핑
# bean_code_areas.json 의 코드 11개에 대응
AREA_COORDS = {
    "0483": (35.95, 127.00),  # 익산(국립식량과학원)
    "0484": (37.26, 126.99),  # 수원(중부작물부)
    "0485": (35.49, 128.75),  # 밀양(남부작물부)
    "0486": (37.75, 128.88),  # 강릉
    "2346": (35.01, 126.72),  # 나주
    "2347": (38.09, 127.08),  # 연천
    "2348": (36.63, 127.48),  # 청원
    "2383": (35.90, 127.13),  # 완주
    "2384": (36.64, 127.49),  # 청주
    "2385": (35.95, 127.00),  # 익산(전북) — 0483 과 좌표 동일
    "2386": (35.18, 128.08),  # 진주
}


# ─────────────────────────────────────────────
# OpenMeteo → PCSE 포맷 CSV 저장
# ─────────────────────────────────────────────
def fetch_and_save(code, name, lat, lon):
    short_name = name.split("(")[0]
    out_path = os.path.join(OUT_DIR, f"weather_{short_name}_{lat}_{lon}.csv")

    if os.path.exists(out_path):
        print(f"  [{code}] {short_name}: 이미 존재, 건너뜀")
        return True

    for attempt in range(5):
        try:
            wdp = OpenMeteoWeatherDataProvider(
                latitude=lat, longitude=lon, start_date=START_DATE
            )
            break
        except Exception as e:
            if attempt < 4:
                wait = 15 * (attempt + 1)
                print(f"  [{code}] {short_name}: 재시도 {attempt+1}/5 ({wait}초 대기)")
                time.sleep(wait)
            else:
                print(f"  [{code}] {short_name}: 실패 - {e}")
                return False

    rows = []
    for day, wdc in wdp.store.items():
        rows.append({
            "day": day,
            "IRRAD": wdc.IRRAD,
            "TMIN": wdc.TMIN,
            "TMAX": wdc.TMAX,
            "VAP": wdc.VAP,
            "WIND": wdc.WIND,
            "RAIN": wdc.RAIN,
            "E0": wdc.E0,
            "ES0": wdc.ES0,
            "ET0": wdc.ET0,
        })
    df = pd.DataFrame(rows).sort_values("day")
    df.to_csv(out_path, index=False)
    print(f"  [{code}] {short_name}: {len(df)}일 ({df['day'].min()} ~ {df['day'].max()}) → {os.path.basename(out_path)}")
    return True


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(AREA_JSON, encoding="utf-8") as f:
        areas = json.load(f)

    print(f"두류 시험 지역 {len(areas)}곳의 기상 데이터 수집")
    print(f"기간: {START_DATE} ~ 현재 / 지역 간 대기: {SLEEP_BETWEEN}초\n")

    success = 0
    pending = []
    for i, (code, name) in enumerate(areas.items()):
        if code not in AREA_COORDS:
            print(f"  [{code}] {name}: 좌표 없음, 건너뜀")
            continue
        lat, lon = AREA_COORDS[code]
        if fetch_and_save(code, name, lat, lon):
            success += 1
        else:
            pending.append(f"{code} {name}")
        if i < len(areas) - 1:
            time.sleep(SLEEP_BETWEEN)

    print(f"\n완료: {success}/{len(areas)} 지역")
    if pending:
        print(f"실패한 지역 ({len(pending)}곳) — 잠시 후 다시 실행하면 이어받습니다:")
        for p in pending:
            print(f"  - {p}")


if __name__ == "__main__":
    main()
