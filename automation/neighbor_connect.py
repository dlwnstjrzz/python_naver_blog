import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


class NeighborConnectCollector:
    """네이버 블로그 이웃커넥트 수집 기능을 처리하는 클래스"""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    def extract_blog_id_from_url(self, blog_url):
        """블로그 URL에서 블로그 아이디를 추출"""
        try:
            # https://blog.naver.com/hahehe- 형태에서 hahehe- 추출
            if "blog.naver.com/" in blog_url:
                parts = blog_url.split("blog.naver.com/")
                if len(parts) > 1:
                    blog_id = parts[1].strip().rstrip('/')
                    return blog_id
            return None
        except Exception as e:
            self.logger.error(f"블로그 아이디 추출 중 오류: {e}")
            return None
    
    def check_neighbor_connect_availability(self, blog_id):
        """이웃커넥트가 공개되어 있는지 확인"""
        try:
            # 이웃커넥트 URL 생성
            neighbor_connect_url = f"https://section.blog.naver.com/connect/ViewMoreFollowers.naver?blogId={blog_id}&widgetSeq=1"
            self.logger.info(f"이웃커넥트 페이지 접속: {neighbor_connect_url}")
            
            # 페이지로 이동
            self.driver.get(neighbor_connect_url)
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)
            
            # 비공개 메시지 확인
            try:
                empty_element = self.driver.find_element(
                    By.XPATH, "//img[@alt='새 글을 구독하는 공개된 이웃이 없습니다.']"
                )
                if empty_element:
                    self.logger.warning(f"블로그 '{blog_id}'는 이웃 커넥트 비공개입니다.")
                    return False, "해당 블로그는 이웃 커넥트 비공개이니 다른 블로그를 선택해주시기 바랍니다."
            except NoSuchElementException:
                # 비공개 메시지가 없으면 공개된 것
                pass
            
            # my_buddy_list 클래스를 가진 ul 태그 찾기
            try:
                buddy_list = self.driver.find_element(By.CSS_SELECTOR, "ul.my_buddy_list")
                self.logger.info(f"이웃커넥트 목록 발견: {blog_id}")
                return True, None
            except NoSuchElementException:
                self.logger.warning(f"이웃커넥트 목록을 찾을 수 없음: {blog_id}")
                return False, "이웃커넥트 목록을 찾을 수 없습니다."
                
        except Exception as e:
            self.logger.error(f"이웃커넥트 가용성 확인 중 오류 ({blog_id}): {e}")
            return False, f"이웃커넥트 확인 중 오류가 발생했습니다: {e}"
    
    def collect_neighbor_blog_urls(self, blog_id):
        """이웃커넥트에서 블로그 URL들을 수집"""
        try:
            # 이미 해당 페이지에 있다고 가정하고 바로 수집 시작
            blog_urls = []
            
            # ul.my_buddy_list 안의 모든 li 태그 찾기
            try:
                buddy_list = self.driver.find_element(By.CSS_SELECTOR, "ul.my_buddy_list")
                li_elements = buddy_list.find_elements(By.TAG_NAME, "li")
                
                self.logger.info(f"발견된 이웃 수: {len(li_elements)}")
                
                for li in li_elements:
                    try:
                        # li 태그 안의 a 태그들 찾기 (블로그 링크)
                        blog_links = li.find_elements(By.CSS_SELECTOR, "a.buddy_name, a.imgbox, a.blog_name")
                        
                        for link in blog_links:
                            href = link.get_attribute("href")
                            if href and "blog.naver.com" in href:
                                # 중복 제거를 위해 블로그 URL만 추출 (포스트 번호 제거)
                                if "/PostView.naver" in href or "/PostList.naver" in href:
                                    # 포스트나 목록 URL에서 블로그 메인 URL 추출
                                    parts = href.split("blog.naver.com/")
                                    if len(parts) > 1:
                                        blog_id_part = parts[1].split("/")[0].split("?")[0]
                                        main_blog_url = f"https://blog.naver.com/{blog_id_part}"
                                        if main_blog_url not in blog_urls:
                                            blog_urls.append(main_blog_url)
                                            self.logger.debug(f"블로그 URL 수집: {main_blog_url}")
                                            break  # 같은 li에서 중복 수집 방지
                                elif href not in blog_urls:
                                    blog_urls.append(href)
                                    self.logger.debug(f"블로그 URL 수집: {href}")
                                    break  # 같은 li에서 중복 수집 방지
                    except Exception as e:
                        self.logger.debug(f"개별 이웃 정보 수집 중 오류: {e}")
                        continue
                
                self.logger.info(f"총 {len(blog_urls)}개의 블로그 URL을 수집했습니다.")
                return blog_urls
                
            except NoSuchElementException:
                self.logger.error(f"이웃커넥트 목록을 찾을 수 없음: {blog_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"이웃커넥트 블로그 URL 수집 중 오류 ({blog_id}): {e}")
            return []
    
    def process_neighbor_connect(self, blog_url):
        """이웃커넥트 전체 처리 프로세스"""
        try:
            # 1. 블로그 아이디 추출
            blog_id = self.extract_blog_id_from_url(blog_url)
            if not blog_id:
                return False, "유효하지 않은 블로그 URL입니다.", []
            
            self.logger.info(f"블로그 아이디 추출 완료: {blog_id}")
            
            # 2. 이웃커넥트 가용성 확인
            is_available, error_message = self.check_neighbor_connect_availability(blog_id)
            if not is_available:
                return False, error_message, []
            
            # 3. 이웃 블로그 URL들 수집
            neighbor_urls = self.collect_neighbor_blog_urls(blog_id)
            if not neighbor_urls:
                return False, "이웃 목록을 수집할 수 없습니다.", []
            
            return True, f"총 {len(neighbor_urls)}개의 이웃 블로그를 수집했습니다.", neighbor_urls
            
        except Exception as e:
            self.logger.error(f"이웃커넥트 처리 중 오류: {e}")
            return False, f"처리 중 오류가 발생했습니다: {e}", []