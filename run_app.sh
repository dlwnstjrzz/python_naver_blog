#!/bin/bash

# 네이버 블로그 자동화 실행 스크립트
echo "🚀 네이버 블로그 자동화 프로그램 시작"

# Python 경로 확인
PYTHON_PATH=$(which python)
echo "Python 경로: $PYTHON_PATH"

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# 필요한 모듈 확인
echo "📦 모듈 확인 중..."
python -c "import PyQt5; import selenium; import google.generativeai; print('✅ 모든 모듈 정상')" || {
    echo "❌ 필요한 모듈이 설치되지 않았습니다."
    echo "다음 명령어를 실행해주세요:"
    echo "pip install -r requirements.txt"
    exit 1
}

# GUI 프로그램 실행
echo "🎯 GUI 프로그램 실행 중..."
python main.py

echo "✅ 프로그램 종료"