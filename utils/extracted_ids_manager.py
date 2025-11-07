import os
from datetime import datetime
from typing import Dict, List, Optional

from utils.config_manager import ConfigManager


class ExtractedIdsManager:
    """추출된 블로그 아이디 목록을 settings.json으로 관리한다."""

    def __init__(self, config_manager: ConfigManager = None, config_key: str = "extracted_blog_ids"):
        self.config_manager = config_manager or ConfigManager()
        self.config_key = config_key
        self.extracted_ids: Dict[str, Dict[str, str]] = {}

        self._load_data()

    def _load_data(self):
        """설정 파일에서 추출된 아이디 정보를 불러온다."""
        try:
            raw_data = self.config_manager.get(self.config_key, {})

            if not isinstance(raw_data, dict):
                raw_data = {}

            normalized: Dict[str, Dict[str, str]] = {}
            for blog_id, data in raw_data.items():
                if isinstance(data, dict):
                    normalized[blog_id] = {
                        "date": data.get("date", "날짜 없음"),
                        "status": data.get("status", "성공"),
                        "method": data.get("method", ""),
                        "detail": data.get("detail", "")
                    }
                elif isinstance(data, str):
                    normalized[blog_id] = {
                        "date": data,
                        "status": "성공",
                        "method": "",
                        "detail": ""
                    }
                else:
                    normalized[blog_id] = {
                        "date": "날짜 없음",
                        "status": "성공",
                        "method": "",
                        "detail": ""
                    }

            self.extracted_ids = normalized

            if normalized != raw_data:
                self._save_data()
        except Exception as e:
            print(f"추출된 블로그 아이디 로드 중 오류: {e}")
            self.extracted_ids = {}

    def _save_data(self):
        """현재 추출된 아이디 정보를 settings.json에 저장한다."""
        try:
            self.config_manager.set(self.config_key, self.extracted_ids)
            return self.config_manager.save_config()
        except Exception as e:
            print(f"추출된 블로그 아이디 저장 중 오류: {e}")
            return False

    def add_extracted_ids(
        self,
        blog_ids: List[str],
        success: bool = True,
        status: Optional[str] = None,
        method: Optional[str] = None,
        detail: Optional[str] = None
    ) -> int:
        """새로 수집한 블로그 아이디를 추가한다."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_value = status if status is not None else ("성공" if success else "실패")
        added_count = 0

        for blog_id in blog_ids:
            if blog_id not in self.extracted_ids:
                self.extracted_ids[blog_id] = {
                    "date": current_time,
                    "status": status_value,
                    "method": method or "",
                    "detail": detail or ""
                }
                added_count += 1

        if added_count > 0:
            self._save_data()

        return added_count

    def reload(self):
        """외부에서 설정 파일이 수정된 경우 다시 불러온다."""
        self.config_manager.config = self.config_manager.load_config()
        self._load_data()

    def update_status(self, blog_id: str, success: bool = True, status: str = None) -> bool:
        """특정 블로그 아이디의 상태를 갱신한다."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_value = status if status is not None else ("성공" if success else "실패")

        if blog_id not in self.extracted_ids:
            self.extracted_ids[blog_id] = {
                "date": current_time,
                "status": status_value,
                "method": "",
                "detail": ""
            }
        else:
            self.extracted_ids[blog_id]["date"] = current_time
            self.extracted_ids[blog_id]["status"] = status_value

        return self._save_data()

    def filter_new_ids(self, blog_ids: List[str]) -> List[str]:
        """이미 추출된 아이디를 제외한 새 아이디만 반환한다."""
        return [blog_id for blog_id in blog_ids if blog_id not in self.extracted_ids]

    def is_extracted(self, blog_id: str) -> bool:
        """아이디가 이미 추출되었는지 여부를 반환한다."""
        return blog_id in self.extracted_ids

    def get_all_extracted_ids(self) -> Dict[str, Dict[str, str]]:
        """전체 추출 목록을 복사본으로 돌려준다."""
        return self.extracted_ids.copy()

    def get_extracted_count(self) -> int:
        """총 추출된 아이디 수를 반환한다."""
        return len(self.extracted_ids)

    def remove_extracted_id(self, blog_id: str) -> bool:
        """특정 아이디를 목록에서 제거한다."""
        if blog_id in self.extracted_ids:
            del self.extracted_ids[blog_id]
            self._save_data()
            return True
        return False

    def remove_multiple_ids(self, blog_ids: List[str]) -> int:
        """여러 아이디를 한꺼번에 제거한다."""
        removed_count = 0

        for blog_id in blog_ids:
            if blog_id in self.extracted_ids:
                del self.extracted_ids[blog_id]
                removed_count += 1

        if removed_count > 0:
            self._save_data()

        return removed_count

    def clear_all_extracted_ids(self) -> bool:
        """전체 목록을 초기화한다."""
        self.extracted_ids = {}
        return self._save_data()

    def get_statistics(self) -> Dict:
        """추출된 아이디 통계를 반환한다."""
        if not self.extracted_ids:
            return {
                'total_count': 0,
                'success_count': 0,
                'fail_count': 0,
                'pending_count': 0,
                'oldest_date': None,
                'newest_date': None
            }

        dates = [data['date'] for data in self.extracted_ids.values()]
        success_count = sum(1 for data in self.extracted_ids.values() if data.get('status') == '성공')
        fail_count = sum(1 for data in self.extracted_ids.values() if data.get('status') == '실패')
        pending_count = len(self.extracted_ids) - success_count - fail_count

        return {
            'total_count': len(self.extracted_ids),
            'success_count': success_count,
            'fail_count': fail_count,
            'pending_count': pending_count,
            'oldest_date': min(dates) if dates else None,
            'newest_date': max(dates) if dates else None
        }

    def export_to_text(self, export_path: str = None) -> str:
        """추출된 아이디 목록을 텍스트 파일로 저장한다."""
        if export_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"data/extracted_ids_export_{timestamp}.txt"

        try:
            export_dir = os.path.dirname(export_path)
            if export_dir:
                os.makedirs(export_dir, exist_ok=True)

            stats = self.get_statistics()
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(f"추출된 블로그 아이디 목록 (총 {stats['total_count']}건)\n")
                f.write(
                    f"성공: {stats['success_count']}건, 실패: {stats['fail_count']}건, 보류: {stats['pending_count']}건\n"
                )
                f.write("=" * 60 + "\n")
                f.write(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                sorted_items = sorted(self.extracted_ids.items(), key=lambda x: x[1]['date'])
                for blog_id, data in sorted_items:
                    f.write(f"{blog_id}\t{data['date']}\t{data['status']}\n")

            return export_path
        except Exception as e:
            print(f"텍스트 내보내기 실패: {e}")
            return None
