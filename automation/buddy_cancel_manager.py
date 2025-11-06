import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class BuddyCancelManager:
    """서로이웃 신청 취소 기능을 처리하는 클래스"""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger

    def cancel_buddy_requests_page(self, naver_id):
        """서로이웃 신청을 뒤에서부터 1페이지씩 취소"""
        try:
            # 서로이웃 신청 관리 페이지로 이동
            manage_url = f"https://admin.blog.naver.com/BuddyInviteSentManage.naver?blogId={naver_id}"
            self.logger.info(f" 서로이웃 신청 관리 페이지 접속: {manage_url}")
            self.driver.get(manage_url)
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)
            
            # 마지막 페이지로 이동
            if not self._navigate_to_last_page():
                self.logger.warning(" 마지막 페이지로 이동 실패")
                return False
            
            # 전체선택 체크박스 클릭
            if not self._click_select_all():
                self.logger.warning(" 전체선택 체크박스 클릭 실패")
                return False
            
            # 신청취소 버튼 클릭
            if not self._click_cancel_button():
                self.logger.warning(" 신청취소 버튼 클릭 실패")
                return False
            
            # 확인 알림창 처리 (2번)
            if not self._handle_confirmation_alerts():
                self.logger.warning(" 확인 알림창 처리 실패")
                return False
            
            self.logger.info(" 한 페이지의 서로이웃 신청 취소 완료")
            return True
            
        except Exception as e:
            self.logger.error(f" 서로이웃 신청 취소 중 오류: {e}")
            return False
    
    def _navigate_to_last_page(self):
        """마지막 페이지로 이동"""
        try:
            self.logger.info(" div.paginate 태그 검색 중...")
            
            # div.paginate 태그 찾기
            paginate_div = self.driver.find_element(By.CSS_SELECTOR, "div.paginate")
            self.logger.info(" div.paginate 태그 발견")
            
            # 마지막 페이지 링크 찾기 (마지막 child)
            page_links = paginate_div.find_elements(By.TAG_NAME, "a")
            if page_links:
                last_page_link = page_links[-1]  # 마지막 요소
                self.logger.info(" 마지막 페이지 링크 클릭 중...")
                last_page_link.click()
                
                # 페이지 로딩 대기
                time.sleep(2)
                self.logger.info(" 마지막 페이지로 이동 완료")
                return True
            else:
                # 페이지가 1페이지뿐인 경우
                self.logger.info(" 페이지가 1개뿐 - 현재 페이지에서 진행")
                return True
                
        except NoSuchElementException:
            # paginate div가 없는 경우 (데이터가 없거나 1페이지뿐)
            self.logger.info(" 페이지네이션이 없음 - 현재 페이지에서 진행")
            return True
        except Exception as e:
            self.logger.error(f" 마지막 페이지 이동 중 오류: {e}")
            return False
    
    def _click_select_all(self):
        """전체선택 체크박스 클릭"""
        try:
            self.logger.info(" span.all_select 안의 input 태그 검색 중...")
            
            # span.all_select 안의 input 태그 찾기
            all_select_span = self.driver.find_element(By.CSS_SELECTOR, "span.all_select")
            select_all_input = all_select_span.find_element(By.TAG_NAME, "input")
            
            self.logger.info(" 전체선택 체크박스 발견")
            self.logger.info(" 전체선택 체크박스 클릭 중...")
            
            select_all_input.click()
            time.sleep(1)
            
            self.logger.info(" 전체선택 체크박스 클릭 완료")
            return True
            
        except NoSuchElementException as e:
            self.logger.error(f" 전체선택 체크박스를 찾을 수 없음: {e}")
            return False
        except Exception as e:
            self.logger.error(f" 전체선택 체크박스 클릭 중 오류: {e}")
            return False
    
    def _click_cancel_button(self):
        """신청취소 버튼 클릭"""
        try:
            self.logger.info(" '신청취소' 버튼 검색 중...")
            
            # span.btn2 안의 '신청취소' 텍스트를 가진 버튼 찾기
            btn2_spans = self.driver.find_elements(By.CSS_SELECTOR, "span.btn2")
            
            cancel_button = None
            for span in btn2_spans:
                buttons = span.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if "신청취소" in button.text:
                        cancel_button = button
                        break
                if cancel_button:
                    break
            
            if not cancel_button:
                self.logger.error(" '신청취소' 버튼을 찾을 수 없음")
                return False
            
            self.logger.info(" '신청취소' 버튼 발견")
            self.logger.info(" '신청취소' 버튼 클릭 중...")
            
            cancel_button.click()
            time.sleep(1)
            
            self.logger.info(" '신청취소' 버튼 클릭 완료")
            return True
            
        except Exception as e:
            self.logger.error(f" '신청취소' 버튼 클릭 중 오류: {e}")
            return False
    
    def _handle_confirmation_alerts(self):
        """확인 알림창 처리 (2번의 accept)"""
        try:
            self.logger.info(" 첫 번째 확인 알림창 대기 중...")
            
            # 첫 번째 알림창 처리
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert1 = self.driver.switch_to.alert
            alert_text1 = alert1.text
            self.logger.info(f" 첫 번째 알림창: {alert_text1}")
            
            # accept() 메서드로 확인
            alert1.accept()
            time.sleep(1)
            self.logger.info(" 첫 번째 알림창 확인 완료")
            
            self.logger.info(" 두 번째 확인 알림창 대기 중...")
            
            # 두 번째 알림창 처리
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert2 = self.driver.switch_to.alert
            alert_text2 = alert2.text
            self.logger.info(f" 두 번째 알림창: {alert_text2}")
            
            # accept() 메서드로 확인
            alert2.accept()
            time.sleep(1)
            self.logger.info(" 두 번째 알림창 확인 완료")
            
            self.logger.info(" 모든 확인 알림창 처리 완료")
            return True
            
        except TimeoutException:
            self.logger.warning(" 알림창이 나타나지 않음")
            return False
        except Exception as e:
            self.logger.error(f" 알림창 처리 중 오류: {e}")
            return False