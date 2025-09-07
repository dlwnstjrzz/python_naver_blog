import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from utils.logger import setup_logger
from .naver_auth import NaverAuth
from .blog_search import BlogSearcher
from .neighbor_connect import NeighborConnectCollector
from .buddy_manager import BuddyManager
from .post_interaction import PostInteraction


class BlogAutomation:
    """네이버 블로그 자동화 메인 컨트롤러"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.logger = setup_logger()
        self.headless = headless
        
        # 각 기능별 모듈
        self.auth = None
        self.blog_searcher = None
        self.neighbor_collector = None
        self.buddy_manager = None
        self.post_interaction = None

    def setup_driver(self):
        """Chrome 드라이버 설정 및 모든 모듈 초기화"""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument('--headless')

            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_window_size(1280, 800)

            self.auth = NaverAuth(self.driver, self.logger)
            self.blog_searcher = BlogSearcher(self.driver, self.logger)
            self.neighbor_collector = NeighborConnectCollector(self.driver, self.logger)
            self.buddy_manager = BuddyManager(self.driver, self.logger)
            self.post_interaction = PostInteraction(self.driver, self.logger)
            
            self.logger.info("Chrome 드라이버 및 모든 모듈이 성공적으로 초기화되었습니다.")
            return True

        except Exception as e:
            self.logger.error(f"드라이버 설정 실패: {e}")
            return False

    def login(self, username, password, max_retries=2):
        """네이버 로그인"""
        if not self.driver:
            if not self.setup_driver():
                return False
        
        if not self.auth:
            self.logger.error("인증 모듈이 초기화되지 않았습니다.")
            return False
            
        return self.auth.login(username, password, max_retries=max_retries)

    def search_and_collect_blogs(self, keyword, target_count, start_page=1):
        """키워드 검색으로 블로그 수집"""
        if not self.blog_searcher:
            self.logger.error("블로그 검색 모듈이 초기화되지 않았습니다.")
            return []
            
        if not self.blog_searcher.navigate_to_blog_search(keyword):
            return []
            
        return self.blog_searcher.collect_blog_names(target_count, start_page)

    def collect_neighbor_blogs(self, blog_url):
        """이웃커넥트에서 블로그 목록 수집"""
        if not self.neighbor_collector:
            self.logger.error("이웃커넥트 수집 모듈이 초기화되지 않았습니다.")
            return False, "초기화 오류", []
        return self.neighbor_collector.process_neighbor_connect(blog_url)

    def process_blog_automation(self, blog_data, progress_callback=None):
        """블로그 자동화 메인 프로세스"""
        try:
            total_count = len(blog_data)
            
            if not self.buddy_manager or not self.post_interaction:
                self.logger.error("필요한 모듈이 초기화되지 않았습니다.")
                return 0, total_count

            self.buddy_manager.reset_buddy_count()
            self.logger.info(f"총 {total_count}개 블로그 처리를 시작합니다.")

            for i, data in enumerate(blog_data, 1):
                blog_name = data['blog_name']
                post_url = data['post_url']

                self.logger.info(f"[{i}/{total_count}] {blog_name} 블로그 처리 중...")

                if progress_callback:
                    progress_callback(i, total_count, blog_name)

                self.buddy_manager.buddy_available = False
                self.buddy_manager.add_buddy_to_blog(blog_name)

                if not self.buddy_manager.buddy_available:
                    self.logger.warning(f"❌ {blog_name} 서로이웃 추가 불가능 - 건너뛰기")
                    continue

                interaction_success = self.post_interaction.process_post_interaction(post_url, blog_name)
                if interaction_success:
                    self.logger.info(f"게시글 상호작용 완료: {blog_name}")
                else:
                    self.logger.warning(f"게시글 상호작용 실패: {blog_name}")

                if i < total_count:
                    delay = random.uniform(1, 2)
                    time.sleep(delay)

            success_count = self.buddy_manager.get_buddy_success_count()
            self.logger.info(f"블로그 처리 완료: {success_count}/{total_count} 성공")
            return success_count, total_count

        except Exception as e:
            self.logger.error(f"블로그 처리 중 오류: {e}")
            return 0, len(blog_data) if blog_data else 0
        
        finally:
            self.cleanup_driver()

    def cleanup_driver(self):
        """자동화 완료 후 브라우저 드라이버 완전 정리"""
        try:
            if self.driver:
                self.logger.info("🔄 자동화 완료, 브라우저 정리 중...")
                
                try:
                    all_handles = self.driver.window_handles
                    for handle in all_handles:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except:
                            pass
                except:
                    pass
                
                try:
                    self.driver.quit()
                    self.logger.info("✅ 브라우저 드라이버 정리 완료")
                except:
                    pass
                
                self.driver = None
                
        except Exception as e:
            self.logger.warning(f"브라우저 정리 중 오류 (무시하고 계속): {e}")
        finally:
            self.driver = None

    def close(self):
        """자동화 종료"""
        self.cleanup_driver()

    def get_driver(self):
        """현재 드라이버 반환"""
        return self.driver