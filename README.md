# Week 6 - PCSE/WOFOST 작물 시뮬레이션

스마트 온실 모델링 이론과 개발 실습 강의자료입니다.

## 빠른 시작

```bash
# 1. uv 설치 (없다면)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 의존성 설치
uv sync

# 3. 시뮬레이션 실행
uv run python run_pcse_example.py
```

## 강의자료

브라우저에서 `lecture.html`을 열면 됩니다.

## 파일 구조

```
├── lecture.html              # 강의용 HTML (브라우저에서 열기)
├── run_pcse_example.py       # PCSE 벼 시뮬레이션 예제
├── result_rice_daejeon_2025.png  # 시뮬레이션 결과 그래프
├── pyproject.toml            # 프로젝트 의존성 (uv)
└── uv.lock                   # 의존성 잠금 파일
```
