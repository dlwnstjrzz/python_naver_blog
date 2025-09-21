#!/usr/bin/env python3
"""
네이버 블로그 자동화 GUI 실행 스크립트
"""

from gui.main_window import MainWindow
import sys
import os

# 자동 업데이트 모듈 import
try:
    from utils.updater import AutoUpdater
    from utils.config_manager import ConfigManager
    UPDATE_AVAILABLE = True
    print("[INFO] 자동 업데이트 모듈 로드 성공")
except ImportError as e:
    print(f"[WARNING] 자동 업데이트 모듈 로드 실패: {e}")
    UPDATE_AVAILABLE = False

# 프로젝트 루트 경로를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# PyQt5 임포트 확인
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QFont
except ImportError:
    print("PyQt5가 설치되지 않았습니다.")
    print("다음 명령어로 설치해주세요:")
    print("pip install PyQt5")
    sys.exit(1)


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
        print(f"[WARNING] 업데이트 확인 중 오류: {e}")

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

        # 자동 업데이트 확인 (GUI 표시 후)
        print(f"[DEBUG] UPDATE_AVAILABLE: {UPDATE_AVAILABLE}")
        if UPDATE_AVAILABLE:
            try:
                from PyQt5.QtCore import QTimer
                print("[INFO] 업데이트 확인 타이머 설정 중...")
                # 윈도우가 완전히 로드된 후 업데이트 확인 (1초 후)
                QTimer.singleShot(1000, lambda: check_for_updates_with_parent(window))
                print("[INFO] 업데이트 확인 타이머 설정 완료")
            except Exception as e:
                print(f"[WARNING] 업데이트 확인 타이머 설정 실패: {e}")
        else:
            print("[WARNING] 업데이트 모듈을 사용할 수 없음")

        # 이벤트 루프 시작
        sys.exit(app.exec_())

    except Exception as e:
        print(f"GUI 시작 중 오류 발생: {str(e)}")
        sys.exit(1)

def check_for_updates_with_parent(parent_window):
    """부모 윈도우와 함께 업데이트 확인"""
    try:
        print("[INFO] 업데이트 확인 시작...")
        config_manager = ConfigManager()
        update_settings = config_manager.get('update_settings', {})
        print(f"[INFO] 업데이트 설정: {update_settings}")

        if not update_settings.get('check_update_on_startup', True):
            print("[INFO] 시작 시 업데이트 확인이 비활성화됨")
            return

        # GitHub 레포지토리가 설정되지 않았으면 확인 건너뛰기
        if not update_settings.get('github_repo'):
            print("[WARNING] GitHub 레포지토리가 설정되지 않음")
            return

        print("[INFO] 업데이터 실행 중...")
        updater = AutoUpdater(update_settings)
        updater.run_auto_update(parent_window)

    except Exception as e:
        print(f"[WARNING] 업데이트 확인 중 오류: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
