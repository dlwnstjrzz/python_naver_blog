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
    
    def get_latest_post_url(self, blog_url):
        """블로그 메인 페이지에서 최신 게시글 URL 가져오기"""
        try:
            self.logger.info(f"최신 게시글 URL 가져오기: {blog_url}")
            
            # 블로그 메인 페이지로 이동
            self.driver.get(blog_url)
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)
            
            # iframe 확인 및 전환
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                self.logger.debug(f"iframe 내부로 전환")
                self.driver.switch_to.frame(iframes[0])
                time.sleep(0.5)
            
            # 최신 게시글 링크 찾기 - 여러 시도
            post_url = None
            
            # 시도 1: se-module-oglink 클래스 (스마트 에디터)
            try:
                post_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "a.se-module-oglink")
                if post_elements:
                    post_url = post_elements[0].get_attribute("href")
                    self.logger.debug(f"se-module-oglink에서 URL 찾음: {post_url}")
            except:
                pass
            
            # 시도 2: 일반 게시글 링크
            if not post_url:
                try:
                    post_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, "a[href*='/PostView.naver']")
                    if post_elements:
                        post_url = post_elements[0].get_attribute("href")
                        self.logger.debug(f"PostView 링크에서 URL 찾음: {post_url}")
                except:
                    pass
            
            # 시도 3: 제목 링크
            if not post_url:
                try:
                    post_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, "a.se-title-text")
                    if post_elements:
                        post_url = post_elements[0].get_attribute("href")
                        self.logger.debug(f"se-title-text에서 URL 찾음: {post_url}")
                except:
                    pass
            
            # iframe에서 나가기
            if len(iframes) > 0:
                self.driver.switch_to.default_content()
            
            if post_url and "blog.naver.com" in post_url:
                self.logger.info(f"최신 게시글 URL 수집 성공: {post_url}")
                return post_url
            else:
                self.logger.warning(f"최신 게시글 URL을 찾을 수 없음: {blog_url}")
                return blog_url  # 실패 시 메인 블로그 URL 반환
                
        except Exception as e:
            self.logger.error(f"최신 게시글 URL 가져오기 실패 ({blog_url}): {e}")
            return blog_url  # 오류 시 메인 블로그 URL 반환

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

    def process_neighbor_connect_with_posts(self, blog_url):
        """이웃커넥트 수집 + 각 블로그의 최신 게시글 URL까지 가져오기"""
        try:
            # 1. 기본 이웃커넥트 처리
            success, message, neighbor_urls = self.process_neighbor_connect(blog_url)
            if not success:
                return False, message, []
            
            # 2. 각 이웃 블로그에서 최신 게시글 URL 가져오기
            blog_data = []
            
            for i, neighbor_url in enumerate(neighbor_urls, 1):
                try:
                    # 블로그 아이디 추출
                    if "blog.naver.com/" in neighbor_url:
                        blog_id = neighbor_url.split("blog.naver.com/")[1].rstrip('/')
                        
                        self.logger.info(f"[{i}/{len(neighbor_urls)}] {blog_id} - 최신 게시글 URL 가져오는 중...")
                        
                        # 최신 게시글 URL 가져오기
                        post_url = self.get_latest_post_url(neighbor_url)
                        
                        blog_data.append({
                            'blog_name': blog_id,
                            'post_url': post_url
                        })
                        
                        # 각 블로그 사이에 잠시 대기 (너무 빠른 연속 접속 방지)
                        if i < len(neighbor_urls):
                            time.sleep(0.5)
                            
                except Exception as e:
                    self.logger.warning(f"블로그 {neighbor_url} 처리 중 오류: {e}")
                    continue
            
            if blog_data:
                return True, f"총 {len(blog_data)}개의 블로그 데이터를 수집했습니다.", blog_data
            else:
                return False, "유효한 블로그 데이터를 수집할 수 없습니다.", []
                
        except Exception as e:
            self.logger.error(f"이웃커넥트 + 게시글 URL 처리 중 오류: {e}")
            return False, f"처리 중 오류가 발생했습니다: {e}", []