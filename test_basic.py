#!/usr/bin/env python3
"""
기본 기능 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import ConfigManager
from utils.logger import setup_logger

def test_config_manager():
    """설정 관리자 테스트"""
    print("=== ConfigManager 테스트 ===")
    
    config = ConfigManager()
    
    # 기본값 확인
    print(f"기본 블로그 개수: {config.get('blog_count')}")
    print(f"기본 댓글 옵션: {config.get('comment_option')}")
    
    # 설정 변경
    config.set('test_key', 'test_value')
    print(f"테스트 키 설정: {config.get('test_key')}")
    
    # 설정 저장 테스트
    if config.save_config():
        print("✅ 설정 저장 성공")
    else:
        print("❌ 설정 저장 실패")
    
    print()

def test_logger():
    """로거 테스트"""
    print("=== Logger 테스트 ===")
    
    logger = setup_logger()
    logger.info("테스트 정보 메시지")
    logger.warning("테스트 경고 메시지")
    logger.error("테스트 에러 메시지")
    
    print("✅ 로거 테스트 완료")
    print()

def test_imports():
    """모든 모듈 임포트 테스트"""
    print("=== Import 테스트 ===")
    
    try:
        from automation.naver_login import NaverLogin
        print("✅ NaverLogin 임포트 성공")
    except Exception as e:
        print(f"❌ NaverLogin 임포트 실패: {e}")
    
    try:
        from automation.utils import AutomationUtils
        print("✅ AutomationUtils 임포트 성공")
    except Exception as e:
        print(f"❌ AutomationUtils 임포트 실패: {e}")
    
    try:
        from gui.main_window import MainWindow
        print("✅ MainWindow 임포트 성공")
    except Exception as e:
        print(f"❌ MainWindow 임포트 실패: {e}")
    
    print()

if __name__ == "__main__":
    print("🚀 네이버 블로그 자동화 프로그램 기본 테스트\n")
    
    test_imports()
    test_config_manager()
    test_logger()
    
    print("✨ 모든 기본 테스트 완료!")
    print("\n📌 다음 단계:")
    print("1. 가상환경 활성화: python -m venv venv && source venv/bin/activate")
    print("2. GUI 실행: python main.py")
    print("3. 네이버 계정 정보 입력 후 테스트")