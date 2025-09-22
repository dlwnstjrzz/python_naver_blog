#!/usr/bin/env python3
"""
라이선스 검증 모듈
Firebase Realtime Database를 사용한 라이선스 키 검증
"""

import json
import os
import platform
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import pyrebase
from utils.device_identifier import get_device_id

# 로거 설정
logger = logging.getLogger('license_validator')


class LicenseValidator:
    """Firebase 기반 라이선스 검증 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        초기화 (환경변수 전용, 배포 환경 지원)

        Args:
            config_path: 사용하지 않음 (하위 호환성을 위해 유지)
        """
        # 환경변수만 사용하므로 config_path는 무시
        self.firebase = None
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Firebase 초기화"""
        try:
            # 보안 Firebase 설정 로드 (환경변수 우선)
            from utils.secure_firebase_config import get_secure_firebase_config

            print("Firebase 설정 로드 시도...")
            firebase_config = get_secure_firebase_config()

            if not firebase_config:
                print("Firebase 설정을 로드할 수 없습니다.")
                logger.error("Firebase 설정을 로드할 수 없습니다. 환경변수 또는 설정 파일을 확인하세요.")
                self.firebase = None
                self.db = None
                return

            print(f"Firebase 설정 로드 성공. Project ID: {firebase_config.get('project_id', 'N/A')}")

            # pyrebase 설정 구성 (pyrebase 필수값 모두 포함)
            config = {
                "apiKey": firebase_config.get('api_key', 'dummy-key'),
                "authDomain": f"{firebase_config['project_id']}.firebaseapp.com",
                "databaseURL": f"https://{firebase_config['project_id']}-default-rtdb.asia-southeast1.firebasedatabase.app",
                "projectId": firebase_config['project_id'],
                "storageBucket": f"{firebase_config['project_id']}.appspot.com",
                "messagingSenderId": "123456789",  # 더미값
                "appId": "1:123456789:web:abcdef",  # 더미값
                "serviceAccount": firebase_config  # 환경변수에서 로드된 설정 사용
            }

            print("pyrebase 초기화 시도...")
            print(f"Database URL: {config['databaseURL']}")

            # Firebase 초기화
            self.firebase = pyrebase.initialize_app(config)
            self.db = self.firebase.database()

            print("Firebase 초기화 완료!")
            logger.info("Firebase 초기화 완료")

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Firebase 초기화 실패:")
            print(f"   에러: {e}")
            print(f"   상세: {error_detail}")
            print(f"배포된 버전에서는 환경변수 설정이 필요합니다:")
            print(f"   - FIREBASE_PROJECT_ID")
            print(f"   - FIREBASE_PRIVATE_KEY")
            print(f"   - FIREBASE_CLIENT_EMAIL")
            logger.error(f"Firebase 초기화 실패: {e}")
            logger.error(f"상세 오류: {error_detail}")
            self.firebase = None
            self.db = None
    
    def validate_license_key(self, license_key: str) -> Dict[str, Any]:
        """
        라이선스 키 검증 (기기 등록 포함)

        Args:
            license_key: 검증할 라이선스 키

        Returns:
            Dict: 검증 결과
                - valid: bool - 유효성 여부
                - message: str - 결과 메시지
                - expiry_date: str - 만료일 (유효한 경우)
                - days_remaining: int - 남은 일수 (유효한 경우)
                - device_registered: bool - 기기 등록 여부
        """
        try:
            # Firebase 초기화 확인
            if not self.db:
                logger.error("Firebase가 초기화되지 않았습니다.")
                return {
                    "valid": False,
                    "message": "Firebase 연결 오류가 발생했습니다.",
                    "expiry_date": None,
                    "days_remaining": 0,
                    "device_registered": False
                }

            if not license_key or license_key.strip() == "":
                return {
                    "valid": False,
                    "message": "라이선스 키가 입력되지 않았습니다.",
                    "expiry_date": None,
                    "days_remaining": 0,
                    "device_registered": False
                }

            # 현재 기기 ID 가져오기
            current_device_id = get_device_id()

            # Firebase에서 라이선스 키 조회
            license_data = self.db.child("licenses").child(license_key).get()
            
            if not license_data.val():
                return {
                    "valid": False,
                    "message": "유효하지 않은 라이선스 키입니다.",
                    "expiry_date": None,
                    "days_remaining": 0,
                    "device_registered": False
                }
            
            license_info = license_data.val()
            
            # 활성화 상태 확인
            if not license_info.get('active', False):
                return {
                    "valid": False,
                    "message": "비활성화된 라이선스입니다.",
                    "expiry_date": license_info.get('expiry_date'),
                    "days_remaining": 0,
                    "device_registered": False
                }
            
            # 만료일 확인
            expiry_date_str = license_info.get('expiry_date')
            if not expiry_date_str:
                return {
                    "valid": False,
                    "message": "라이선스 만료일 정보가 없습니다.",
                    "expiry_date": None,
                    "days_remaining": 0,
                    "device_registered": False
                }
            
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
                current_date = datetime.now()
                days_remaining = (expiry_date - current_date).days
                
                if days_remaining < 0:
                    return {
                        "valid": False,
                        "message": f"라이선스가 만료되었습니다. (만료일: {expiry_date_str})",
                        "expiry_date": expiry_date_str,
                        "days_remaining": days_remaining,
                        "device_registered": False
                    }
                
                # 기기 등록 확인 및 처리
                device_validation_result = self._validate_and_register_device(license_key, current_device_id, license_info)
                
                if not device_validation_result['valid']:
                    return {
                        "valid": False,
                        "message": device_validation_result['message'],
                        "expiry_date": expiry_date_str,
                        "days_remaining": days_remaining,
                        "device_registered": False
                    }
                
                # 마지막 사용일 업데이트
                self._update_last_used(license_key, current_device_id)
                
                if days_remaining <= 7:
                    message = f"라이선스가 곧 만료됩니다. (남은 일수: {days_remaining}일)"
                else:
                    message = f"유효한 라이선스입니다. (남은 일수: {days_remaining}일)"
                
                return {
                    "valid": True,
                    "message": message,
                    "expiry_date": expiry_date_str,
                    "days_remaining": days_remaining,
                    "device_registered": True
                }
                
            except ValueError as e:
                logger.error(f"날짜 형식 오류: {e}")
                return {
                    "valid": False,
                    "message": "라이선스 날짜 형식이 올바르지 않습니다.",
                    "expiry_date": expiry_date_str,
                    "days_remaining": 0,
                    "device_registered": False
                }
            
        except Exception as e:
            logger.error(f"라이선스 검증 중 오류: {e}")
            return {
                "valid": False,
                "message": f"라이선스 검증 중 오류가 발생했습니다: {str(e)}",
                "expiry_date": None,
                "days_remaining": 0,
                "device_registered": False
            }
    
    def _validate_and_register_device(self, license_key: str, device_id: str, license_info: dict) -> Dict[str, Any]:
        """기기 등록 확인 및 처리"""
        try:
            max_devices = license_info.get('max_devices', 1)
            registered_devices = license_info.get('registered_devices', {})
            
            # 현재 기기가 이미 등록된 경우
            if device_id in registered_devices:
                return {"valid": True, "message": "이미 등록된 기기입니다."}
            
            # 등록 가능한 기기 수 확인 (이미 등록된 기기가 아닌 경우만)
            if len(registered_devices) >= max_devices:
                # 등록된 기기 목록 표시
                device_list = []
                for reg_device_id, device_info in registered_devices.items():
                    device_name = device_info.get('device_name', f'기기-{reg_device_id[:8]}')
                    registered_at = device_info.get('registered_at', '알 수 없음')
                    device_list.append(f"• {device_name} (등록일: {registered_at})")
                
                device_list_str = '\n'.join(device_list)
                return {
                    "valid": False,
                    "message": f"최대 {max_devices}개 기기까지 등록 가능합니다.\n\n현재 등록된 기기:\n{device_list_str}\n\n다른 기기를 해제하고 다시 시도하세요."
                }
            
            # 새 기기 등록
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            device_name = f"{platform.system()} {platform.release()}"
            
            new_device_info = {
                "registered_at": current_time,
                "device_name": device_name,
                "platform": platform.platform(),
                "last_used": current_time
            }
            
            # Firebase에 기기 정보 추가
            self.db.child("licenses").child(license_key).child("registered_devices").child(device_id).set(new_device_info)
            
            logger.info(f"새 기기 등록 완료: {device_id}")
            return {"valid": True, "message": "새 기기가 성공적으로 등록되었습니다."}
            
        except Exception as e:
            logger.error(f"기기 검증 중 오류: {e}")
            return {"valid": False, "message": f"기기 검증 중 오류가 발생했습니다: {str(e)}"}
    
    def _update_last_used(self, license_key: str, device_id: str = None):
        """마지막 사용일 업데이트"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 라이선스 전체 last_used 업데이트
            self.db.child("licenses").child(license_key).update({
                "last_used": current_time
            })
            
            # 기기별 last_used 업데이트
            if device_id:
                self.db.child("licenses").child(license_key).child("registered_devices").child(device_id).update({
                    "last_used": current_time
                })
                
        except Exception as e:
            logger.warning(f"마지막 사용일 업데이트 실패: {e}")
    
    def get_license_info(self, license_key: str) -> Optional[Dict[str, Any]]:
        """
        라이선스 상세 정보 조회
        
        Args:
            license_key: 조회할 라이선스 키
            
        Returns:
            Dict: 라이선스 정보 또는 None
        """
        try:
            license_data = self.db.child("licenses").child(license_key).get()
            return license_data.val() if license_data.val() else None
        except Exception as e:
            logger.error(f"라이선스 정보 조회 실패: {e}")
            return None
    
    def unregister_device(self, license_key: str, device_id: str = None) -> Dict[str, Any]:
        """기기 등록 해제"""
        try:
            if device_id is None:
                device_id = get_device_id()
            
            # 라이선스 정보 확인
            license_data = self.db.child("licenses").child(license_key).get()
            if not license_data.val():
                return {"success": False, "message": "유효하지 않은 라이선스 키입니다."}
            
            license_info = license_data.val()
            registered_devices = license_info.get('registered_devices', {})
            
            if device_id not in registered_devices:
                return {"success": False, "message": "등록되지 않은 기기입니다."}
            
            # 기기 정보 삭제
            self.db.child("licenses").child(license_key).child("registered_devices").child(device_id).remove()
            
            logger.info(f"기기 등록 해제 완료: {device_id}")
            return {"success": True, "message": "기기 등록이 성공적으로 해제되었습니다."}
            
        except Exception as e:
            logger.error(f"기기 해제 중 오류: {e}")
            return {"success": False, "message": f"기기 해제 중 오류가 발생했습니다: {str(e)}"}
    
    def get_registered_devices(self, license_key: str) -> Dict[str, Any]:
        """등록된 기기 목록 조회"""
        try:
            license_data = self.db.child("licenses").child(license_key).get()
            if not license_data.val():
                return {"success": False, "message": "유효하지 않은 라이선스 키입니다.", "devices": []}
            
            license_info = license_data.val()
            registered_devices = license_info.get('registered_devices', {})
            max_devices = license_info.get('max_devices', 1)
            
            device_list = []
            for device_id, device_info in registered_devices.items():
                device_list.append({
                    "device_id": device_id,
                    "device_name": device_info.get('device_name', f'기기-{device_id[:8]}'),
                    "platform": device_info.get('platform', '알 수 없음'),
                    "registered_at": device_info.get('registered_at', '알 수 없음'),
                    "last_used": device_info.get('last_used', '알 수 없음')
                })
            
            return {
                "success": True,
                "devices": device_list,
                "max_devices": max_devices,
                "registered_count": len(device_list)
            }
            
        except Exception as e:
            logger.error(f"기기 목록 조회 중 오류: {e}")
            return {"success": False, "message": f"기기 목록 조회 중 오류가 발생했습니다: {str(e)}", "devices": []}

    def is_firebase_available(self) -> bool:
        """Firebase 연결 가능 여부 확인"""
        try:
            # 단순한 테스트 쿼리
            test_data = self.db.child("test").get()
            return True
        except Exception as e:
            logger.error(f"Firebase 연결 확인 실패: {e}")
            return False


# 전역 인스턴스 (싱글톤 패턴)
_license_validator = None

def get_license_validator() -> LicenseValidator:
    """라이선스 검증기 싱글톤 인스턴스 반환"""
    global _license_validator
    if _license_validator is None:
        _license_validator = LicenseValidator()
    return _license_validator


def validate_license(license_key: str) -> Dict[str, Any]:
    """
    간편한 라이선스 검증 함수
    
    Args:
        license_key: 검증할 라이선스 키
        
    Returns:
        Dict: 검증 결과
    """
    validator = get_license_validator()
    return validator.validate_license_key(license_key)


if __name__ == "__main__":
    # 테스트 코드
    import sys
    
    if len(sys.argv) > 1:
        test_key = sys.argv[1]
        result = validate_license(test_key)
        print(f"라이선스 키: {test_key}")
        print(f"검증 결과: {result}")
    else:
        print("사용법: python license_validator.py <license_key>")