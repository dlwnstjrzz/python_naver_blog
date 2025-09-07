import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


class BlogSearcher:
    """네이버 블로그 검색 관련 기능을 처리하는 클래스"""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    def navigate_to_blog_search(self, keyword):
        """네이버 블로그 검색 페이지로 이동하여 키워드 검색"""
        try:
            if not self.driver:
                self.logger.error("드라이버가 초기화되지 않았습니다.")
                return False

            # 네이버 블로그 페이지로 이동
            blog_url = "https://section.blog.naver.com/BlogHome.naver?directoryNo=0&currentPage=1&groupId=0"
            self.logger.info(f"네이버 블로그 페이지로 이동: {blog_url}")
            self.driver.get(blog_url)

            # 검색창 찾기 및 키워드 입력
            self.logger.info(f"키워드 검색: {keyword}")

            # class="search" div 안의 input 요소 찾기
            search_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".search input[type='text']"))
            )

            # 검색창 클릭 및 키워드 입력
            search_input.click()
            search_input.clear()

            # 사람처럼 타이핑
            for char in keyword:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            # 타이핑 완료 후 잠시 대기
            time.sleep(0.2)  # 입력 완료 최소 시간

            # Enter 키로 검색 실행
            search_input.send_keys('\n')

            self.logger.info(f"키워드 '{keyword}' 검색 완료")
            # 검색 결과 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "list_search_post"))
            )
            time.sleep(1)

            return True

        except Exception as e:
            self.logger.error(f"블로그 검색 중 오류: {e}")
            return False

    def extract_blog_names_from_page(self):
        """현재 페이지에서 블로그 이름과 URL들을 추출"""
        try:
            blog_data = []  # {'blog_name': 'xxx', 'post_url': 'xxx'} 형태로 저장

            # list_search_post 클래스를 가진 div들을 찾기
            search_posts = self.driver.find_elements(
                By.CLASS_NAME, "list_search_post")
            self.logger.info(f"검색된 포스트 개수: {len(search_posts)}")

            extracted_blog_names = set()  # 중복 방지용

            for search_post in search_posts:
                try:
                    # info_post 안의 desc_inner 클래스를 가진 a 태그 찾기
                    desc_inner_link = search_post.find_element(
                        By.CSS_SELECTOR, ".info_post .desc_inner")
                    href = desc_inner_link.get_attribute("href")

                    if href and "blog.naver.com" in href:
                        # href에서 블로그 이름 추출: https://blog.naver.com/블로그이름/글아이디
                        parts = href.split("/")
                        if len(parts) >= 4:
                            blog_name = parts[3]  # 블로그이름 부분
                            if blog_name and blog_name not in extracted_blog_names:
                                extracted_blog_names.add(blog_name)
                                blog_data.append({
                                    'blog_name': blog_name,
                                    'post_url': href
                                })
                                self.logger.debug(
                                    f"블로그 데이터 추출: {blog_name} - {href}")

                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.debug(f"블로그 데이터 추출 중 오류: {e}")
                    continue

            self.logger.info(f"현재 페이지에서 {len(blog_data)}개의 블로그 데이터를 추출했습니다.")
            if blog_data:
                self.logger.debug(
                    f"추출된 블로그 데이터: {[data['blog_name'] for data in blog_data]}")
            return blog_data

        except Exception as e:
            self.logger.error(f"블로그 데이터 추출 중 오류: {e}")
            return []

    def scroll_to_bottom(self):
        """페이지 하단까지 스크롤"""
        try:
            last_height = self.driver.execute_script(
                "return document.body.scrollHeight")

            while True:
                # 페이지 하단까지 스크롤
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                # 스크롤 후 내용 로딩 대기
                WebDriverWait(self.driver, 5).until(
                    lambda driver: driver.execute_script(
                        "return document.readyState") == "complete"
                )

                # 새로운 높이 계산
                new_height = self.driver.execute_script(
                    "return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            self.logger.info("페이지 하단까지 스크롤 완료")
            return True

        except Exception as e:
            self.logger.error(f"스크롤 중 오류: {e}")
            return False

    def navigate_to_next_page(self, current_page_num):
        """다음 페이지로 이동"""
        try:
            current_url = self.driver.current_url

            # URL에서 pageNo 부분을 다음 페이지 번호로 변경
            if "pageNo=" in current_url:
                # 기존 pageNo 값을 새로운 값으로 교체
                new_url = current_url.replace(
                    f"pageNo={current_page_num}", f"pageNo={current_page_num + 1}")
            else:
                # pageNo가 없으면 추가
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}pageNo={current_page_num + 1}"

            self.logger.info(f"페이지 {current_page_num + 1}로 이동: {new_url}")
            self.driver.get(new_url)
            # 다음 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "list_search_post"))
            )
            time.sleep(0.5)
            return True

        except Exception as e:
            self.logger.error(f"다음 페이지 이동 중 오류: {e}")
            return False

    def _navigate_to_page(self, page_num):
        """지정된 페이지로 직접 이동"""
        try:
            current_url = self.driver.current_url

            # URL에서 pageNo 부분을 지정된 페이지 번호로 변경
            if "pageNo=" in current_url:
                # 기존 pageNo 값을 새로운 값으로 교체
                import re
                new_url = re.sub(
                    r'pageNo=\d+', f'pageNo={page_num}', current_url)
            else:
                # pageNo가 없으면 추가
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}pageNo={page_num}"

            self.logger.info(f"페이지 {page_num}로 직접 이동: {new_url}")
            self.driver.get(new_url)
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "list_search_post"))
            )
            time.sleep(0.5)
            return True

        except Exception as e:
            self.logger.error(f"페이지 {page_num} 이동 중 오류: {e}")
            return False

    def collect_blog_names(self, target_count, start_page=1):
        """설정된 개수만큼 블로그 데이터를 수집"""
        try:
            collected_blogs = []
            current_page = start_page  # 시작 페이지 설정
            max_pages = start_page + 9  # 시작 페이지부터 10페이지까지
            collected_blog_names = set()  # 중복 방지용

            self.logger.info(
                f"목표 블로그 수집 개수: {target_count}, 시작 페이지: {start_page}")

            # 시작 페이지가 1이 아니면 해당 페이지로 먼저 이동
            if start_page > 1:
                if not self._navigate_to_page(start_page):
                    self.logger.error(f"시작 페이지 {start_page}로 이동 실패")
                    return []

            while len(collected_blogs) < target_count and current_page <= max_pages:
                self.logger.info(f"페이지 {current_page}에서 블로그 수집 중...")

                # 현재 페이지를 하단까지 스크롤
                self.scroll_to_bottom()

                # 현재 페이지에서 블로그 데이터들 추출
                page_blog_data = self.extract_blog_names_from_page()

                # 새로운 블로그 데이터들만 추가 (중복 제거)
                for blog_data in page_blog_data:
                    blog_name = blog_data['blog_name']
                    if blog_name not in collected_blog_names:
                        collected_blog_names.add(blog_name)
                        collected_blogs.append(blog_data)

                        if len(collected_blogs) >= target_count:
                            break

                self.logger.info(
                    f"현재까지 수집된 블로그 수: {len(collected_blogs)}/{target_count}")

                # 목표 개수에 도달했으면 종료
                if len(collected_blogs) >= target_count:
                    break

                # 다음 페이지로 이동
                if current_page < max_pages:
                    if not self.navigate_to_next_page(current_page):
                        self.logger.warning("다음 페이지 이동 실패, 수집 종료")
                        break
                    current_page += 1
                else:
                    self.logger.warning(f"최대 페이지 수({max_pages})에 도달했습니다.")
                    break

            # 목표 개수만큼만 반환
            final_blogs = collected_blogs[:target_count]
            self.logger.info(f"블로그 데이터 수집 완료: {len(final_blogs)}개")

            return final_blogs

        except Exception as e:
            self.logger.error(f"블로그 수집 중 오류: {e}")
            return []