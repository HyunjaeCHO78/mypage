# CANDIDATE_INPUT_FORMAT

## 목적
이 문서는 `scripts/rank_candidates.py` 에 넣는 후보 종목 입력 파일 형식을 설명합니다.

## 지원 형식
- JSON (`--format json`)
- CSV (`--format csv`)

입력 파일이 없으면 스크립트 내부 mock data를 사용합니다.

---

## 필드 정의

| 필드명 | 설명 | 필수 여부 | 값 형식 | 비고 |
|---|---|---|---|---|
| ticker | 종목 코드 | 필수 | 문자열 | 출력에도 사용 |
| name | 종목명 | 필수 | 문자열 | 출력에도 사용 |
| theme | 테마/섹터 | 선택 | 문자열 | 요약용 |
| material_clarity | 재료 명확성 | 필수 | 0~2 숫자 | 점수화 대상 |
| trading_value | 거래대금 | 필수 | 0~2 숫자 | 점수화 대상 |
| foreign_flow | 외국인 수급 | 선택 | 0~2 숫자 | 점수화 대상 |
| institutional_flow | 기관 수급 | 선택 | 0~2 숫자 | 점수화 대상 |
| program_flow | 프로그램 흐름 | 선택 | 0~2 숫자 | 점수화 대상 |
| chart_position | 차트 자리 | 필수 | 0~2 숫자 | 점수화 대상 |
| early_stage | 시세 초입성 | 필수 | 0~2 숫자 | 점수화 대상 |
| next_day_expectation | 다음날 기대감 | 선택 | 0~2 숫자 | 점수화 대상 |
| market_alignment | 시장 시황 일치도 | 필수 | 0~2 숫자 | 점수화 대상 |
| understanding | 내가 이해하는 종목인가 | 필수 | 0~2 숫자 | 점수화 대상 |

---

## JSON 예시

```json
[
  {
    "ticker": "111111",
    "name": "AlphaBio",
    "theme": "바이오",
    "material_clarity": 2,
    "trading_value": 2,
    "foreign_flow": 1,
    "institutional_flow": 0,
    "program_flow": 1,
    "chart_position": 2,
    "early_stage": 1,
    "next_day_expectation": 2,
    "market_alignment": 2,
    "understanding": 2
  }
]
```

---

## CSV 예시

```csv
ticker,name,theme,material_clarity,trading_value,foreign_flow,institutional_flow,program_flow,chart_position,early_stage,next_day_expectation,market_alignment,understanding
111111,AlphaBio,바이오,2,2,1,0,1,2,1,2,2,2
```

---

## 실행 예시 명령어

```bash
python3 scripts/rank_candidates.py \
  --profile conservative \
  --input data/samples/candidates_sample.json \
  --format json

python3 scripts/rank_candidates.py \
  --profile aggressive \
  --input data/samples/candidates_sample.csv \
  --format csv \
  --output reports/aggressive_top3.json
```

---

## 흔한 오류 예시

### 1) 필수 필드 누락
- 예: `ticker` 또는 `name` 이 없음
- 처리: 경고 후 `passed=false`

### 2) 점수 범위 오류
- 예: `material_clarity=3`
- 처리: 경고 기록

### 3) 숫자형 변환 실패
- 예: `trading_value="high"`
- 처리: 경고 기록 후 해당 값은 0점 처리

### 4) 형식 지정 오류
- 예: JSON 파일인데 `--format csv` 로 실행
- 처리: 파싱 오류 발생 가능
