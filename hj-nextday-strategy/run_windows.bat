@echo off
chcp 65001 > nul

REM 배치 파일이 위치한 현재 프로젝트 폴더로 이동
cd /d "%~dp0"

REM 의존성 설치
pip install -r requirements.txt

REM 장 마감 데이터 생성
python generate_market_close.py

echo 완료: input\market_close.json 생성 작업이 끝났습니다.
pause
