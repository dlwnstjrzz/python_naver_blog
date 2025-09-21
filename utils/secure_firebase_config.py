#!/usr/bin/env python3
"""
보안 Firebase 설정 관리
환경변수를 사용한 보안 설정 로드
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv


def get_firebase_config_from_env() -> Optional[Dict[str, Any]]:
    """환경변수에서 Firebase 설정 로드"""
    try:
        # .env 파일 로드
        load_dotenv()

        # 필수 환경변수 확인
        required_vars = [
            'FIREBASE_PROJECT_ID',
            'FIREBASE_PRIVATE_KEY',
            'FIREBASE_CLIENT_EMAIL'
        ]

        for var in required_vars:
            if not os.getenv(var):
                print(f"환경변수 {var}가 설정되지 않았습니다.")
                return None

        # Firebase 설정 구성
        config = {
            "type": os.getenv('FIREBASE_TYPE', 'service_account'),
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
            "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL'),
            "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN', 'googleapis.com')
        }

        return config

    except Exception as e:
        print(f"환경변수에서 Firebase 설정 로드 실패: {e}")
        return None


def get_secure_firebase_config(license_key: str = None) -> Optional[Dict[str, Any]]:
    """보안 Firebase 설정 가져오기"""
    # 환경변수에서 Firebase 설정 로드
    config = get_firebase_config_from_env()

    if config:
        return config
    else:
        print("환경변수에서 Firebase 설정을 로드할 수 없습니다.")
        return None


if __name__ == "__main__":
    # 테스트
    config = get_secure_firebase_config()
    if config:
        print(f"프로젝트 ID: {config.get('project_id', 'N/A')}")
    else:
        print("Firebase 설정 로드 실패")
