#!/usr/bin/env python3
"""
Firebase 데이터베이스 구조를 기기 등록 지원으로 업데이트
"""

import json
import os
from datetime import datetime

def update_firebase_structure():
    """기존 라이선스에 기기 등록 정보 추가"""
    
    try:
        import pyrebase
        from utils.device_identifier import get_device_id
        
        # Firebase 설정 로드
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'firebase_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            firebase_config = json.load(f)
        
        # Firebase 설정
        config = {
            "apiKey": "",
            "authDomain": f"{firebase_config['project_id']}.firebaseapp.com",
            "databaseURL": f"https://{firebase_config['project_id']}-default-rtdb.asia-southeast1.firebasedatabase.app",
            "projectId": firebase_config['project_id'],
            "storageBucket": f"{firebase_config['project_id']}.appspot.com",
            "serviceAccount": config_path
        }
        
        # Firebase 초기화
        firebase = pyrebase.initialize_app(config)
        db = firebase.database()
        
        # 현재 기기 ID
        current_device_id = get_device_id()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"현재 기기 ID: {current_device_id}")
        print("Firebase 라이선스 구조를 업데이트 중...")
        
        # 기존 라이선스들 조회
        licenses_data = db.child("licenses").get()
        
        if licenses_data.val():
            for license_key, license_info in licenses_data.val().items():
                print(f"\n라이선스 {license_key} 업데이트 중...")
                
                # 기기 등록 정보가 없는 경우 추가
                if 'registered_devices' not in license_info:
                    # 새로운 구조로 업데이트
                    updated_info = {
                        **license_info,
                        'max_devices': 1,  # 기본적으로 1개 기기만 허용
                        'registered_devices': {}  # 빈 기기 목록으로 시작
                    }
                    
                    # 업데이트 실행
                    db.child("licenses").child(license_key).set(updated_info)
                    print(f"✅ {license_key} 구조 업데이트 완료")
                else:
                    print(f"⏩ {license_key}는 이미 업데이트됨")
        
        print(f"\n🎉 Firebase 구조 업데이트 완료!")
        
        # 새로운 구조 예시 표시
        print(f"\n📋 업데이트된 라이선스 구조:")
        example_structure = {
            "NBL-2024-XXXXXXXX": {
                "active": True,
                "expiry_date": "2026-09-14",
                "created_at": "2025-09-14 20:00:00",
                "last_used": "",
                "max_devices": 1,  # 허용 기기 수
                "registered_devices": {
                    # "DEVICE_ID": {
                    #     "registered_at": "2025-09-14 21:00:00",
                    #     "device_name": "MacBook Pro",
                    #     "platform": "macOS-15.1.1",
                    #     "last_used": "2025-09-14 21:30:00"
                    # }
                },
                "user_info": {
                    "email": "user@example.com",
                    "name": "사용자명"
                }
            }
        }
        
        print(json.dumps(example_structure, indent=2, ensure_ascii=False))
        
    except ImportError as e:
        print(f"❌ 필요한 모듈을 찾을 수 없습니다: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    update_firebase_structure()