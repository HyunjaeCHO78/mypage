# FILE_ORGANIZATION_PLAYBOOK

## 목적
이 문서는 실전 운영 중 입력 파일과 결과 파일이 누적되어도
헷갈리지 않도록 날짜 기준 폴더/파일 구조를 설명합니다.

---

## 새 폴더 구조
```text
reports/
├─ daily/
│  ├─ 2026-03-21_conservative_top3.json
│  └─ 2026-03-21_conservative_summary.txt
├─ weekly/
│  └─ 2026-03-21_weekly_conservative_report.md
└─ (기존 예시 파일들)

inputs/
└─ archive/
   └─ 2026-03-21_candidates.csv
```

---

## 일별 파일은 어디에 저장되는가?
매일 실행 결과는 아래에 저장됩니다.

- `reports/daily/YYYY-MM-DD_conservative_top3.json`
- `reports/daily/YYYY-MM-DD_conservative_summary.txt`

예:
- `reports/daily/2026-03-21_conservative_top3.json`
- `reports/daily/2026-03-21_conservative_summary.txt`

이렇게 하면 같은 명령어를 매일 써도 결과가 날짜별로 분리됩니다.

---

## 주간 파일은 어디에 저장되는가?
주간 리포트는 아래에 저장됩니다.

- `reports/weekly/YYYY-MM-DD_weekly_conservative_report.md`

예:
- `reports/weekly/2026-03-21_weekly_conservative_report.md`

보통 금요일 장 마감 후나 주말 복기 시간에 생성합니다.

---

## 입력 파일 보관 방식
실전 실행 시 현재 템플릿 입력본을 아래 경로에 복사 보관합니다.

- `inputs/archive/YYYY-MM-DD_candidates.csv`

예:
- `inputs/archive/2026-03-21_candidates.csv`

이렇게 하면 나중에 “그날 어떤 후보를 넣었는지”를 다시 확인할 수 있습니다.

---

## 파일이 많아졌을 때 확인 순서
가장 추천하는 확인 순서는 아래와 같습니다.

1. 오늘 실행 결과: `reports/daily/` 
2. 주간 복기 결과: `reports/weekly/`
3. 그날 입력 원본: `inputs/archive/`
4. 오래된 예시/샘플 파일: 루트 `reports/` 의 기존 예시 파일

즉, 실전 운영에서는 **daily → weekly → input archive** 순서로 보면 됩니다.

---

## 삭제하면 안 되는 파일
아래 파일은 되도록 지우지 않는 것이 좋습니다.

- `templates/candidate_input_template.csv`
- `profiles/conservative.json`
- `profiles/aggressive.json`
- `scripts/run_daily_conservative.py`
- `scripts/run_candidate_pipeline.py`
- `scripts/generate_weekly_report.py`
- `inputs/archive/` 아래 실제 입력 기록
- `reports/daily/` 아래 실제 일별 결과
- `reports/weekly/` 아래 실제 주간 리포트

---

## 삭제 가능한 파일
아래 파일은 필요에 따라 정리할 수 있습니다.

- 과거 테스트용 샘플 결과 파일
- 중복 생성된 예시 리포트
- 임시 출력 파일

단, 삭제 전에 실제 운영 기록인지 먼저 확인해야 합니다.

---

## 날짜별 파일명 규칙
- 일별 JSON: `YYYY-MM-DD_conservative_top3.json`
- 일별 TXT: `YYYY-MM-DD_conservative_summary.txt`
- 주간 MD: `YYYY-MM-DD_weekly_conservative_report.md`
- 입력 보관 CSV: `YYYY-MM-DD_candidates.csv`

---

## 사용자는 무엇만 기억하면 되는가?
1. 매일은 `python3 scripts/run_daily_conservative.py`
2. 주말은 `python3 scripts/generate_weekly_report.py`
3. 결과는 `reports/daily`, `reports/weekly`, `inputs/archive` 에 날짜별로 쌓인다
