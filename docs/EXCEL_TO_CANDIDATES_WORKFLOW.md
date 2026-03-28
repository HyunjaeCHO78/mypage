# EXCEL_TO_CANDIDATES_WORKFLOW

## 목적
이 문서는 엑셀/시트에서 후보 종목 정보를 정리한 뒤,
`templates/candidate_input_template.csv` 로 옮기고,
`scripts/rank_candidates.py` 및 `scripts/run_candidate_pipeline.py` 로 바로 연결하는 방법을 설명합니다.

---

## 1. 사용자가 엑셀/시트에서 입력해야 하는 항목
후보 종목 한 줄당 아래 항목을 정리합니다.

| 컬럼 | 의미 | 입력 가이드 |
|---|---|---|
| ticker | 종목 코드 | 숫자 또는 문자열 형태로 입력 |
| name | 종목명 | 종목명 그대로 입력 |
| theme | 테마/섹터 | 예: 반도체, 바이오, 2차전지 |
| material_clarity | 재료 명확성 | 0~2 |
| trading_value | 거래대금 | 0~2 |
| foreign_flow | 외국인 수급 | 0~2 |
| institutional_flow | 기관 수급 | 0~2 |
| program_flow | 프로그램 흐름 | 0~2 |
| chart_position | 차트 자리 | 0~2 |
| early_stage | 시세 초입성 | 0~2 |
| next_day_expectation | 다음날 기대감 | 0~2 |
| market_alignment | 시장 시황과의 일치도 | 0~2 |
| understanding | 내가 이해하는 종목인가 | 0~2 |

점수형 항목은 모두 **0~2 범위**를 사용합니다.

---

## 2. candidate_input_template.csv 로 옮기는 방법
1. `templates/candidate_input_template.csv` 를 복사합니다.
2. 각 행을 후보 종목 1개로 사용합니다.
3. 기존 예시 행을 수정하거나 새 행을 추가합니다.
4. 저장할 때는 UTF-8 CSV 형식을 권장합니다.

추천 흐름:
- 엑셀에서 종목 후보를 먼저 정리
- 점수 항목을 0/1/2로 빠르게 입력
- CSV로 저장 또는 복붙
- 파이프라인 실행

---

## 3. rank_candidates.py 와 연결하는 방법
직접 실행하려면 아래처럼 사용합니다.

```bash
python3 scripts/rank_candidates.py \
  --profile conservative \
  --input templates/candidate_input_template.csv \
  --format csv \
  --output reports/candidates_conservative_top3.json
```

공격형 예시:

```bash
python3 scripts/rank_candidates.py \
  --profile aggressive \
  --input templates/candidate_input_template.csv \
  --format csv \
  --output reports/candidates_aggressive_top3.json
```

---

## 4. run_candidate_pipeline.py 로 더 쉽게 실행하는 방법
파이프라인 스크립트는 내부적으로 `rank_candidates.py` 를 호출하고,
출력 파일명을 자동으로 만들어 줍니다.

### 보수형 실행 예시
```bash
python3 scripts/run_candidate_pipeline.py \
  --input templates/candidate_input_template.csv \
  --profile conservative
```

### 공격형 실행 예시
```bash
python3 scripts/run_candidate_pipeline.py \
  --input templates/candidate_input_template.csv \
  --profile aggressive
```

자동 저장 예시:
- `reports/candidates_conservative_top3.json`
- `reports/candidates_aggressive_top3.json`

---

## 5. 결과 파일 확인 방법
실행 후 아래를 확인하면 됩니다.

1. 콘솔에 상위 후보 3개가 출력되는지 확인
2. `reports/` 폴더에 결과 JSON 파일이 생겼는지 확인
3. 각 결과 파일에서 다음 항목을 확인
   - rank
   - profile_name
   - ticker
   - name
   - total_score
   - passed
   - major_score_details

---

## 6. 흔한 입력 실수와 해결법

### 실수 1) 점수에 0~2가 아닌 값을 넣음
- 예: `3`, `-1`
- 해결: 0, 1, 2 중 하나로 수정
- 참고: 스크립트는 경고를 출력하고 점수를 0~2 범위로 보정합니다.

### 실수 2) 숫자 대신 문자 입력
- 예: `high`, `good`
- 해결: 숫자 0~2로 바꾸기
- 참고: 변환 실패 시 경고가 출력되고 0점 처리됩니다.

### 실수 3) 필수 컬럼 누락
- 예: `ticker`, `name`, `trading_value` 누락
- 해결: 템플릿 헤더와 동일하게 컬럼명을 맞추기

### 실수 4) CSV 인코딩 문제
- 한글이 깨지면 UTF-8로 다시 저장

### 실수 5) 헤더 이름이 다름
- 예: `turnover`, `chart_setup`
- 해결: 현재 템플릿 기준 헤더명(`trading_value`, `chart_position`)을 사용

---

## 7. 추천 실전 사용 순서
1. 엑셀에서 후보 종목 정리
2. 템플릿 CSV에 복사/입력
3. 보수형으로 먼저 실행
4. 공격형으로 한 번 더 실행
5. 두 결과를 비교해 최종 관심 종목 1~3개 압축
