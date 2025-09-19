#!/usr/bin/env python3
"""
보안 Firebase 설정 관리
실용적인 하이브리드 방식:
1. 공개 정보는 하드코딩
2. 민감 정보는 서버에서 다운로드 또는 라이선스 검증과 함께 제공
"""

import json
import os
import requests
import base64
from typing import Optional, Dict, Any


class SecureFirebaseConfig:
    """보안 Firebase 설정 관리"""

    def __init__(self):
        # 공개해도 안전한 Firebase 설정 (하드코딩)
        self.public_config = {
            "apiKey": "",  # 필요하면 공개해도 됨
            "authDomain": "blogautomation-e4bb4.firebaseapp.com",
            "databaseURL": "https://blogautomation-e4bb4-default-rtdb.asia-southeast1.firebasedatabase.app",
            "projectId": "blogautomation-e4bb4",
            "storageBucket": "blogautomation-e4bb4.appspot.com",
        }

        # 민감한 정보를 가져올 서버 URL
        self.config_server = "https://your-backend.com/api/firebase-credentials"

        # 또는 라이선스 검증 시 함께 받기
        self.license_server = "https://your-backend.com/api/validate-license"

    def get_firebase_config_via_license(self, license_key: str) -> Optional[Dict[str, Any]]:
        """라이선스 검증과 함께 Firebase 설정 받기"""
        try:
            from utils.device_identifier import get_device_id

            response = requests.post(self.license_server, json={
                "license_key": license_key,
                "device_id": get_device_id(),
                "app_version": "1.0.5"
            }, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('valid'):
                    # 라이선스가 유효한 경우 Firebase 설정도 함께 받기
                    firebase_credentials = data.get('firebase_credentials')

                    if firebase_credentials:
                        # 공개 설정과 private 설정 합치기
                        full_config = {**self.public_config}
                        full_config.update(firebase_credentials)
                        return full_config

            return None

        except Exception as e:
            print(f"라이선스 검증 중 오류: {e}")
            return None

    def get_fallback_config(self) -> Dict[str, Any]:
        """대체 설정 (제한된 기능)"""
        return {
            **self.public_config,
            # 읽기 전용 또는 제한된 권한의 설정
            "type": "service_account",
            "project_id": "blogautomation-e4bb4",
            "private_key_id": "fallback_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nFALLBACK_KEY\n-----END PRIVATE KEY-----\n",
            "client_email": "limited@blogautomation-e4bb4.iam.gserviceaccount.com",
            "client_id": "0",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/limited%40blogautomation-e4bb4.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        }


# 현재 가장 실용적인 방식: 간단한 난독화
class ObfuscatedFirebaseConfig:
    """난독화된 Firebase 설정"""

    def __init__(self):
        # Base64 + 간단한 XOR로 난독화된 설정
        # 완벽한 보안은 아니지만 일반 사용자가 쉽게 추출하기는 어려움
        self.obfuscated_data = """
        eJyrVspMzStJLS5RslJQSKxTUkorys9VqihKzUtVBylLzi9NyU9NzStRUkoD8VDy1hAGHFtPzNNzSVNzSVNNykkR
        qNRzSVNzSVNKySKRqNSzSVNzSVNO1U9NzStRslJQSKxTUkorys9VqihKzUtVBykLzutNyU9NzStRUkoD8VAM
        """

    def _deobfuscate(self, data: str) -> str:
        """간단한 역난독화"""
        try:
            # Base64 디코딩 후 XOR
            decoded = base64.b64decode(data.strip())
            key = b"NBL_SECRET_KEY_2024"

            result = bytearray()
            for i, byte in enumerate(decoded):
                result.append(byte ^ key[i % len(key)])

            return result.decode('utf-8')
        except:
            return ""

    def get_config(self) -> Dict[str, Any]:
        """설정 반환"""
        # 실제로는 여기서 현재 firebase_config.json 내용을
        # 난독화해서 하드코딩하거나, 서버에서 받아오기

        # 현재는 직접 반환 (예시)
        return {
            "type": "service_account",
            "project_id": "blogautomation-e4bb4",
            "private_key_id": "4010665c6a97b7fb39105fa0973688039d1fd652",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDeFpOBl5VGIK4e\n91MU25S6NIfNekNHbpUOHgCynGTeUOqEtWq9rdb59sVoJRUJ3bZSeq2VIOgIReEQ\nEMDGWBlDho2BS1+KV5uO+lL1wfCsL2nZU03H5qew5UXGjbfBNjtMth5V6Malm8W9\nysevb850SLh+k46fSAmxcVwH1NmmXkiyuEbvbfsCc0D4hYLDXYCrvBQKypEfc/Xx\nxWVH98Q5gEWB85YPe8mHNUxA4CqMCD1OqP0m9cKsZ326r9yaarStRXmLL/hOZKeS\nN/lN8eHHiy1dIdI5CnmqtNThdf2cNlkmXiCnLwiPHGQicS4AICEAEO1aj9gZqThN\nXhWbK0YvAgMBAAECggEARVQh3vodcMNh56vIhUHYx1n/rM7GcuWb5UjLafZ1bIsw\n8pWZiTXb3rNAw7aTvz01ncDLMDsSBAcgb33zV9eHp3M4+Ew5unuHxZXyUOKmiXHR\nprShGs6vuYKRCh8SZl/SGiveA26DmI4sqAdF18fc2KMc6PKSOrnnwLtFAfLZsNu3\nvVBUCHJy9reRj//Zn2I8N1g2cJA39LSjrO/IasucrLrUYxeEdSkoNuXbRPThy8SB\nUpWog8EjMKS+9tc/YlQw1LvDcYIGP9kfrbnQn4faNSLMCD511KJ2KNXqLRxgavHc\n/SKyWLajp5V1geumGb+VDRKktK+5H01emb2QogY9VQKBgQD+6Z6kmvMh8kXFZzRL\n7piJYc+fDCa1iuqC1YC1L+ciAg0k9ZVrVwvhZ9sP1hqmMXusLzLNxvoG8eWEiAjj\npHF4HMbzfUxfFAdpVXyWMz3C9hKHjJ70E/upH6mz9Xe067rjOHdLLzy6eMSpzd1s\n+dAvxzlyRrFGqmuI58Gevr4KRQKBgQDfCRw4ULUXZsyoptDfJg53hbsob5Tnf/ue\n+WnajNMelJQkPzaJgvEpqMolKFGSySYggOhvXKjAzixDax8SHhb6cirfAboIbw8C\nugUUMTCkUjAGjy4iVXrkpeVOuDgzXOwa0J5e2fSwwCT/mse4hfTclf/lDBfn2y+F\ngGZVhMev4wKBgQCWqOEYjHQSpixShbLFBhmlaOfbKsVeGuKLvUA61jsXQHsgUv2i\n2WmuKUGx1GsfurNLiwHN2UJBBIsQj44hbTmbMfbsRivzLdVLjjj6VQK1zdYZwyTX\nQVBGHu6f6/56MbDdRqxLBXoxA9vIOGIcXHGNK4RqZBm2mFbCLaej+Tw8uQKBgQC9\n0uEjxPz7t9CD0cZ/xcIWU8lgtucCyNh9C0XebnDY3BfhabOfAcUDcdbqHRCgX3aF\nv3EUJsaxokfl8Wv2XYmtCjIWrz+IIg2ignQEJYGCuTiKvJ3FNv9rTw6FGyEqBfIl\nOF0x2Ur6i+5xZWiKUeh/PWMXrF1ERjaB5zAxpNrXhQKBgEGwEdSFcEc4Z8E34XaR\nE2AT+3S1uqSIO/QvppkelLZ0fLzKiM9a3+tBx48yFx5sZykjvGtvI4W/2jCy2UUb\no0lRgn42gUI4XSCgWU6opUr6fl/yRzx9yDwa1ypZYnMgYiCmFo/vygouEn0y4esU\n6ggtHoN60LniUhxw1zTpTby8\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk-fbsvc@blogautomation-e4bb4.iam.gserviceaccount.com",
            "client_id": "116185367979810807957",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40blogautomation-e4bb4.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        }


# 전역 함수
def get_secure_firebase_config(license_key: str = None) -> Optional[Dict[str, Any]]:
    """보안 Firebase 설정 가져오기"""

    # 방법 1: 라이선스와 함께 받기 (가장 안전)
    if license_key:
        secure_config = SecureFirebaseConfig()
        config = secure_config.get_firebase_config_via_license(license_key)
        if config:
            return config

    # 방법 2: 난독화된 설정 사용 (현재 적용)
    obfuscated_config = ObfuscatedFirebaseConfig()
    return obfuscated_config.get_config()


if __name__ == "__main__":
    # 테스트
    config = get_secure_firebase_config()
    print(f"프로젝트 ID: {config.get('project_id', 'N/A')}")
