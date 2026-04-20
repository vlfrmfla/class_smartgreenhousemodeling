"""
농촌진흥청 두류 작황 성적 데이터 수집 → CSV 저장
================================================
공공데이터포털 API를 통해 두류(콩) 실측 데이터를 받아
data/ 폴더에 CSV로 저장한다.

API: 농촌진흥청 국립식량과학원_두류 작황 성적 정보 서비스 (v2)
https://www.data.go.kr/data/15065006/openapi.do

실행: uv run python fetch_rda_data_bean.py
"""

import json
import os
import requests
import pandas as pd

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"
BASE_URL = "https://apis.data.go.kr/1390803/PlcrCrpstScoreInfoService_v2"

OUT_DIR = os.path.join(os.path.dirname(__file__), "data")

YEARS = range(2017, 2026)  # 2017~2025

# ─────────────────────────────────────────────
# API 호출 함수
# ─────────────────────────────────────────────
def call_api(endpoint, extra_params=None):
    """RDA 두류 작황 API 호출 (페이지네이션 포함)"""
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
        return []

    data = resp.json()
    body = data.get("body", data)
    items = body.get("items", [])
    total = body.get("totalCount", len(items))
    print(f"  {endpoint}: {total}건")
    return items


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) 코드 목록 (품종, 지역) → JSON 저장
    print("[코드 목록 조회]")
    code_items = call_api("getPlcrCodeList_v2")
    if code_items:
        resp = requests.get(
            f"{BASE_URL}/getPlcrCodeList_v2",
            params={"serviceKey": SERVICE_KEY, "pageNo": "1", "numOfRows": "1000"},
            timeout=30,
        )
        body = resp.json().get("body", resp.json())

        species = body.get("spciesCode", [])
        areas = body.get("exprAreaCode", [])

        species_map = {item["code"]: item["name"] for item in species}
        areas_map = {item["code"]: item["name"] for item in areas}

        with open(os.path.join(OUT_DIR, "bean_code_species.json"), "w", encoding="utf-8") as f:
            json.dump(species_map, f, ensure_ascii=False, indent=2)
        with open(os.path.join(OUT_DIR, "bean_code_areas.json"), "w", encoding="utf-8") as f:
            json.dump(areas_map, f, ensure_ascii=False, indent=2)
        print(f"  → bean_code_species.json ({len(species_map)}건)")
        print(f"  → bean_code_areas.json ({len(areas_map)}건)")

    # 2) 회차별 데이터 (01~04) → 전 연도 통합 CSV
    rounds = {
        "01": "getPlcrExprTmrd_01List_v2",  # 파종기, 출현일
        "02": "getPlcrExprTmrd_02List_v2",  # 초장, 분지수, 개화기
        "03": "getPlcrExprTmrd_03List_v2",  # 협수, 립수, 건물중
        "04": "getPlcrExprTmrd_04List_v2",  # 수량, 백립중, 품질
    }

    for rnd, endpoint in rounds.items():
        all_items = []
        print(f"\n[{rnd}회차 데이터 수집]")
        for year in YEARS:
            items = call_api(endpoint, {"srchExprYear": str(year)})
            all_items.extend(items)

        if all_items:
            df = pd.DataFrame(all_items)
            fname = f"bean_round{rnd}_{YEARS.start}_{YEARS.stop - 1}.csv"
            df.to_csv(os.path.join(OUT_DIR, fname), index=False, encoding="utf-8-sig")
            print(f"  → {fname} ({len(df)}건)")
        else:
            print(f"  → {rnd}회차 데이터 없음")

    # 3) 재배 관리 정보 → CSV
    all_ctvt = []
    print("\n[재배 관리 정보 수집]")
    for year in YEARS:
        items = call_api("getPlcrCtvtMthList_v2", {"srchExprYear": str(year)})
        all_ctvt.extend(items)

    if all_ctvt:
        df = pd.DataFrame(all_ctvt)
        fname = f"bean_cultivation_{YEARS.start}_{YEARS.stop - 1}.csv"
        df.to_csv(os.path.join(OUT_DIR, fname), index=False, encoding="utf-8-sig")
        print(f"  → {fname} ({len(df)}건)")

    print("\n완료!")


if __name__ == "__main__":
    main()
