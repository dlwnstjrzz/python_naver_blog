#!/usr/bin/env python3
"""
네이버 블로그 자동화 GUI 실행 스크립트
"""

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# PyQt5 임포트


def check_for_updates():
    """프로그램 시작 시 업데이트 확인"""
    if not UPDATE_AVAILABLE:
        return

    try:
        # 설정 로드
        config_manager = ConfigManager()
        update_settings = config_manager.get('update_settings', {})

        # 시작 시 업데이트 확인이 비활성화된 경우 건너뛰기
        if not update_settings.get('check_update_on_startup', True):
            return

        # 업데이트 체크 실행
        updater = AutoUpdater(update_settings)
        updater.run_auto_update()

    except Exception as e:
        print(f"⚠️  업데이트 확인 중 오류: {e}")


def main():
    """메인 실행 함수"""
    # QApplication 생성
    app = QApplication(sys.argv)

    # 한국어 폰트 설정 (16px)
    try:
        font = QFont("맑은 고딕", 12)  # 12pt ≈ 16px
        app.setFont(font)
    except:
        # 맑은 고딕이 없는 경우 기본 폰트 사용 (크기만 조정)
        font = QFont()
        font.setPointSize(12)
        app.setFont(font)

    # 메인 윈도우 생성 및 표시
    try:
        window = MainWindow()
        window.show()

        # 이벤트 루프 시작
        sys.exit(app.exec_())

    except Exception as e:
        print(f"GUI 시작 중 오류 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
