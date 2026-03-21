# 운영 워크플로우(초안)

1. `universe/kospi200_universe.csv` 준비(종목코드/종목명/시장/섹터)
2. `scripts/collect_reports.py` 실행해 기본 결과 테이블 골격 생성
3. (향후) 수집/파싱 스크립트로 목표가/의견/날짜/증권사 정보 보강
4. `scripts/calculate_gap.py`로 괴리율/업사이드 계산
5. `scripts/export_final_csv.py`로 최종 CSV 정렬·저장
6. 로그(`logs/run_log.txt`)와 문서에 제한사항/수동보완 내역 기록
