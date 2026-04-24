# dry-run 시뮬레이션 연결 가이드

## 1. 이번 단계에서 검증되는 범위
- 장중 입력(`INTRADAY_SIGNAL_BRIDGE.json`)을 dry-run 입력으로 연결한다.
- 장후 입력(`INTEGRATED_SIGNAL_BOARD.json`)을 dry-run 입력으로 연결한다.
- 최종 판단 레이어 규칙(pass/hold/block/review)을 같은 엔진에서 평가한다.
- 결과를 `dry_run_results.json`, `dry_run.log`로 저장하고 실제 주문 API는 호출하지 않는다.

## 2. 실행 방법
```bash
python Trading/run_dry_run_simulation.py
```

실행 후 생성 파일:
- `Trading/dry_run_results.json`
- `Trading/dry_run.log`

## 3. 출력 해석 방법
`dry_run_results.json` 각 레코드는 아래 필드를 포함한다.
- `ticker`
- `market_phase`
- `final_decision`
- `decision_reason`
- `decision_flags`
- `required_next_action`
- `decision_timestamp`
- `source_signal_type`

판정 해석:
- `pass`: 주문 검토 후보
- `hold`: 재평가 전 보류
- `block`: 당일 제외
- `review`: 수동 검토 필요

## 4. 샘플 시뮬레이션 검증
- `Trading/examples/dry_run_scenarios.sample.json`에 pass/hold/block/review 샘플을 포함했다.
- 본 샘플은 실데이터 브리지 결과와 별도로 dry-run 판정 커버리지를 확인하기 위한 용도다.

## 5. 실주문 연결 전 추가 확인사항
1. 임계치(`total_score`, `intraday_execution_score`, `execution_priority`)의 주간 리플레이 보정
2. 차단 플래그(`INDUSTRY_STAGE_HIGH`, `FOREIGN_FLOW_ONLY_STRONG` 등)의 오탐률 확인
3. review 케이스 수동 승인 프로세스(담당자/체크리스트/승인 로그) 확정
4. 주문 API 연결 시점에도 `order_api_called` 가드가 환경별로 안전하게 분기되는지 재검증
