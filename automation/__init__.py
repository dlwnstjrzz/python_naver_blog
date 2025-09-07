"""
네이버 블로그 자동화 모듈

이 패키지는 네이버 블로그 자동화 기능을 제공합니다.
각 모듈별로 기능이 분리되어 있어 필요한 기능만 선택적으로 사용할 수 있습니다.

모듈 구조:
- blog_automation: 메인 자동화 컨트롤러 (모든 기능 통합)
- naver_auth: 네이버 로그인/인증
- blog_search: 블로그 키워드 검색
- neighbor_connect: 이웃커넥트 수집
- buddy_manager: 서로이웃 추가 관리
- post_interaction: 게시글 상호작용 (공감, 댓글)
"""

from .blog_automation import BlogAutomation
from .naver_auth import NaverAuth
from .blog_search import BlogSearcher
from .neighbor_connect import NeighborConnectCollector
from .buddy_manager import BuddyManager
from .post_interaction import PostInteraction

__all__ = [
    'BlogAutomation',
    'NaverAuth',
    'BlogSearcher', 
    'NeighborConnectCollector',
    'BuddyManager',
    'PostInteraction'
]

__version__ = '2.0.0'
__author__ = 'Blog Automation Team'