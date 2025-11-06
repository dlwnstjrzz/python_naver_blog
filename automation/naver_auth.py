import time
import random
import pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class NaverAuth:
    """네이버 로그인/인증 전용 클래스"""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.login_url = "https://nid.naver.com/nidlogin.login?mode=form&url=https://www.naver.com/"

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
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id"))
            )

            # 로그인 폼 요소 찾기
            wait = WebDriverWait(self.driver, 5)

            # 아이디 입력
            username_field = wait.until(
                EC.element_to_be_clickable((By.ID, "id")))
            username_field.click()
            # 클릭 후 입력 가능 상태 대기
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "id"))
            )

            # 클립보드에 아이디 복사 후 붙여넣기
            original_clipboard = pyperclip.paste()  # 기존 클립보드 내용 백업
            pyperclip.copy(username)
            time.sleep(0.1)  # 클립보드 복사 최소 시간

            # Ctrl+V로 붙여넣기
            username_field.send_keys('\ue009v')  # Ctrl+A
            time.sleep(0.1)  # 키 입력 최소 시간
            username_field.send_keys('\ue009v')  # Ctrl+V

            # 비밀번호 입력
            password_field = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "pw"))
            )
            password_field.click()

            # 클립보드에 비밀번호 복사 후 붙여넣기
            pyperclip.copy(password)
            time.sleep(0.1)  # 클립보드 복사 최소 시간

            password_field.send_keys('\ue009a')  # Ctrl+A
            time.sleep(0.1)  # 키 입력 최소 시간
            password_field.send_keys('\ue009v')  # Ctrl+V

            # 원래 클립보드 내용 복원
            pyperclip.copy(original_clipboard)

            # 로그인 버튼 클릭
            login_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "log.login"))
            )
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
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id"))
            )

            # 로그인 폼 요소 찾기
            wait = WebDriverWait(self.driver, 10)

            # 아이디 입력
            username_field = wait.until(
                EC.element_to_be_clickable((By.ID, "id")))
            username_field.click()
            # 클릭 후 입력 가능 상태 대기
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "id"))
            )
            self.human_like_type(username_field, username)

            # 비밀번호 입력
            password_field = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "pw"))
            )
            password_field.click()
            self.human_like_type(password_field, password)

            # 로그인 버튼 클릭
            login_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "log.login"))
            )
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

    def check_login_success(self, timeout=200):
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
                    captcha_element = self.driver.find_element(
                        By.CLASS_NAME, "captcha_box")
                    if captcha_element.is_displayed():
                        self.logger.warning("CAPTCHA 인증이 필요합니다. 수동으로 처리해주세요.")

                        # CAPTCHA를 수동으로 처리할 시간을 줌 (60초)
                        manual_wait_time = 60
                        self.logger.info(
                            f"{manual_wait_time}초간 수동 CAPTCHA 처리를 기다립니다...")

                        for i in range(manual_wait_time):
                            time.sleep(1)  # CAPTCHA 처리 대기는 time.sleep 유지
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
                    error_elements = self.driver.find_elements(
                        By.CLASS_NAME, "error_msg")
                    for error_element in error_elements:
                        if error_element.is_displayed():
                            error_text = error_element.text
                            self.logger.error(f"로그인 실패: {error_text}")
                            return False
                except NoSuchElementException:
                    pass

                time.sleep(1)  # 상태 확인 간격은 time.sleep 유지

            # 시간 초과
            self.logger.error("로그인 결과 확인 시간 초과")
            return False

        except Exception as e:
            self.logger.error(f"로그인 결과 확인 실패: {e}")
            return False

    def login(self, username, password, use_clipboard=True, max_retries=2):
        """네이버 로그인 실행"""
        for attempt in range(max_retries):
            self.logger.info(f"로그인 시도 {attempt + 1}/{max_retries}")

            try:
                # 직접 타이핑
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
                        # 재시도 간격은 time.sleep 유지
                        time.sleep(random.uniform(3, 5))

            except Exception as e:
                self.logger.error(f"로그인 시도 {attempt + 1} 중 오류 발생: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 5))  # 재시도 간격은 time.sleep 유지

        self.logger.error("모든 로그인 시도 실패")
        return False

    def is_logged_in(self):
        """로그인 상태 확인"""
        try:
            # 현재 URL이 로그인된 상태인지 확인
            current_url = self.driver.current_url
            if "nidlogin.login" in current_url:
                return False

            # 네이버 메인 페이지로 이동해서 로그인 상태 확인
            self.driver.get("https://www.naver.com")
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script(
                    "return document.readyState") == "complete"
            )

            # 로그인 상태를 나타내는 요소 확인
            try:
                # 로그인된 경우 나타나는 요소들 (예: 프로필 영역)
                login_indicator = self.driver.find_element(
                    By.CLASS_NAME, "MyView-module__link_login___HpHMW")
                return False  # 로그인 링크가 있으면 로그아웃 상태
            except NoSuchElementException:
                return True  # 로그인 링크가 없으면 로그인 상태

        except Exception as e:
            self.logger.error(f"로그인 상태 확인 실패: {e}")
            return False
