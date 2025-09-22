#!/usr/bin/env python3
"""
Firebase 설정을 안전하게 관리하는 모듈
암호화된 설정 파일 + 하드코딩된 복호화 키 사용
"""

import json
import os
import base64
from cryptography.fernet import Fernet
from typing import Optional, Dict, Any

from .firebase_key import FERNET_KEY


class FirebaseConfigManager:
    """Firebase 설정 안전 관리 클래스"""

    def __init__(self):
        # 프로그램에 하드코딩된 암호화 키 (빌드 시점에 생성)
        # 실제 운영에서는 이 키를 더 복잡하게 생성하고 난독화해야 함
        self.cipher_suite = Fernet(FERNET_KEY)

        self.config_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'firebase_encrypted.dat'
        )

    def create_encrypted_config(self, firebase_config: Dict[str, Any]) -> bool:
        """Firebase 설정을 암호화하여 저장 (개발자용)"""
        try:
            # JSON을 문자열로 변환
            config_json = json.dumps(firebase_config)

            # 암호화
            encrypted_data = self.cipher_suite.encrypt(config_json.encode())

            # Base64 인코딩하여 파일에 저장
            with open(self.config_file, 'wb') as f:
                f.write(base64.b64encode(encrypted_data))

            print(f"✅ 암호화된 설정 파일 생성: {self.config_file}")
            return True

        except Exception as e:
            print(f"❌ 설정 암호화 실패: {e}")
            return False

    def get_firebase_config(self) -> Optional[Dict[str, Any]]:
        """암호화된 Firebase 설정을 복호화하여 반환 (사용자용)"""
        try:
            if not os.path.exists(self.config_file):
                print(f"❌ 설정 파일이 없습니다: {self.config_file}")
                return None

            # 파일 읽기
            with open(self.config_file, 'rb') as f:
                encrypted_data = base64.b64decode(f.read())

            # 복호화
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)

            # JSON 파싱
            config = json.loads(decrypted_data.decode())

            return config

        except Exception as e:
            print(f"❌ 설정 복호화 실패: {e}")
            return None

    def is_config_available(self) -> bool:
        """설정 파일 존재 여부 확인"""
        return os.path.exists(self.config_file)


# 전역 인스턴스
_config_manager = None


def get_firebase_config_manager() -> FirebaseConfigManager:
    """Firebase 설정 관리자 싱글톤 인스턴스"""
    global _config_manager
    if _config_manager is None:
        _config_manager = FirebaseConfigManager()
    return _config_manager


def get_firebase_config() -> Optional[Dict[str, Any]]:
    """간편한 Firebase 설정 조회 함수"""
    manager = get_firebase_config_manager()
    return manager.get_firebase_config()


if __name__ == "__main__":
    # 개발자용: 기존 firebase_config.json을 암호화
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "encrypt":
        config_path = os.path.join(os.path.dirname(
            __file__), '..', 'config', 'firebase_config.json')

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                original_config = json.load(f)

            manager = FirebaseConfigManager()
            if manager.create_encrypted_config(original_config):
                print("🔐 Firebase 설정이 암호화되어 저장되었습니다.")
                print("⚠️  이제 firebase_config.json 파일을 삭제하고 .gitignore에 추가하세요.")
            else:
                print("❌ 암호화 실패")
        else:
            print(f"❌ 원본 설정 파일을 찾을 수 없습니다: {config_path}")
    else:
        # 테스트: 설정 읽기
        config = get_firebase_config()
        if config:
            print("✅ 설정 읽기 성공")
            print(f"프로젝트 ID: {config.get('project_id', 'N/A')}")
        else:
            print("❌ 설정 읽기 실패")
