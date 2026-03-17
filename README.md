# mypage 데이터 파이프라인 (1차/2차)

이 저장소는 **구조 검증과 최소 실행 가능성 확보**를 목표로 하는 간단한 파이프라인 예시입니다.

## 실행 목적
- 1차: 폴더/스크립트 구조를 먼저 만들고 실행 가능한 흐름을 확보
- 2차: 외부 패키지 설치 실패 환경에서도 표준 라이브러리로 동작

## 설치
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 외부 패키지 설치가 프록시(예: 403) 등으로 실패하더라도,
> 본 프로젝트는 **표준 라이브러리 모드**로 기본 동작합니다.
> 즉, pandas 없이도 CSV 읽기/쓰기 및 기본 산출물 생성이 가능합니다.

## 실행 순서
```bash
python scripts/build_universe.py
python scripts/collect_reports.py
python scripts/calculate_gap.py
python scripts/export_final_csv.py
```

최종 결과물:
- `output/kospi200_targetprice_table.csv`

## 예시 데이터 안내
- `data/universe_example.csv`는 실제 운용 데이터가 아닌 **예시 데이터**입니다.
