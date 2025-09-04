import time
import random
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
# from webdriver_manager.chrome import ChromeDriverManager  # 문제 발생으로 주석 처리
from utils.logger import setup_logger

class NaverLogin:
    """네이버 로그인 자동화 클래스"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.logger = setup_logger()
        self.headless = headless
        self.login_url = "https://nid.naver.com/nidlogin.login?mode=form&url=https://www.naver.com/"
    
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        try:
            # Chrome 옵션 설정
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # 봇 감지 우회 옵션들
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User-Agent 설정
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Chrome 브라우저 강제 실행
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            
            # 시스템에 설치된 ChromeDriver 사용
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # JavaScript를 통해 webdriver 속성 제거
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 창 크기 설정
            self.driver.set_window_size(1280, 800)
            
            self.logger.info("Chrome 드라이버가 성공적으로 설정되었습니다.")
            return True
            
        except Exception as e:
            self.logger.error(f"드라이버 설정 실패: {e}")
            return False
    
    def human_like_type(self, element, text, typing_delay_range=(0.05, 0.15)):
        """사람처럼 타이핑하는 함수"""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(*typing_delay_range))
    
    def clipboard_login(self, username, password):
        """클립보드를 이용한 로그인 (CAPTCHA 우회)"""
        try:
            self.logger.info("클립보드를 이용한 로그인 시도...")
            
            # 네이버 로그인 페이지로 이동
            self.driver.get(self.login_url)
            time.sleep(random.uniform(2, 4))
            
            # 로그인 폼 요소 찾기
            wait = WebDriverWait(self.driver, 10)
            
            # 아이디 입력
            username_field = wait.until(EC.element_to_be_clickable((By.ID, "id")))
            username_field.click()
            time.sleep(random.uniform(0.5, 1.0))
            
            # 클립보드에 아이디 복사 후 붙여넣기
            original_clipboard = pyperclip.paste()  # 기존 클립보드 내용 백업
            pyperclip.copy(username)
            time.sleep(0.1)
            
            # Ctrl+V로 붙여넣기
            username_field.send_keys('\ue009v')  # Ctrl+A
            time.sleep(0.1)
            username_field.send_keys('\ue009v')  # Ctrl+V
            time.sleep(random.uniform(0.5, 1.0))
            
            # 비밀번호 입력
            password_field = self.driver.find_element(By.ID, "pw")
            password_field.click()
            time.sleep(random.uniform(0.5, 1.0))
            
            # 클립보드에 비밀번호 복사 후 붙여넣기
            pyperclip.copy(password)
            time.sleep(0.1)
            
            password_field.send_keys('\ue009a')  # Ctrl+A
            time.sleep(0.1)
            password_field.send_keys('\ue009v')  # Ctrl+V
            time.sleep(random.uniform(0.5, 1.0))
            
            # 원래 클립보드 내용 복원
            pyperclip.copy(original_clipboard)
            
            # 로그인 버튼 클릭
            login_button = self.driver.find_element(By.ID, "log.login")
            time.sleep(random.uniform(1, 2))
            login_button.click()
            
            self.logger.info("로그인 버튼을 클릭했습니다.")
            return True
            
        except TimeoutException:
            self.logger.error("로그인 페이지 로딩 시간 초과")
            return False
        except NoSuchElementException as e:
            self.logger.error(f"로그인 요소를 찾을 수 없음: {e}")
            return False
        except Exception as e:
            self.logger.error(f"클립보드 로그인 실패: {e}")
            return False
    
    def direct_typing_login(self, username, password):
        """직접 타이핑을 통한 로그인"""
        try:
            self.logger.info("직접 타이핑을 통한 로그인 시도...")
            
            # 네이버 로그인 페이지로 이동
            self.driver.get(self.login_url)
            time.sleep(random.uniform(2, 4))
            
            # 로그인 폼 요소 찾기
            wait = WebDriverWait(self.driver, 10)
            
            # 아이디 입력
            username_field = wait.until(EC.element_to_be_clickable((By.ID, "id")))
            username_field.click()
            time.sleep(random.uniform(0.5, 1.0))
            self.human_like_type(username_field, username)
            
            # 비밀번호 입력
            password_field = self.driver.find_element(By.ID, "pw")
            password_field.click()
            time.sleep(random.uniform(0.5, 1.0))
            self.human_like_type(password_field, password)
            
            # 로그인 버튼 클릭
            login_button = self.driver.find_element(By.ID, "log.login")
            time.sleep(random.uniform(1, 2))
            login_button.click()
            
            self.logger.info("로그인 버튼을 클릭했습니다.")
            return True
            
        except TimeoutException:
            self.logger.error("로그인 페이지 로딩 시간 초과")
            return False
        except NoSuchElementException as e:
            self.logger.error(f"로그인 요소를 찾을 수 없음: {e}")
            return False
        except Exception as e:
            self.logger.error(f"직접 타이핑 로그인 실패: {e}")
            return False
    
    def check_login_success(self, timeout=30):
        """로그인 성공 여부 확인"""
        try:
            self.logger.info("로그인 결과를 확인하는 중...")
            
            # 로그인 완료 페이지나 에러 메시지를 기다림
            wait = WebDriverWait(self.driver, timeout)
            
            # 여러 가능한 결과를 체크
            for _ in range(timeout):
                current_url = self.driver.current_url
                
                # 로그인 성공 - 메인 페이지나 리다이렉트된 페이지
                if "naver.com" in current_url and "nidlogin.login" not in current_url:
                    self.logger.info("로그인 성공!")
                    return True
                
                # CAPTCHA 또는 추가 인증이 필요한 경우
                try:
                    captcha_element = self.driver.find_element(By.CLASS_NAME, "captcha_box")
                    if captcha_element.is_displayed():
                        self.logger.warning("CAPTCHA 인증이 필요합니다. 수동으로 처리해주세요.")
                        
                        # CAPTCHA를 수동으로 처리할 시간을 줌 (60초)
                        manual_wait_time = 60
                        self.logger.info(f"{manual_wait_time}초간 수동 CAPTCHA 처리를 기다립니다...")
                        
                        for i in range(manual_wait_time):
                            time.sleep(1)
                            current_url = self.driver.current_url
                            if "naver.com" in current_url and "nidlogin.login" not in current_url:
                                self.logger.info("CAPTCHA 처리 완료 후 로그인 성공!")
                                return True
                        
                        self.logger.error("CAPTCHA 처리 시간 초과")
                        return False
                except NoSuchElementException:
                    pass
                
                # 로그인 실패 메시지 체크
                try:
                    error_elements = self.driver.find_elements(By.CLASS_NAME, "error_msg")
                    for error_element in error_elements:
                        if error_element.is_displayed():
                            error_text = error_element.text
                            self.logger.error(f"로그인 실패: {error_text}")
                            return False
                except NoSuchElementException:
                    pass
                
                time.sleep(1)
            
            # 시간 초과
            self.logger.error("로그인 결과 확인 시간 초과")
            return False
            
        except Exception as e:
            self.logger.error(f"로그인 결과 확인 실패: {e}")
            return False
    
    def login(self, username, password, use_clipboard=True, max_retries=2):
        """네이버 로그인 실행"""
        if not self.driver:
            if not self.setup_driver():
                return False
        
        for attempt in range(max_retries):
            self.logger.info(f"로그인 시도 {attempt + 1}/{max_retries}")
            
            try:
                # 첫 번째 시도는 클립보드 방식, 실패 시 직접 타이핑
                if use_clipboard and attempt == 0:
                    success = self.clipboard_login(username, password)
                else:
                    success = self.direct_typing_login(username, password)
                
                if not success:
                    continue
                
                # 로그인 결과 확인
                if self.check_login_success():
                    self.logger.info("네이버 로그인 완료")
                    return True
                else:
                    self.logger.warning(f"로그인 시도 {attempt + 1} 실패")
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(3, 5))
                        
            except Exception as e:
                self.logger.error(f"로그인 시도 {attempt + 1} 중 오류 발생: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 5))
        
        self.logger.error("모든 로그인 시도 실패")
        return False
    
    def is_logged_in(self):
        """로그인 상태 확인"""
        try:
            if not self.driver:
                return False
            
            # 현재 URL이 로그인된 상태인지 확인
            current_url = self.driver.current_url
            if "nidlogin.login" in current_url:
                return False
            
            # 네이버 메인 페이지로 이동해서 로그인 상태 확인
            self.driver.get("https://www.naver.com")
            time.sleep(2)
            
            # 로그인 상태를 나타내는 요소 확인
            try:
                # 로그인된 경우 나타나는 요소들 (예: 프로필 영역)
                login_indicator = self.driver.find_element(By.CLASS_NAME, "MyView-module__link_login___HpHMW")
                return False  # 로그인 링크가 있으면 로그아웃 상태
            except NoSuchElementException:
                return True  # 로그인 링크가 없으면 로그인 상태
                
        except Exception as e:
            self.logger.error(f"로그인 상태 확인 실패: {e}")
            return False
    
    def close(self):
        """드라이버 종료"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("웹 드라이버를 종료했습니다.")
        except Exception as e:
            self.logger.error(f"드라이버 종료 실패: {e}")
    
    def get_driver(self):
        """현재 드라이버 반환"""
        return self.driver
    
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
            
            # 페이지 로딩 대기
            time.sleep(3)
            
            # 검색창 찾기 및 키워드 입력
            self.logger.info(f"키워드 검색: {keyword}")
            
            # class="search" div 안의 input 요소 찾기
            search_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".search input[type='text']"))
            )
            
            # 검색창 클릭 및 키워드 입력
            search_input.click()
            time.sleep(0.5)
            search_input.clear()
            
            # 사람처럼 타이핑
            for char in keyword:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            time.sleep(1)
            
            # Enter 키로 검색 실행
            search_input.send_keys('\n')
            
            self.logger.info(f"키워드 '{keyword}' 검색 완료")
            time.sleep(3)  # 검색 결과 로딩 대기
            
            return True
            
        except Exception as e:
            self.logger.error(f"블로그 검색 중 오류: {e}")
            return False