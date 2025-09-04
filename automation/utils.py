import time
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.logger import setup_logger

class AutomationUtils:
    """자동화 유틸리티 클래스"""
    
    def __init__(self, driver):
        self.driver = driver
        self.logger = setup_logger()
    
    @staticmethod
    def random_delay(min_seconds=1, max_seconds=3):
        """랜덤 대기"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return delay
    
    def human_like_scroll(self, scroll_count=3, scroll_delay=2):
        """사람처럼 스크롤하기"""
        try:
            for i in range(scroll_count):
                # 랜덤한 스크롤 거리
                scroll_distance = random.randint(300, 800)
                
                # 아래로 스크롤
                self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
                self.random_delay(scroll_delay * 0.5, scroll_delay * 1.5)
                
                # 가끔 위로도 스크롤 (더 자연스럽게)
                if random.random() < 0.3:  # 30% 확률
                    up_scroll = random.randint(100, 300)
                    self.driver.execute_script(f"window.scrollBy(0, -{up_scroll});")
                    self.random_delay(0.5, 1.0)
            
            # 마지막에 페이지 하단으로 스크롤
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.random_delay(1, 2)
            
            self.logger.info(f"페이지 스크롤 완료 ({scroll_count}회)")
            return True
            
        except Exception as e:
            self.logger.error(f"스크롤 실행 실패: {e}")
            return False
    
    def safe_click(self, element, max_retries=3):
        """안전한 클릭 (재시도 포함)"""
        for attempt in range(max_retries):
            try:
                # 요소가 클릭 가능할 때까지 대기
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(element)
                )
                
                # 요소로 스크롤
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                self.random_delay(0.5, 1.0)
                
                # 클릭
                element.click()
                self.random_delay(0.5, 1.5)
                
                return True
                
            except Exception as e:
                self.logger.warning(f"클릭 시도 {attempt + 1} 실패: {e}")
                if attempt < max_retries - 1:
                    self.random_delay(1, 2)
                    
                    # JavaScript 클릭 시도
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                        self.random_delay(0.5, 1.5)
                        return True
                    except:
                        continue
        
        return False
    
    def safe_send_keys(self, element, text, clear_first=True):
        """안전한 텍스트 입력"""
        try:
            if clear_first:
                element.clear()
                self.random_delay(0.2, 0.5)
            
            # 사람처럼 한 글자씩 입력
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            self.random_delay(0.5, 1.0)
            return True
            
        except Exception as e:
            self.logger.error(f"텍스트 입력 실패: {e}")
            return False
    
    def switch_to_frame(self, frame_locator, timeout=10):
        """iframe으로 전환"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            frame = wait.until(EC.frame_to_be_available_and_switch_to_it(frame_locator))
            self.logger.info("iframe으로 전환 완료")
            return True
        except TimeoutException:
            self.logger.error("iframe 전환 시간 초과")
            return False
        except Exception as e:
            self.logger.error(f"iframe 전환 실패: {e}")
            return False
    
    def switch_to_default(self):
        """메인 프레임으로 돌아가기"""
        try:
            self.driver.switch_to.default_content()
            self.logger.info("메인 프레임으로 복귀")
            return True
        except Exception as e:
            self.logger.error(f"메인 프레임 복귀 실패: {e}")
            return False
    
    def wait_for_page_load(self, timeout=10):
        """페이지 로딩 완료 대기"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            self.random_delay(1, 2)  # 추가 안정화 시간
            return True
        except TimeoutException:
            self.logger.warning("페이지 로딩 시간 초과")
            return False
        except Exception as e:
            self.logger.error(f"페이지 로딩 대기 실패: {e}")
            return False
    
    def handle_alert(self, accept=True):
        """알림창 처리"""
        try:
            alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            
            if accept:
                alert.accept()
            else:
                alert.dismiss()
            
            self.logger.info(f"알림창 처리 완료: {alert_text}")
            return alert_text
            
        except TimeoutException:
            return None
        except Exception as e:
            self.logger.error(f"알림창 처리 실패: {e}")
            return None
    
    def get_current_window_handles(self):
        """현재 윈도우 핸들 목록 반환"""
        return self.driver.window_handles
    
    def switch_to_new_window(self):
        """새 윈도우로 전환"""
        try:
            current_windows = self.get_current_window_handles()
            if len(current_windows) > 1:
                # 가장 최근에 열린 윈도우로 전환
                self.driver.switch_to.window(current_windows[-1])
                self.logger.info("새 윈도우로 전환 완료")
                return True
            return False
        except Exception as e:
            self.logger.error(f"새 윈도우 전환 실패: {e}")
            return False
    
    def close_current_window_and_switch_back(self):
        """현재 윈도우 닫고 이전 윈도우로 돌아가기"""
        try:
            current_windows = self.get_current_window_handles()
            if len(current_windows) > 1:
                self.driver.close()
                self.driver.switch_to.window(current_windows[0])
                self.logger.info("윈도우 닫기 및 복귀 완료")
                return True
            return False
        except Exception as e:
            self.logger.error(f"윈도우 닫기 실패: {e}")
            return False