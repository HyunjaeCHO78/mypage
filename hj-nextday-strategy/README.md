# hj-nextday-strategy

장 마감 후 데이터를 자동 수집해 `input/market_close.json`을 만들고,
이를 기반으로 다음 거래일 전략 문서를 작성하는 프로젝트입니다.

> 핵심: 실시간 매매가 아니라 **장마감 데이터 기반의 다음날 전략 준비**에 집중합니다.

## 1) 프로젝트 목적
- 시장 마감 후 주요 지표(채권/원유/미국지수/국내 ETF) 데이터를 정리합니다.
- 정리된 입력 파일을 기준으로 다음 거래일 계획을 일관되게 작성합니다.
- 감정 매매를 줄이고, 현금 비중/손절 기준을 포함한 보수적 운영을 돕습니다.

## 2) 설치 방법
1. Python 3.9+ 설치
2. 프로젝트 폴더로 이동
3. 아래 명령 실행

```bash
pip install -r requirements.txt
```

## 3) 장마감 데이터 생성 방법
아래 스크립트를 실행하면 `input/market_close.json` 파일이 생성됩니다.

```bash
python generate_market_close.py
```

## 4) 맥 실행 방법
Finder에서 `run_mac.command`를 더블클릭하거나, 터미널에서 실행하세요.

```bash
bash run_mac.command
```

## 5) 윈도우 실행 방법
`run_windows.bat` 파일을 더블클릭해서 실행하세요.

또는 CMD에서:

```bat
run_windows.bat
```

## 6) 직접 실행 방법
운영체제와 상관없이 수동 실행도 가능합니다.

```bash
pip install -r requirements.txt
python generate_market_close.py
```

(맥에서 기본 Python이 3가 필요한 경우 `python3 generate_market_close.py` 사용)

## 7) 생성 결과 파일 설명
- `input/market_close.template.json`: 입력 구조 템플릿
- `input/market_close.json`: 장마감 수집 결과
- `output/PLAN_TOMORROW.md`: 다음 거래일 전략 문서
- `output/ORDERS_TOMORROW.csv`: 다음 거래일 주문 계획 CSV
- `output/CHECKLIST_TOMORROW.md`: 실행 체크리스트

---

## Codex 후속 프롬프트 (복붙용)

이 저장소의 AGENTS.md 규칙을 먼저 읽고 따르세요.
input/market_close.json을 읽고
다음 3개 파일을 생성하거나 갱신하세요.
1) output/PLAN_TOMORROW.md
2) output/ORDERS_TOMORROW.csv
3) output/CHECKLIST_TOMORROW.md

작성 규칙:
- 한국어
- 내일 전략만 작성
- 실시간 매매 지시 금지
- KODEX 미국10년국채선물, KODEX WTI원유선물인버스(H) 2종목만 평가
- action은 신규매수 / 추가매수 / 관망 / 일부익절 / 손절대기 중 하나
- buy_below, sell_above, stop_loss는 숫자로 작성
- 불확실하면 관망 우선
- 현금 비중 제안 포함
- 마지막에 '내일 하지 말아야 할 행동 3가지' 추가
