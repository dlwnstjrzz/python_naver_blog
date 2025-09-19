#!/usr/bin/env python3
"""
기기 고유 식별자 생성 및 관리 모듈
"""

import hashlib
import platform
import subprocess
import uuid
import os
import json
from typing import Optional

class DeviceIdentifier:
    """기기 고유 식별자 관리 클래스"""
    
    def __init__(self):
        self.device_info_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'device_info.json'
        )
    
    def get_system_info(self) -> dict:
        """시스템 정보 수집"""
        info = {}
        
        try:
            # 운영체제 정보
            info['platform'] = platform.platform()
            info['machine'] = platform.machine()
            info['processor'] = platform.processor()
            
            # Mac의 경우 하드웨어 UUID 사용
            if platform.system() == 'Darwin':  # macOS
                try:
                    result = subprocess.run(['system_profiler', 'SPHardwareDataType'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Hardware UUID' in line:
                                info['hardware_uuid'] = line.split(':')[1].strip()
                                break
                except Exception:
                    pass
            
            # Windows의 경우 WMIC 사용
            elif platform.system() == 'Windows':
                try:
                    result = subprocess.run(['wmic', 'csproduct', 'get', 'uuid'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            info['hardware_uuid'] = lines[1].strip()
                except Exception:
                    pass
            
            # Linux의 경우 machine-id 사용
            elif platform.system() == 'Linux':
                try:
                    with open('/etc/machine-id', 'r') as f:
                        info['machine_id'] = f.read().strip()
                except Exception:
                    try:
                        with open('/var/lib/dbus/machine-id', 'r') as f:
                            info['machine_id'] = f.read().strip()
                    except Exception:
                        pass
            
            # 네트워크 MAC 주소 (fallback)
            try:
                info['mac_address'] = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                                              for ele in range(0, 8*6, 8)][::-1])
            except Exception:
                pass
                
        except Exception as e:
            print(f"시스템 정보 수집 중 오류: {e}")
        
        return info
    
    def generate_device_id(self) -> str:
        """기기 고유 ID 생성"""
        system_info = self.get_system_info()
        
        # 우선순위: hardware_uuid > machine_id > mac_address
        unique_identifiers = []
        
        if 'hardware_uuid' in system_info and system_info['hardware_uuid']:
            unique_identifiers.append(system_info['hardware_uuid'])
        
        if 'machine_id' in system_info and system_info['machine_id']:
            unique_identifiers.append(system_info['machine_id'])
            
        if 'mac_address' in system_info and system_info['mac_address']:
            unique_identifiers.append(system_info['mac_address'])
        
        # 플랫폼 정보도 포함
        unique_identifiers.extend([
            system_info.get('platform', ''),
            system_info.get('machine', ''),
            system_info.get('processor', '')
        ])
        
        # 모든 정보를 합쳐서 해시 생성
        combined_info = '|'.join(filter(None, unique_identifiers))
        
        if not combined_info:
            # 마지막 fallback: 랜덤 UUID 생성하고 저장
            device_id = str(uuid.uuid4())
        else:
            # SHA-256 해시로 기기 ID 생성
            device_id = hashlib.sha256(combined_info.encode()).hexdigest()[:32]
        
        return device_id.upper()
    
    def get_device_id(self) -> str:
        """기기 ID 조회 (캐시된 값 우선 사용)"""
        
        # 기존에 저장된 기기 정보가 있는지 확인
        if os.path.exists(self.device_info_file):
            try:
                with open(self.device_info_file, 'r', encoding='utf-8') as f:
                    device_info = json.load(f)
                    
                stored_device_id = device_info.get('device_id')
                if stored_device_id:
                    return stored_device_id
            except Exception:
                pass
        
        # 새로 생성
        device_id = self.generate_device_id()
        
        # 파일에 저장
        self.save_device_info(device_id)
        
        return device_id
    
    def save_device_info(self, device_id: str):
        """기기 정보를 파일에 저장"""
        try:
            # config 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(self.device_info_file), exist_ok=True)
            
            device_info = {
                'device_id': device_id,
                'created_at': platform.uname()._asdict(),
                'generated_at': str(uuid.uuid4()),  # 파일 생성 시점 식별용
                'system_info': self.get_system_info()
            }
            
            with open(self.device_info_file, 'w', encoding='utf-8') as f:
                json.dump(device_info, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"기기 정보 저장 중 오류: {e}")
    
    def get_device_fingerprint(self) -> dict:
        """기기 지문 정보 (디버깅용)"""
        return {
            'device_id': self.get_device_id(),
            'system_info': self.get_system_info(),
            'platform': platform.platform(),
            'node': platform.node()
        }


# 전역 인스턴스
_device_identifier = None

def get_device_identifier() -> DeviceIdentifier:
    """기기 식별자 싱글톤 인스턴스 반환"""
    global _device_identifier
    if _device_identifier is None:
        _device_identifier = DeviceIdentifier()
    return _device_identifier

def get_device_id() -> str:
    """간편한 기기 ID 조회 함수"""
    return get_device_identifier().get_device_id()


if __name__ == "__main__":
    # 테스트 코드
    device_id = get_device_id()
    print(f"기기 ID: {device_id}")
    
    fingerprint = get_device_identifier().get_device_fingerprint()
    print(f"기기 지문: {json.dumps(fingerprint, indent=2, ensure_ascii=False)}")