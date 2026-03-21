# workflow

## 1차 단계 (구조 중심)
- 목적: 스크립트 실행 골격 확보
- 특징:
  - 실제 외부 데이터 수집보다 파일 입출력 경로 확인이 우선
  - 예시 CSV를 기준으로 파이프라인이 끊기지 않고 실행되는지 점검
  - 결과 CSV가 비어 있어도 템플릿 형태(헤더 포함)로 생성되면 통과

## 2차 단계 (표준 라이브러리 안정화)
- 목적: 외부 패키지 설치 실패 환경에서도 최소 실행 보장
- 변경점:
  - pandas를 필수 의존성에서 제외(선택 의존성)
  - `csv`, `pathlib`, `datetime` 중심으로 스크립트 동작
  - `current_price` 또는 `target_price`가 없어도 에러 없이 처리
  - `calculate_gap.py`는 값이 없으면 `gap_pct`를 빈 값으로 저장
  - `export_final_csv.py`는 항상 `output/kospi200_targetprice_table.csv`를 생성

## 단계별 산출물
1. `build_universe.py` → `output/universe_stage1.csv`
2. `collect_reports.py` → `output/reports_stage1.csv`
3. `calculate_gap.py` → `output/gap_stage2.csv`
4. `export_final_csv.py` → `output/kospi200_targetprice_table.csv`
