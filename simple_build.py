#!/usr/bin/env python3
"""
간단한 exe 빌드 스크립트 (matplotlib 제외)
"""

import subprocess
import sys
import os
import json

from utils.firebase_key import FERNET_KEY
from utils.firebase_logging import append_firebase_log

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def create_encrypted_firebase_config():
    """빌드 시 환경변수에서 암호화된 Firebase 설정 파일 생성"""
    try:
        from cryptography.fernet import Fernet
        import base64

        append_firebase_log("[build] Firebase config encryption step started")

        # 환경변수에서 Firebase 설정 읽기
        firebase_config = {
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "universe_domain": "googleapis.com"
        }

        # 필수 환경변수 확인
        if not all([firebase_config["project_id"], firebase_config["private_key"], firebase_config["client_email"]]):
            append_firebase_log(
                "[build] Firebase env missing - project_id:%s private_key:%s client_email:%s" % (
                    bool(firebase_config["project_id"]),
                    bool(firebase_config["private_key"]),
                    bool(firebase_config["client_email"]),
                )
            )
            print("환경변수에서 Firebase 설정을 찾을 수 없습니다. 빌드를 계속합니다...")
            return False

        # private_key 처리 (개행 문자 복원)
        if firebase_config["private_key"] and '\\n' in firebase_config["private_key"]:
            firebase_config["private_key"] = firebase_config["private_key"].replace('\\n', '\n')

        # 암호화 키 (실제 배포시에는 더 복잡한 키 사용)
        cipher_suite = Fernet(FERNET_KEY)

        # config 디렉토리 생성
        config_dir = "config"
        os.makedirs(config_dir, exist_ok=True)

        # JSON을 문자열로 변환하고 암호화
        config_json = json.dumps(firebase_config)
        encrypted_data = cipher_suite.encrypt(config_json.encode())

        # Base64 인코딩하여 파일에 저장
        config_path = os.path.join(config_dir, "firebase_encrypted.dat")
        with open(config_path, 'wb') as f:
            f.write(base64.b64encode(encrypted_data))

        print(f"암호화된 Firebase 설정 파일 생성 완료: {config_path}")
        append_firebase_log(f"[build] Firebase config encrypted -> {config_path}")
        return True

    except Exception as e:
        print(f"암호화된 Firebase 설정 파일 생성 실패: {e}")
        append_firebase_log(f"[build] Firebase config encryption failed: {e}")
        return False

def build_exe():
    """간단한 방식으로 exe 빌드"""

    print("Building exe file...")

    # 빌드 시 암호화된 Firebase 설정 파일 생성
    create_encrypted_firebase_config()
    
    cmd = [
        'pyinstaller',
        '--onedir',  # onefile 대신 onedir 사용 (더 안정적)
        '--windowed',  # GUI 애플리케이션
        '--name=NaverBlogAutomation',
        '--add-data=config:config',
        '--add-data=data:data',
        '--add-data=image:image',
        '--hidden-import=selenium',
        '--hidden-import=selenium.webdriver.chrome.service',
        '--hidden-import=webdriver_manager',
        '--hidden-import=webdriver_manager.chrome',
        '--hidden-import=PyQt5',
        '--hidden-import=google.generativeai',
        '--hidden-import=automation',
        '--hidden-import=utils',
        '--hidden-import=utils.updater',
        '--hidden-import=utils.config_manager',
        '--hidden-import=version',
        '--hidden-import=requests',
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
