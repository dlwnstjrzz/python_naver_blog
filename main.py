#!/usr/bin/env python3
"""
네이버 블로그 서로이웃 자동화 프로그램
"""
from utils.logger import setup_logger
from gui.main_window import MainWindow
import sys
import os

# 프로젝트 루트 디렉터리를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    """메인 함수"""
    logger = setup_logger()
    logger.info("네이버 블로그 자동화 프로그램 시작")

    try:
        app = MainWindow()
        app.run()
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
