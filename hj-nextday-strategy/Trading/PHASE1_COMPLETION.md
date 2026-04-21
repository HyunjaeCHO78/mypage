# Trading/통합감시엔진 검증단계 1차 완료

## 요약
- 통합감시엔진 검증단계 1차 구조를 반영함
- 샘플 시나리오 기반 점수 계산/분류 검증 흐름 추가
- INTEGRATED_SIGNAL_BOARD.json 출력 구조 고정
- VALIDATION_REPORT.md 검증 보고서 추가
- scenarios_validation_input.json / validate_integrated_signal_board.py 추가

## 반영 내용
- 분류 체계 5단계 고정
  - 제외 / 관찰 / 후보 / 매수대기 / 실행검토
- raw_classification / final_classification 분리
- adjustments 필드 반영
- evidence_summary / next_action / bridge_ready 구조 반영
- 샘플 시나리오 기반 기대값/실제값 비교 구조 반영

## 검증 포인트
- 산업사이클 2단계 + COT 우호 + 외국인 순매수 강세 시 상위 분류 확인
- 산업사이클 4단계 이상 시 보수적 하향 규칙 확인
- 외국인 순매수 단독 강세 시 실행검토 제한 확인
- 대표주/후발주 정렬 여부에 따른 실행점수 반영 확인
- 기존 실매매 프로젝트가 읽기 쉬운 JSON 구조 유지 확인

## 생성 파일
- Trading/INTEGRATED_SIGNAL_BOARD.json
- Trading/VALIDATION_REPORT.md
- Trading/scenarios_validation_input.json
- Trading/validate_integrated_signal_board.py

## 다음 단계
- 검증 시나리오 결과 최종 확인
- KIS websocket 연결 이전에 분류/보정 로직 고정
- 이후 kis_websocket_bridge.py 연동 단계로 진행
