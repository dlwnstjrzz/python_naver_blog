import json
import os
from datetime import datetime
from typing import Set, List, Dict


class ExtractedIdsManager:
    """추출된 블로그 아이디들을 관리하는 클래스"""
    
    def __init__(self, file_path: str = "data/extracted_blog_ids.json"):
        self.file_path = file_path
        self.data_dir = os.path.dirname(file_path)
        self.extracted_ids: Dict[str, str] = {}  # {blog_id: extraction_date}
        
        # 데이터 디렉토리 생성
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 기존 데이터 로드
        self._load_data()
    
    def _load_data(self):
        """파일에서 추출된 아이디 데이터 로드"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                    # 기존 데이터 형식과의 호환성 처리
                    self.extracted_ids = {}
                    for blog_id, data in loaded_data.items():
                        if isinstance(data, str):
                            # 기존 형식 (날짜 문자열)
                            self.extracted_ids[blog_id] = {
                                "date": data,
                                "status": "성공"  # 기존 데이터는 모두 성공으로 간주
                            }
                        elif isinstance(data, dict):
                            # 새 형식 (딕셔너리)
                            self.extracted_ids[blog_id] = data
                        else:
                            # 예외 상황
                            self.extracted_ids[blog_id] = {
                                "date": "알 수 없음",
                                "status": "성공"
                            }
        except Exception as e:
            print(f"추출된 아이디 데이터 로드 중 오류: {e}")
            self.extracted_ids = {}
    
    def _save_data(self):
        """추출된 아이디 데이터를 파일에 저장"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_ids, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"추출된 아이디 데이터 저장 중 오류: {e}")
            return False
    
    def add_extracted_ids(self, blog_ids: List[str], success: bool = True) -> int:
        """새로 추출된 블로그 아이디들을 추가"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "성공" if success else "실패"
        added_count = 0
        
        for blog_id in blog_ids:
            if blog_id not in self.extracted_ids:
                self.extracted_ids[blog_id] = {
                    "date": current_time,
                    "status": status
                }
                added_count += 1
        
        if added_count > 0:
            self._save_data()
        
        return added_count
    
    def filter_new_ids(self, blog_ids: List[str]) -> List[str]:
        """이미 추출된 아이디들을 제외한 새로운 아이디들만 반환"""
        new_ids = [blog_id for blog_id in blog_ids if blog_id not in self.extracted_ids]
        return new_ids
    
    def is_extracted(self, blog_id: str) -> bool:
        """특정 블로그 아이디가 이미 추출되었는지 확인"""
        return blog_id in self.extracted_ids
    
    def get_all_extracted_ids(self) -> Dict[str, str]:
        """모든 추출된 아이디와 추출 날짜 반환"""
        return self.extracted_ids.copy()
    
    def get_extracted_count(self) -> int:
        """추출된 아이디 총 개수"""
        return len(self.extracted_ids)
    
    def remove_extracted_id(self, blog_id: str) -> bool:
        """특정 블로그 아이디를 추출 목록에서 제거"""
        if blog_id in self.extracted_ids:
            del self.extracted_ids[blog_id]
            self._save_data()
            return True
        return False
    
    def remove_multiple_ids(self, blog_ids: List[str]) -> int:
        """여러 블로그 아이디들을 추출 목록에서 제거"""
        removed_count = 0
        
        for blog_id in blog_ids:
            if blog_id in self.extracted_ids:
                del self.extracted_ids[blog_id]
                removed_count += 1
        
        if removed_count > 0:
            self._save_data()
        
        return removed_count
    
    def clear_all_extracted_ids(self) -> bool:
        """모든 추출된 아이디 목록 초기화"""
        self.extracted_ids = {}
        return self._save_data()
    
    def get_statistics(self) -> Dict:
        """추출된 아이디 통계 정보"""
        if not self.extracted_ids:
            return {
                'total_count': 0,
                'success_count': 0,
                'fail_count': 0,
                'oldest_date': None,
                'newest_date': None
            }
        
        dates = [data['date'] for data in self.extracted_ids.values()]
        success_count = sum(1 for data in self.extracted_ids.values() if data.get('status') == '성공')
        fail_count = len(self.extracted_ids) - success_count
        
        return {
            'total_count': len(self.extracted_ids),
            'success_count': success_count,
            'fail_count': fail_count,
            'oldest_date': min(dates) if dates else None,
            'newest_date': max(dates) if dates else None
        }
    
    def export_to_text(self, export_path: str = None) -> str:
        """추출된 아이디 목록을 텍스트 파일로 내보내기"""
        if export_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"data/extracted_ids_export_{timestamp}.txt"
        
        try:
            stats = self.get_statistics()
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(f"추출된 블로그 아이디 목록 (총 {stats['total_count']}개)\n")
                f.write(f"성공: {stats['success_count']}개, 실패: {stats['fail_count']}개\n")
                f.write("=" * 60 + "\n")
                f.write(f"내보내기 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # 날짜순으로 정렬하여 출력
                sorted_items = sorted(self.extracted_ids.items(), key=lambda x: x[1]['date'])
                for blog_id, data in sorted_items:
                    f.write(f"{blog_id}\t{data['date']}\t{data['status']}\n")
            
            return export_path
        except Exception as e:
            print(f"텍스트 내보내기 중 오류: {e}")
            return None