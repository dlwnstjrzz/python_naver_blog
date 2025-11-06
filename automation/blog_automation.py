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
from utils.extracted_ids_manager import ExtractedIdsManager


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
        self.extracted_ids_manager = ExtractedIdsManager()

    def setup_driver(self):
        """Chrome 드라이버 설정 및 모든 모듈 초기화"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            import platform

            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument('--headless')

            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(
                '--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option(
                'useAutomationExtension', False)
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # OS별 Chrome 바이너리 위치 설정
            system = platform.system()
            if system == "Darwin":  # macOS
                chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            elif system == "Windows":
                # Windows는 기본 설치 경로 사용 (자동 탐지)
                pass
            elif system == "Linux":
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--remote-debugging-port=9222')

            # webdriver-manager를 사용하여 자동으로 ChromeDriver 다운로드/관리
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(
                    service=service, options=chrome_options)
                self.logger.info("webdriver-manager로 Chrome 드라이버 설정 완료")
            except Exception as e:
                self.logger.warning(f"webdriver-manager 실패, 시스템 드라이버 시도: {e}")
                # 폴백: 시스템에 설치된 드라이버 사용
                self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_window_size(1280, 800)

            self.auth = NaverAuth(self.driver, self.logger)
            self.blog_searcher = BlogSearcher(self.driver, self.logger)
            self.neighbor_collector = NeighborConnectCollector(
                self.driver, self.logger)
            self.buddy_manager = BuddyManager(self.driver, self.logger)
            self.post_interaction = PostInteraction(
                self.driver, self.logger, self.buddy_manager)

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
        """키워드 검색으로 블로그 수집 (목표 수만큼 새로운 아이디가 나올 때까지 계속 수집)"""
        if not self.blog_searcher:
            self.logger.error("블로그 검색 모듈이 초기화되지 않았습니다.")
            return []

        if not self.blog_searcher.navigate_to_blog_search(keyword):
            return []

        collected_blogs = []
        current_page = start_page
        max_attempts = 1000  # 최대 20페이지까지 시도

        self.logger.info(f"목표: 새로운 아이디 {target_count}개 수집")

        while len(collected_blogs) < target_count and current_page < start_page + max_attempts:
            self.logger.info(
                f"페이지 {current_page}에서 수집 중... (현재 {len(collected_blogs)}/{target_count}개)")

            # 필요한 개수만큼만 수집
            remaining_needed = target_count - len(collected_blogs)
            page_target = remaining_needed  # 정확히 필요한 개수만

            # 현재 페이지에서 블로그 수집
            raw_blogs = self.blog_searcher.collect_blog_names(
                page_target, current_page)

            if not raw_blogs:
                self.logger.warning(f"페이지 {current_page}에서 수집된 블로그가 없습니다.")
                break

            # 블로그 아이디 추출
            blog_ids = [blog.get('blog_name', '')
                        for blog in raw_blogs if blog.get('blog_name')]
            self.logger.info(f"페이지 {current_page}에서 {len(blog_ids)}개 블로그 발견")

            # 이미 추출된 아이디 제외
            new_blog_ids = self.extracted_ids_manager.filter_new_ids(blog_ids)
            excluded_count = len(blog_ids) - len(new_blog_ids)

            if excluded_count > 0:
                self.logger.info(
                    f"페이지 {current_page}에서 이미 추출된 아이디 {excluded_count}개 제외")

            # 새로운 아이디만 포함된 블로그 데이터 구성
            new_blogs = [blog for blog in raw_blogs
                         if blog.get('blog_name') in new_blog_ids]

            # 목표 수를 초과하지 않도록 제한
            remaining_needed = target_count - len(collected_blogs)
            if len(new_blogs) > remaining_needed:
                new_blogs = new_blogs[:remaining_needed]

            collected_blogs.extend(new_blogs)
            self.logger.info(
                f"페이지 {current_page}에서 {len(new_blogs)}개 새 블로그 추가 (총 {len(collected_blogs)}/{target_count}개)")

            # 목표 달성 확인
            if len(collected_blogs) >= target_count:
                self.logger.info(
                    f"목표 달성! {len(collected_blogs)}개 새로운 블로그 수집 완료")
                break

            current_page += 1

        if len(collected_blogs) < target_count:
            self.logger.warning(
                f"목표 미달성: {len(collected_blogs)}/{target_count}개만 수집됨 (최대 {max_attempts}페이지 탐색)")

        self.logger.info(f"최종 수집 완료: {len(collected_blogs)}개 새로운 블로그")
        return collected_blogs

    def collect_neighbor_blogs(self, blog_url, target_count=None):
        """이웃커넥트에서 블로그 목록 수집 (목표 수만큼 새로운 아이디 반환)"""
        if not self.neighbor_collector:
            self.logger.error("이웃커넥트 수집 모듈이 초기화되지 않았습니다.")
            return False, "초기화 오류", []

        # 설정에서 목표 수 가져오기 (이웃커넥트용)
        if target_count is None:
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            target_count = config_manager.get('neighbor_count')
            if target_count is None:
                self.logger.error(
                    "이웃 수집 개수가 설정되지 않았습니다. GUI에서 이웃 개수를 설정해주세요.")
                return False, "이웃 수집 개수 미설정", []

        self.logger.info(f"목표: 새로운 아이디 {target_count}개 수집")

        # 이웃커넥트에서 목표 개수만큼 새로운 아이디 수집 (여러 페이지 지원)
        blog_id = self._extract_blog_id_from_url(blog_url)
        if not blog_id:
            return False, "유효하지 않은 블로그 URL입니다.", []

        # 이웃커넥트 가용성 확인
        is_available, error_message = self.neighbor_collector.check_neighbor_connect_availability(
            blog_id)
        if not is_available:
            return False, error_message, []

        # 목표 개수에 도달할 때까지 여러 페이지 수집
        collected_new_ids = []
        collected_urls = []
        current_page = 1
        max_pages = 1000  # 최대 20페이지까지 탐색

        while len(collected_new_ids) < target_count and current_page <= max_pages:
            self.logger.info(
                f"이웃커넥트 페이지 {current_page} 수집 중... (현재 {len(collected_new_ids)}/{target_count}개 새로운 아이디)")

            # 현재 페이지에서 URL 수집
            page_url = f"https://section.blog.naver.com/connect/ViewMoreFollowers.naver?blogId={blog_id}&currentPage={current_page}"
            self.driver.get(page_url)

            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script(
                    "return document.readyState") == "complete"
            )
            import time
            time.sleep(1)

            # 현재 페이지에서 URL 수집
            page_urls = self.neighbor_collector._collect_urls_from_current_page()

            if not page_urls:
                self.logger.warning(
                    f"페이지 {current_page}에서 아무 이웃도 찾지 못함 - 더 이상 페이지가 없는 것 같음")
                break

            # 블로그 아이디 추출
            page_blog_ids = []
            url_to_id_map = {}
            for url in page_urls:
                if "blog.naver.com/" in url:
                    extracted_id = url.split("blog.naver.com/")[1].rstrip('/')
                    page_blog_ids.append(extracted_id)
                    url_to_id_map[extracted_id] = url

            # 이미 추출된 아이디 제외
            new_ids_from_page = self.extracted_ids_manager.filter_new_ids(
                page_blog_ids)

            # 중복 제거 (이미 수집된 아이디들과도 비교)
            truly_new_ids = []
            for new_id in new_ids_from_page:
                if new_id not in collected_new_ids:
                    truly_new_ids.append(new_id)

            # 목표 개수만큼만 추가
            remaining_needed = target_count - len(collected_new_ids)
            if len(truly_new_ids) > remaining_needed:
                truly_new_ids = truly_new_ids[:remaining_needed]

            # 수집된 데이터에 추가
            for new_id in truly_new_ids:
                collected_new_ids.append(new_id)
                if new_id in url_to_id_map:
                    collected_urls.append(url_to_id_map[new_id])

            excluded_count = len(page_blog_ids) - len(new_ids_from_page)
            self.logger.info(
                f"페이지 {current_page}: 총 {len(page_blog_ids)}개, 이미 추출된 아이디 {excluded_count}개 제외, 새로운 아이디 {len(truly_new_ids)}개 추가")
            self.logger.info(
                f"현재 수집된 새로운 아이디: {len(collected_new_ids)}/{target_count}개")

            # 목표 달성 확인
            if len(collected_new_ids) >= target_count:
                self.logger.info(
                    f"목표 달성! {len(collected_new_ids)}개 새로운 아이디 수집 완료")
                break

            current_page += 1

        if len(collected_new_ids) < target_count:
            message = f"목표 미달성: {len(collected_new_ids)}/{target_count}개만 수집됨 (최대 {max_pages}페이지 탐색)"
            self.logger.warning(message)
        else:
            message = f"목표 달성: {len(collected_new_ids)}개 새로운 아이디 수집 완료"
            self.logger.info(message)

        return True, message, collected_urls

    def _extract_blog_id_from_url(self, blog_url):
        """블로그 URL에서 블로그 아이디를 추출"""
        try:
            if "blog.naver.com/" in blog_url:
                parts = blog_url.split("blog.naver.com/")
                if len(parts) > 1:
                    blog_id = parts[1].strip().rstrip('/')
                    return blog_id
            return None
        except Exception as e:
            self.logger.error(f"블로그 아이디 추출 중 오류: {e}")
            return None

    def process_blog_automation(self, blog_data, progress_callback=None):
        """블로그 자동화 메인 프로세스 (이웃커넥트용)"""
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

                self.logger.info(
                    f"[{i}/{total_count}] {blog_name} 블로그 처리 중...")

                if progress_callback:
                    progress_callback(i, total_count, blog_name)

                self.buddy_manager.buddy_available = False
                # 모바일 서이추 사용 (키워드 검색과 동일)
                self.buddy_manager.add_buddy_to_blog_mobile(blog_name)

                if not self.buddy_manager.buddy_available:
                    self.logger.warning(
                        f"{blog_name} 모바일 서로이웃 추가 불가능 - 건너뛰기")
                    continue

                # 설정에서 공감/댓글 옵션 확인
                from utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                enable_like = config_manager.get('enable_like', True)
                enable_comment = config_manager.get('enable_comment', True)

                # 공감/댓글이 모두 비활성화된 경우 바로 다음 블로그로
                if not enable_like and not enable_comment:
                    self.logger.info(
                        f"[{blog_name}] 공감/댓글 모두 비활성화 - 서이추만 완료하고 다음 블로그로 이동")
                    continue

                # 공감/댓글 중 하나라도 활성화된 경우 게시글로 이동
                # 서로이웃 추가 후 메인 블로그 페이지에서 최신 게시글로 이동 (모바일 방식)
                latest_post_success = self.buddy_manager.navigate_to_latest_post_mobile(
                    blog_name)
                if not latest_post_success:
                    self.logger.warning(f"{blog_name} 최신 게시글 이동 실패 - 건너뛰기")
                    continue

                # 현재 페이지에서 게시글 상호작용 처리 (모바일 방식)
                interaction_success = self.post_interaction.process_current_page_interaction(
                    blog_name)
                if interaction_success:
                    self.logger.info(f"게시글 상호작용 완료: {blog_name}")
                else:
                    self.logger.warning(f"게시글 상호작용 실패: {blog_name}")

                if i < total_count:
                    delay = random.uniform(1, 2)
                    time.sleep(delay)

            success_count = self.buddy_manager.get_buddy_success_count()
            self.logger.info(
                f"이웃커넥트 모바일 블로그 처리 완료: {success_count}/{total_count} 성공")
            return success_count, total_count

        except Exception as e:
            self.logger.error(f"블로그 처리 중 오류: {e}")
            return 0, len(blog_data) if blog_data else 0

        finally:
            self.cleanup_driver()

    def process_keyword_blog_automation(self, blog_data, progress_callback=None):
        """키워드 검색 블로그 자동화 메인 프로세스 (모바일 서이추 사용)"""
        try:
            total_count = len(blog_data)

            if not self.buddy_manager or not self.post_interaction:
                self.logger.error("필요한 모듈이 초기화되지 않았습니다.")
                return 0, total_count

            self.buddy_manager.reset_buddy_count()
            self.logger.info(f"총 {total_count}개 키워드 검색 블로그 처리를 시작합니다.")

            for i, data in enumerate(blog_data, 1):
                blog_name = data['blog_name']
                post_url = data['post_url']

                self.logger.info(
                    f"[{i}/{total_count}] {blog_name} 키워드 블로그 처리 중...")

                if progress_callback:
                    progress_callback(i, total_count, blog_name)

                self.buddy_manager.buddy_available = False
                # 모바일 서이추 사용
                self.buddy_manager.add_buddy_to_blog_mobile(blog_name)

                if not self.buddy_manager.buddy_available:
                    self.logger.warning(
                        f"{blog_name} 모바일 서로이웃 추가 불가능 - 건너뛰기")
                    continue

                # 설정에서 공감/댓글 옵션 확인
                from utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                enable_like = config_manager.get('enable_like', True)
                enable_comment = config_manager.get('enable_comment', True)

                # 공감/댓글이 모두 비활성화된 경우 바로 다음 블로그로
                if not enable_like and not enable_comment:
                    self.logger.info(
                        f"[{blog_name}] 공감/댓글 모두 비활성화 - 서이추만 완료하고 다음 블로그로 이동")
                    continue

                # 공감/댓글 중 하나라도 활성화된 경우 게시글로 이동
                # 서이추 후 메인 블로그 페이지에서 최신 게시글로 이동
                latest_post_success = self.buddy_manager.navigate_to_latest_post_mobile(
                    blog_name)
                if not latest_post_success:
                    self.logger.warning(f"{blog_name} 최신 게시글 이동 실패 - 건너뛰기")
                    continue

                # 현재 페이지에서 게시글 상호작용 처리 (모바일 방식)
                interaction_success = self.post_interaction.process_current_page_interaction(
                    blog_name)
                if interaction_success:
                    self.logger.info(f"게시글 상호작용 완료: {blog_name}")
                else:
                    self.logger.warning(f"게시글 상호작용 실패: {blog_name}")

                if i < total_count:
                    delay = random.uniform(1, 2)
                    time.sleep(delay)

            success_count = self.buddy_manager.get_buddy_success_count()
            self.logger.info(
                f"키워드 블로그 처리 완료: {success_count}/{total_count} 성공")
            return success_count, total_count

        except Exception as e:
            self.logger.error(f"키워드 블로그 처리 중 오류: {e}")
            return 0, len(blog_data) if blog_data else 0

        finally:
            self.cleanup_driver()

    def cleanup_driver(self):
        """자동화 완료 후 브라우저 드라이버 완전 정리"""
        try:
            if self.driver:
                self.logger.info("자동화 완료, 브라우저 정리 중...")

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
                    self.logger.info("브라우저 드라이버 정리 완료")
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
