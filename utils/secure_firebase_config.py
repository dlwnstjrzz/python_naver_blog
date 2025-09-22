#!/usr/bin/env python3
"""
보안 Firebase 설정 관리
환경변수를 사용한 보안 설정 로드
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv


def get_firebase_config_from_env() -> Optional[Dict[str, Any]]:
    """환경변수에서 Firebase 설정 로드 (로컬은 .env, CI는 환경변수)"""
    try:
        # .env 파일 로드 (로컬 개발 환경용)
        load_dotenv()

        # 필수 환경변수 확인
        required_vars = [
            'FIREBASE_PROJECT_ID',
            'FIREBASE_PRIVATE_KEY',
            'FIREBASE_CLIENT_EMAIL'
        ]

        # 환경변수 존재 여부 확인
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            print(f"다음 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
            return None

        # private_key 처리 (개행 문자 복원)
        private_key = os.getenv('FIREBASE_PRIVATE_KEY')
        if private_key:
            # GitHub Actions에서는 이미 올바른 형태로 저장되어 있을 수 있음
            if '\\n' in private_key:
                private_key = private_key.replace('\\n', '\n')

        # Firebase 설정 구성
        config = {
            "type": os.getenv('FIREBASE_TYPE', 'service_account'),
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": private_key,
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
            "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL'),
            "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN', 'googleapis.com')
        }

        print("✅ 환경변수에서 Firebase 설정 로드 성공")
        return config

    except Exception as e:
        print(f"❌ 환경변수에서 Firebase 설정 로드 실패: {e}")
        return None


def get_secure_firebase_config(license_key: str = None) -> Optional[Dict[str, Any]]:
    """보안 Firebase 설정 가져오기 (환경변수 우선, 파일 폴백)"""
    import json

    # 1. 환경변수에서 Firebase 설정 로드 시도
    config = get_firebase_config_from_env()
    if config:
        return config

    # 2. 로컬 파일에서 폴백
    try:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'firebase_config.json'
        )

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print("✅ 로컬 firebase_config.json에서 설정 로드")
            return config
        else:
            print(f"⚠️ 로컬 설정 파일도 없습니다: {config_path}")
    except Exception as e:
        print(f"❌ 로컬 설정 파일 로드 실패: {e}")

    print("❌ Firebase 설정을 로드할 수 없습니다. 환경변수 또는 config/firebase_config.json을 확인하세요.")
    return None


if __name__ == "__main__":
    # 테스트
    config = get_secure_firebase_config()
    if config:
        print(f"프로젝트 ID: {config.get('project_id', 'N/A')}")
    else:
        print("Firebase 설정 로드 실패")
