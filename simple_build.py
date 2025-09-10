#!/usr/bin/env python3
"""
간단한 exe 빌드 스크립트 (matplotlib 제외)
"""

import subprocess
import sys
import os

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def build_exe():
    """간단한 방식으로 exe 빌드"""
    
    print("Building exe file...")
    
    cmd = [
        'pyinstaller',
        '--onedir',  # onefile 대신 onedir 사용 (더 안정적)
        '--windowed',  # GUI 애플리케이션
        '--name=NaverBlogAutomation',
        '--add-data=config:config',
        '--add-data=data:data',
        '--hidden-import=selenium',
        '--hidden-import=selenium.webdriver.chrome.service',
        '--hidden-import=webdriver_manager',
        '--hidden-import=webdriver_manager.chrome',
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
        print(f"Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print("Build successful!")
        print("Check dist/NaverBlogAutomation folder for executable.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False

if __name__ == "__main__":
    success = build_exe()
    if not success:
        sys.exit(1)