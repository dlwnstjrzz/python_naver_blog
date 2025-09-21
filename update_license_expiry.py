#!/usr/bin/env python3
"""
테스트용 라이선스 키의 만료일을 1년 후로 업데이트하는 스크립트
"""

import json
import os
from datetime import datetime, timedelta

def update_license_expiry():
    """테스트 라이선스 키들의 만료일을 1년 후로 업데이트"""
    
    try:
        import pyrebase
        
        # Firebase 설정 로드
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'firebase_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            firebase_config = json.load(f)
        
        # Firebase 설정
        config = {
            "apiKey": "",  # 웹 API 키 (필요시 추가)
            "authDomain": f"{firebase_config['project_id']}.firebaseapp.com",
            "databaseURL": f"https://{firebase_config['project_id']}-default-rtdb.asia-southeast1.firebasedatabase.app",
            "projectId": firebase_config['project_id'],
            "storageBucket": f"{firebase_config['project_id']}.appspot.com",
            "serviceAccount": config_path
        }
        
        # Firebase 초기화
        firebase = pyrebase.initialize_app(config)
        db = firebase.database()
        
        # 1년 후 날짜 계산
        one_year_later = datetime.now() + timedelta(days=365)
        new_expiry_date = one_year_later.strftime('%Y-%m-%d')
        
        # 업데이트할 라이선스 키 목록
        license_keys = ["NBL-2024-TEST001", "NBL-2024-TEST002", "NBL-2024-TEST003"]
        
        print(f"라이선스 만료일을 {new_expiry_date}로 업데이트 중...")
        
        # 각 라이선스의 만료일 업데이트
        for license_key in license_keys:
            try:
                # 기존 데이터 조회
                license_data = db.child("licenses").child(license_key).get()
                
                if license_data.val():
                    # 만료일만 업데이트
                    db.child("licenses").child(license_key).update({
                        "expiry_date": new_expiry_date
                    })
                    print(f"✅ 업데이트 완료: {license_key}")
                else:
                    print(f"⚠️  라이선스 키를 찾을 수 없음: {license_key}")
                    
            except Exception as e:
                print(f"❌ {license_key} 업데이트 실패: {str(e)}")
        
        print(f"\n🎉 만료일 업데이트 완료!")
        print(f"새 만료일: {new_expiry_date} ({one_year_later.strftime('%Y년 %m월 %d일')})")
        print(f"남은 일수: 365일")
        
        print(f"\n테스트용 라이선스 키:")
        for key in license_keys:
            print(f"- {key}")
        
    except ImportError:
        print("❌ pyrebase4가 설치되지 않았습니다. pip install pyrebase4로 설치해주세요.")
    except FileNotFoundError:
        print("❌ Firebase 설정 파일을 찾을 수 없습니다. config/firebase_config.json을 확인해주세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    update_license_expiry()