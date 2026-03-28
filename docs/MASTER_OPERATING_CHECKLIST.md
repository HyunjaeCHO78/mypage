# MASTER_OPERATING_CHECKLIST

## 목적
이 문서는 실전 운영 기준을 **conservative 중심**으로 최종 고정한 마스터 체크리스트입니다.

핵심 목표는 아래 3가지입니다.
- 사용자는 매일/매주 무엇만 하면 되는지 한눈에 본다.
- 기본 실행은 흔들리지 않게 `conservative` 중심으로 고정한다.
- 기능보다 운영 습관을 먼저 안정화한다.

---

## 1. 매일 아침/저녁 운영

### 아침
- 오늘 후보 종목을 **최대 5~10개** 안으로 압축한다.
- `templates/candidate_input_template.csv` 를 수정한다.
- 점수 항목은 `0 / 1 / 2` 로만 입력한다.
- 아직 헷갈리는 종목은 과감히 뺀다.

### 저녁
- `python3 scripts/run_daily_conservative.py` 를 실행한다.
- 결과에서 **상위 3개만** 확인한다.
- 실제 진입했든 안 했든 decision log를 남긴다.
- 장 마감 후 `result_pct`, `result_amount`, `review_note` 를 짧게 기록한다.

---

## 2. 일일 실행 순서
1. `templates/candidate_input_template.csv` 열기
2. 후보 5~10개로 줄이기
3. 점수 입력/수정
4. 아래 명령 실행

```bash
python3 scripts/run_daily_conservative.py
```

5. 아래 순서로 결과 확인
   - 콘솔 상위 3개
   - `reports/daily/YYYY-MM-DD_conservative_top3.json`
   - `reports/daily/YYYY-MM-DD_conservative_summary.txt`

6. **상위 3개만 검토**
7. 나머지는 과감히 버린다.

---

## 3. decision log 기록 순서
1. 아래 명령으로 오늘 decision log 파일 준비

```bash
python3 scripts/log_daily_decision.py --init-only
```

2. `logs/daily_decisions/YYYY-MM-DD_decision_log.csv` 열기
3. 상위 후보 중 실제 판단한 종목만 기록
4. 진입했으면:
   - `entered=yes`
   - `entry_reason` 작성
   - `result_pct`, `result_amount` 입력
5. 진입 안 했어도:
   - `entered=no`
   - `no_entry_reason` 작성
   - `result_pct=0`, `result_amount=0`
6. 마지막에 `review_note` 를 짧게 적기

중요 원칙:
- **진입 안 했어도 decision log는 남긴다.**
- 후보 압축 결과와 실제 행동 결과를 분리하지 않는다.

---

## 4. 주간 복기 순서
주말에는 아래 명령을 실행합니다.

```bash
python3 scripts/generate_weekly_report.py
```

확인 순서:
1. `reports/weekly/YYYY-MM-DD_weekly_conservative_report.md` 열기
2. 후보 압축 결과 요약 먼저 보기
3. 실제 의사결정/실전 결과 요약 보기
4. 아래 항목은 **꼭 확인**하기
   - 평균 `result_pct`
   - 가장 자주 나온 `no_entry_reason`
   - `review_note` 요약
5. 다음 주에 유지할 기준 / 버릴 습관 1~2개만 정리하기

---

## 5. 금지사항
- 하루 후보를 10개 넘게 넣지 않는다.
- 기본 실행을 공격형으로 바꾸지 않는다.
- 상위 3개 외 종목을 계속 미련 있게 붙잡지 않는다.
- 진입 안 한 날 decision log를 비워 두지 않는다.
- `result_pct`, `result_amount` 를 비워 두지 않는다.
- 점수를 감으로 계속 바꾸면서 기준을 흔들지 않는다.

### 공격형을 쓰면 안 되는 경우
- 아직 점수 기준이 자주 흔들릴 때
- 처음 20거래일 적응 기간일 때
- 후보를 5~10개로도 못 줄일 때
- 보수형 결과 복기도 아직 안정되지 않았을 때
- 장세가 애매하고 변동성만 클 때

### 예외적으로 공격형을 시험해볼 수 있는 경우
- 장이 매우 강하고 추세가 명확할 때
- 보수형 결과와 비교용으로만 보고 싶을 때
- 초입 탄력 종목을 따로 관찰해야 할 때
- 20거래일 이상 보수형 운영 기록이 쌓였을 때

---

## 6. 추천 운영 습관
- 처음 **20거래일은 보수형만 사용**한다.
- 매일 같은 시간에 같은 순서로 실행한다.
- 점수 입력은 길게 고민하지 말고 0/1/2 기준으로 짧게 끝낸다.
- daily summary와 decision log를 하루에 같이 마무리한다.
- 주말에는 weekly report를 보고 다음 주 기준 1~2개만 조정한다.
- review_note는 길게 쓰지 말고 다음 판단에 필요한 한 줄만 남긴다.

### 처음 20거래일 운영 원칙
1. 기본 실행은 항상 conservative
2. 후보는 최대 5~10개
3. 상위 3개만 검토
4. 진입 안 했어도 decision log 기록
5. 주말에는 weekly report 실행
6. 평균 `result_pct`, `no_entry_reason`, `review_note` 를 꼭 본다
7. 공격형은 비교용으로도 최대한 늦게 사용한다
