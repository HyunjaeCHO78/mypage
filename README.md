# gojiro-ma-auto-system

고지로 이동평균선 투자법(5일, 20일, 40일)을 기반으로 한 Python 자동매매 프로젝트입니다. 백테스트, 시그널 스캐너, 모의매매를 하나의 CLI에서 실행할 수 있으며, 이후 실거래 API 연동이 가능하도록 브로커 인터페이스를 추상화했습니다.

> **중요:** 현재는 연구/모의매매용이며 실거래 엔진은 미구현 상태입니다.

## 주요 기능
- **백테스트 엔진**: OHLCV 데이터를 기반으로 전략 성과를 계산하고 CAGR, MDD, Win Rate, Profit Factor, Average Return, Max Consecutive Loss를 출력합니다.
- **당일 시그널 스캐너**: 종목별 최신 상태를 `stage6_candidate`, `stage1_candidate`, `pullback_candidate`, `no_signal`로 분류하고 기울기/거래량 평균 컬럼과 함께 CSV로 저장합니다.
- **모의매매 엔진**: `MockBroker`를 통해 단순 모의 주문 체결, 슬리피지, 수수료를 반영합니다.
- **확장 가능한 구조**: `BrokerBase` 추상 인터페이스를 통해 추후 키움/한국투자/증권사 REST API 등으로 연결 가능한 구조입니다.

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
- 1차 경고: `close < MA5` 2일 연속 → 로그 기록만 하고 포지션 유지
- 2차 축소: `MA5 < MA20` and `MA20 slope <= 0` → 보유 수량의 50% 축소
- 최종 청산: `close < MA20` 2일 연속 또는 `MA20 slope < 0` → 전량 청산
- 초기 손절: 진입봉 저가 이탈 또는 ATR 기반 손절 → 전량 청산

## 리스크 관리 및 분할 진입
- 포지션당 최대 손실: 총자산의 1%
- 분할 진입 비중: `30% / 40% / 30%`
- 최초 진입 후 조건이 유지되면 2차, 3차 진입 가능
- `Position`은 트랜치별 진입가/수량/진입사유를 저장
- 동시 보유 종목 수: `config.yaml`에서 조정 가능

## 설치
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```


## P0 실행 전 체크 (필수)
1. 아래 의존성을 먼저 설치하세요.
   ```bash
   pip install -r requirements.txt
   ```
2. `PyYAML`이 설치되지 않으면 `python main.py ...` 실행 시 `ModuleNotFoundError: No module named 'yaml'`로 실패할 수 있습니다.
3. 최소 실행 순서
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py --mode scan --data data/sample_ohlcv.csv
   ```
4. 빠른 점검 명령 (1~2개)
   ```bash
   python -c "import yaml; print('PyYAML OK')"
   python main.py --mode scan --data data/sample_ohlcv.csv
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

## 데이터 흐름
1. CSV 로드 (`src/utils.py`)
2. 지표 계산 (`src/indicators.py`)
3. 전략 시그널 판별 (`src/strategy.py`)
4. 실행 모드별 처리
   - `scan`: 종목별 최신 신호 분류 후 CSV 저장
   - `backtest`: 포지션/현금 관리, 분할 진입, 축소/청산, 성과 계산
   - `mock-trade`: `MockBroker`를 통한 모의 주문 처리
5. 결과를 콘솔과 `reports/` CSV에 저장

## 설정값 설명 (`config.yaml`)
- `initial_equity`: 백테스트 시작 자산
- `max_positions`: 최대 동시 보유 수
- `risk_per_trade`: 종목당 허용 손실 비율
- `atr_period`: ATR 계산 기간
- `atr_multiplier`: ATR 손절 배수
- `allocation_plan`: 분할 진입 비중
- `scanner_lookback`: 눌림목 판별을 위한 최근 봉 수
- `starting_cash`, `slippage_bps`, `fee_bps`: 모의 브로커 설정

## 현재 구현 한계
- 현재는 **연구/모의매매용** 구조이며 실거래 주문 전송, 체결 동기화, 계좌 잔고 동기화는 구현되어 있지 않습니다.
- 입력 데이터는 CSV 일봉 포맷을 가정합니다.
- 실시간 이벤트 드리븐 체결, 장중 부분체결, 종목 정지/상장폐지 등 시장 마이크로구조는 반영하지 않습니다.
- 세금, 종목별 호가단위, 거래정지, 슬리피지의 종목별 차등 모델은 단순화되어 있습니다.

## 다음 확장 항목
- 실거래 브로커 어댑터 구현 (`BrokerBase` 상속)
- 장중/분봉 데이터 대응 및 이벤트 기반 엔진 확장
- 포트폴리오 레벨 익스포저 제한, 섹터 제한, 리밸런싱 규칙 추가
- 종목별 리포트 고도화(holding period, expectancy, R-multiple)
- SQLite/PostgreSQL 기반 거래 로그/연구 결과 저장
- Telegram/Slack 알림 연동

## 예외 처리
- 필수 컬럼 누락 시 즉시 오류 발생
- 숫자형 변환 실패 행 제거
- 실행 중 예외는 로그 파일과 콘솔에 함께 기록

## 빠른 검증 예시
```bash
python main.py --mode backtest --data data/sample_ohlcv.csv
python main.py --mode scan --data data/sample_ohlcv.csv
python main.py --mode mock-trade --data data/sample_ohlcv.csv
```
