import json
import os
from typing import Dict, Any

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'config', 
                'settings.json'
            )
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_config()
        except json.JSONDecodeError:
            return self._get_default_config()
    
    def save_config(self) -> bool:
        """설정 파일 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"설정 저장 실패: {e}")
            return False
    
    def get(self, key: str, default=None):
        """설정값 가져오기"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """설정값 설정"""
        self.config[key] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정값 반환"""
        return {
            "naver_id": "",
            "naver_password": "",
            "search_keywords": [],
            "blog_count": 10,
            "neighbor_message": "안녕하세요! {닉네임}님의 블로그 잘 보고 있어요. 서로이웃 해요!",
            "comment_option": "ai",
            "random_comments": [
                "좋은 정보 감사합니다!",
                "유익한 글이네요~",
                "도움이 되는 내용이에요!",
                "잘 보고 갑니다!",
                "공유해주셔서 감사해요!"
            ],
            "wait_time": {
                "min": 10,
                "max": 30
            },
            "scroll_settings": {
                "scroll_count": 3,
                "scroll_delay": 2
            },
            "extracted_blog_ids": {}
        }