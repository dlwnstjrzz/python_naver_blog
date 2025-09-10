#!/usr/bin/env python3
"""
pip 환경용 빌드 스크립트
"""

import subprocess
import sys
import os

def build_with_pip_env():
    """pip 환경에서 빌드"""
    
    print("🚀 pip 환경으로 exe 파일 빌드 시작...")
    
    # PyInstaller 명령 (더 보수적인 설정)
    cmd = [
        'python', '-m', 'PyInstaller',
        '--onefile',  # 단일 파일로 생성
        '--windowed',
        '--name=NaverBlogAutomation', 
        '--add-data=config:config',
        '--add-data=data:data',
        # PyQt5 관련 명시적 임포트
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtWidgets', 
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.sip',
        # 다른 모듈들
        '--hidden-import=selenium',
        '--hidden-import=selenium.webdriver',
        '--hidden-import=selenium.webdriver.common.by',
        '--hidden-import=google.generativeai',
        '--hidden-import=automation.blog_automation',
        '--hidden-import=automation.buddy_manager',
        '--hidden-import=automation.neighbor_connect', 
        '--hidden-import=automation.post_interaction',
        '--hidden-import=utils.config_manager',
        '--hidden-import=utils.logger',
        '--hidden-import=utils.ai_comment_generator',
        '--hidden-import=gui.main_window',
        # 문제가 되는 모듈들 제외
        '--exclude-module=matplotlib',
        '--exclude-module=numpy', 
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=IPython',
        '--exclude-module=jupyter',
        '--clean',
        'main.py'
    ]
    
    try:
        print(f"실행 명령어: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print("✅ 빌드 성공!")
        print("📁 dist/NaverBlogAutomation에서 실행 파일을 확인하세요.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False

if __name__ == "__main__":
    success = build_with_pip_env()
    if not success:
        sys.exit(1)