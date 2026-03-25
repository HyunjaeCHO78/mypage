#!/bin/bash

# 스크립트 파일이 위치한 현재 프로젝트 폴더로 이동
cd "$(dirname "$0")"

# 의존성 설치
pip install -r requirements.txt

# 장 마감 데이터 생성
python3 generate_market_close.py

echo "완료: input/market_close.json 생성 작업이 끝났습니다."
read -p "엔터를 누르면 종료합니다..."
