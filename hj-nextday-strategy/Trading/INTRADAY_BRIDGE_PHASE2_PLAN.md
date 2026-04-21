# KIS Websocket Bridge (검증단계 2-1) 초안

## 목적
- KIS websocket 실시간 체결/호가/거래대금 수신 기반을 추가한다.
- 자동주문 없이 장중 감시 + execution score 반영 입력까지만 수행한다.

## 신호 분리 규칙
- `market_phase=intraday`: 임시 신호(`intraday_signal_type=temporary`)만 생성
- `market_phase=post_close`: 기존 `INTEGRATED_SIGNAL_BOARD.json` 확정 신호 사용
- 장중 점수는 보조 신호이며 장후 확정 점수와 별도로 저장/해석

## 상태 저장 파일
- `data/state/websocket_state.json`
- 주요 필드
  - `last_connected_at`
  - `subscriptions`
  - `recent_messages`
  - `last_error`
  - `reconnect_count`

## 운영 로그
- `logs/websocket_bridge.log` (런타임)
- 샘플: `logs/websocket_bridge.sample.log`
- `logs/order_bridge.log`와 분리 운영

## INTEGRATED_SIGNAL_BOARD 호환성
- 기존 JSON 파일을 직접 수정하지 않는다.
- watchlist는 `data/watchlist.yaml` 우선, 없으면 `INTEGRATED_SIGNAL_BOARD.json` fallback 로딩
- execution score 엔진에는 별도 `intraday` 입력 payload 전달
