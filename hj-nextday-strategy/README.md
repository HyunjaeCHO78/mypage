# hj-nextday-strategy

장 마감 후 데이터를 자동 수집해 `input/market_close.json`을 만들고,
이를 기반으로 다음 거래일 전략 문서를 작성하는 프로젝트입니다.

> 핵심: 실시간 매매가 아니라 **장마감 데이터 기반의 다음날 전략 준비**에 집중합니다.

## 준비
1. Python 3.9+ 설치
2. 프로젝트 폴더로 이동

```bash
cd hj-nextday-strategy
```

## 실행 순서 (가장 쉬운 버전)

### 1) 의존성 설치
```bash
pip install -r requirements.txt
```

### 2) 장마감 입력 파일 생성
```bash
python generate_market_close.py
```
- 생성 파일: `input/market_close.json`
- 참고: 네트워크/패키지 문제로 시세 수집이 실패해도 JSON 파일 뼈대는 생성됩니다.

### 3) 다음날 전략 파일 작성(후속 프롬프트 사용)
아래 3개 출력 파일을 생성/갱신합니다.
- `output/PLAN_TOMORROW.md`
- `output/ORDERS_TOMORROW.csv`
- `output/CHECKLIST_TOMORROW.md`

## OS별 실행

### macOS
Finder에서 `run_mac.command` 더블클릭 또는 터미널 실행:
```bash
bash run_mac.command
```

### Windows
`run_windows.bat` 더블클릭 또는 CMD 실행:
```bat
run_windows.bat
```

## 생성 결과 파일 설명
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

---

## 초보자용 1-2-3 요약
1. `pip install -r requirements.txt` 실행
2. `python generate_market_close.py` 실행해 `input/market_close.json` 생성 확인
3. Codex 후속 프롬프트로 `output` 3개 파일 생성/갱신
