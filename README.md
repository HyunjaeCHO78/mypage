# gojiro-ma-auto-system

고지로 이동평균선 투자법(5일, 20일, 40일)을 기반으로 한 Python 자동매매 프로젝트입니다. 백테스트, 시그널 스캐너, 모의매매를 하나의 CLI에서 실행할 수 있으며, 이후 실거래 API 연동이 가능하도록 브로커 인터페이스를 추상화했습니다.

> **중요:** 현재 구현은 **연구/모의매매용**입니다. **실거래 주문 API, 체결 동기화, 계좌 연동은 아직 구현되어 있지 않습니다.**

## 현재 구현 범위
- **백테스트 엔진**: OHLCV 데이터를 기반으로 분할 진입, 부분 청산, 최종 청산, ATR/저가 손절을 시뮬레이션합니다.
- **당일 시그널 스캐너**: 종목별 최신 상태를 `stage6_candidate`, `stage1_candidate`, `pullback_candidate`, `no_signal`로 분류하고 이동평균 기울기/거래량 평균을 CSV로 저장합니다.
- **모의매매 엔진**: `MockBroker`를 통해 단순 주문 체결, 슬리피지, 수수료를 반영합니다.
- **브로커 확장 포인트**: `BrokerBase`에 주문 취소, 주문 상태 조회, 평균단가 조회 인터페이스가 포함되어 추후 실거래 어댑터 추가가 가능합니다.

## 현재 한계
- 실거래 브로커 API(키움/한국투자/증권사 REST/WebSocket) 연동은 미구현입니다.
- 입력 데이터는 CSV 일봉 포맷을 가정합니다.
- 장중 이벤트 드리븐 체결, 부분 체결, 거래정지/상장폐지 등 시장 미시구조는 반영하지 않습니다.
- 세금, 종목별 호가단위, 거래정지, 종목별 차등 슬리피지 모델은 단순화되어 있습니다.

## 디렉터리 구조
```text
.
├── config.yaml
├── data/
│   └── sample_ohlcv.csv
├── logs/
├── reports/
├── main.py
├── requirements.txt
└── src/
    ├── backtester.py
    ├── broker_base.py
    ├── broker_mock.py
    ├── indicators.py
    ├── portfolio.py
    ├── risk.py
    ├── scanner.py
    ├── strategy.py
    └── utils.py
```

## 전략 규칙 구현
### 1) 초기 진입 / stage6 / 분빨파
- `MA5 > MA40 > MA20`
- `MA5 slope > 0`
- `close > MA5`
- `volume > SMA(volume, 20)`

### 2) 확정 진입 / stage1 / 정배열
- `MA5 > MA20 > MA40`
- `MA5 slope > 0`
- `MA20 slope > 0`
- `MA40 slope >= 0`
- `close > MA5`

### 3) 눌림목 재진입
- 최근 20봉 이내 정배열 이력 존재
- 직전 봉에서 MA5 또는 MA20 부근까지 눌림 발생
- 현재 종가가 다시 MA5 상향 회복
- `MA20 slope > 0`, `MA40 slope >= 0`

### 4) 청산 / 축소
- 1차 경고: `close < MA5` 2일 연속 → 로그만 남기고 포지션 유지
- 2차 축소: `MA5 < MA20` and `MA20 slope <= 0` → 보유 수량의 50% 부분 청산
- 최종 청산: `close < MA20` 2일 연속 또는 `MA20 slope < 0` → 전량 청산
- 초기 손절: 진입봉 저가 이탈 또는 ATR 기반 손절 → 전량 청산

## 리스크 관리 및 분할 진입
- 포지션당 최대 손실: 총자산의 1%
- 분할 진입 비중: `30% / 40% / 30%`
- 최초 진입 후 조건이 유지되면 2차, 3차 진입이 순차적으로 반영됩니다.
- `tranche_index`를 실제 진입 단계 제어에 사용합니다.
- `Position`은 트랜치별 진입가/수량/진입사유를 저장하며 평균단가와 보유수량이 단계별로 갱신됩니다.

## 성과 리포트
백테스트 완료 시 `reports/` 아래에 다음 파일이 저장됩니다.
- `backtest_trades.csv`: 전체 매매 로그
- `backtest_equity.csv`: 일자별 포트폴리오 자산 곡선
- `backtest_portfolio_metrics.csv`: 전체 포트폴리오 성과 지표
- `backtest_symbol_summary.csv`: 종목별 성과 요약 (`realized_pnl`, `average_return`, `win_rate`, `profit_factor`, `max_consecutive_loss`)

## 설치
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 샘플 데이터
`data/sample_ohlcv.csv`는 다음 컬럼을 포함합니다.
- `date, open, high, low, close, volume, symbol`

샘플 데이터는 3개 종목(`AAA`, `BBB`, `CCC`)의 일봉 OHLCV로 구성되어 있으며, 바로 실행 가능한 상태입니다.

## 실행 방법
### 1. 백테스트 실행
```bash
python main.py --mode backtest --data data/sample_ohlcv.csv
```
실행 결과:
- 콘솔에 `CAGR`, `MDD`, `Win Rate`, `Profit Factor`, `Average Return`, `Max Consecutive Loss` 출력
- 콘솔에 종목별 성과 요약 테이블 출력
- `reports/backtest_trades.csv`
- `reports/backtest_equity.csv`
- `reports/backtest_portfolio_metrics.csv`
- `reports/backtest_symbol_summary.csv`
- 로그: `logs/run.log`

### 2. 시그널 스캔 실행
```bash
python main.py --mode scan --data data/sample_ohlcv.csv
```
실행 결과:
- 콘솔에 최신 종목 분류 결과 출력
- `reports/scan_results.csv` 저장
- 결과 컬럼: `signal`, `ma5_slope`, `ma20_slope`, `ma40_slope`, `volume_sma20` 포함

### 3. 모의매매 실행
```bash
python main.py --mode mock-trade --data data/sample_ohlcv.csv
```
실행 결과:
- 콘솔에 주문/축소/경고 로그 내역 출력
- `reports/mock_trade_orders.csv`

## 빠른 검증 예시
```bash
python main.py --mode backtest --data data/sample_ohlcv.csv
python main.py --mode scan --data data/sample_ohlcv.csv
python main.py --mode mock-trade --data data/sample_ohlcv.csv
```

## 다음 확장 항목
- 실거래 브로커 어댑터 구현 (`BrokerBase` 상속)
- 장중/분봉 데이터 대응 및 이벤트 기반 엔진 확장
- 포트폴리오 레벨 익스포저 제한, 섹터 제한, 리밸런싱 규칙 추가
- 종목별 리포트 고도화(holding period, expectancy, R-multiple)
- SQLite/PostgreSQL 기반 거래 로그/연구 결과 저장
- Telegram/Slack 알림 연동
