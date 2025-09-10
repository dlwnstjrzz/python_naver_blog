#!/usr/bin/env python3
"""
간단한 exe 빌드 스크립트 (matplotlib 제외)
"""

import subprocess
import sys
import os

def build_exe():
    """간단한 방식으로 exe 빌드"""
    
    print("🚀 간단한 방식으로 exe 파일 빌드 시작...")
    
    cmd = [
        'pyinstaller',
        '--onedir',  # onefile 대신 onedir 사용 (더 안정적)
        '--windowed',  # GUI 애플리케이션
        '--name=NaverBlogAutomation',
        '--add-data=config:config',
        '--add-data=data:data',
        '--hidden-import=selenium',
        '--hidden-import=PyQt5',
        '--hidden-import=google.generativeai',
        '--hidden-import=automation',
        '--hidden-import=utils',
        '--hidden-import=gui',
        '--exclude-module=matplotlib',  # matplotlib 제외
        '--exclude-module=numpy',  # numpy 제외
        '--exclude-module=pandas',  # pandas 제외
        '--exclude-module=scipy',  # scipy 제외
        '--clean',
        'main.py'
    ]
    
    try:
        print(f"실행 명령어: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print("✅ 빌드 성공!")
        print("📁 dist/NaverBlogAutomation 폴더에서 실행 파일을 확인하세요.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False

if __name__ == "__main__":
    success = build_exe()
    if not success:
        sys.exit(1)