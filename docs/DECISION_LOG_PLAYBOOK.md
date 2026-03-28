# DECISION_LOG_PLAYBOOK

## 목적
이 문서는 상위 3개 후보를 본 뒤,
사용자가 실제로 **진입했는지/안 했는지** 와 그 결과를 간단히 기록하는 방법을 설명합니다.

핵심은 후보 압축 다음 단계에서
매일 최소한의 실전 판단만 남기는 것입니다.

---

## 언제 기록하는가?
추천 시점은 아래 두 번입니다.

1. **장중 또는 진입 직후**: `entered`, `entry_reason`, `no_entry_reason` 기록
2. **장 마감 후**: `result_pct`, `result_amount`, `review_note` 기록

즉, 하루에 완전히 상세한 매매일지를 쓰는 것이 아니라,
최종 판단과 결과만 남기는 간단한 로그입니다.

---

## 어떤 항목만 입력하면 되는가?
아래 컬럼만 입력하면 됩니다.

- `date`: 날짜
- `ticker`: 종목 코드
- `name`: 종목명
- `selected_rank`: 상위 후보 순위(1~3)
- `entered`: 실제 진입 여부 (`yes` / `no`)
- `entry_reason`: 진입했다면 이유
- `no_entry_reason`: 진입 안 했다면 이유
- `result_pct`: 수익률 또는 손실률
- `result_amount`: 손익 금액
- `review_note`: 짧은 복기 메모

---

## 진입한 경우 예시
- `entered=yes`
- `entry_reason=재료와 거래대금이 가장 명확했고 계획한 자리 도달`
- `no_entry_reason=` 비움
- `result_pct=2.5`
- `result_amount=125000`
- `review_note=계획대로 진입/청산했고 재진입은 하지 않음`

---

## 진입 안 한 경우 예시
- `entered=no`
- `entry_reason=` 비움
- `no_entry_reason=장중 변동성이 너무 커서 보류`
- `result_pct=0`
- `result_amount=0`
- `review_note=후보는 좋았지만 내 기준 타점이 아니었음`

---

## 결과 입력 방법

### result_pct
- 수익이면 양수
- 손실이면 음수
- 진입 안 했으면 `0`

예:
- `3.2`
- `-1.4`
- `0`

### result_amount
- 실제 손익 금액
- 진입 안 했으면 `0`

예:
- `150000`
- `-80000`
- `0`

---

## review_note 에 무엇을 적어야 하는가?
너무 길게 쓰지 말고 아래 중 1~2개만 남기면 됩니다.

- 왜 들어갔는가 / 왜 안 들어갔는가
- 계획과 실제가 어떻게 달랐는가
- 다음에 같은 상황이면 어떻게 할 것인가
- 점수는 높았지만 진입하지 않은 이유는 무엇인가

즉, **다음 판단을 더 잘하기 위한 짧은 복기 메모**만 적으면 됩니다.

---

## 흔한 실수

### 1) entered 를 안 적음
- `yes` 또는 `no` 중 하나는 꼭 입력

### 2) 진입 안 했는데 result 값을 비워 둠
- 진입 안 했으면 `0` 으로 적기

### 3) entry_reason 와 no_entry_reason 를 둘 다 채움
- 진입했으면 `entry_reason`
- 진입 안 했으면 `no_entry_reason`

### 4) review_note 를 너무 길게 씀
- 한 줄 또는 두 줄이면 충분

### 5) 상위 후보 순위를 안 적음
- `selected_rank` 는 나중에 주간 분석에서 중요하므로 꼭 남기기

---

## 실행 흐름 예시
1. `python3 scripts/run_daily_conservative.py`
2. 상위 3개 후보 확인
3. `python3 scripts/log_daily_decision.py --init-only`
4. 생성된 로그 파일 열기
5. 최종 진입 여부와 결과 입력
