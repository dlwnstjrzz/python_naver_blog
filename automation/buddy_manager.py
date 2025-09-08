import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException


class BuddyManager:
    """서로이웃 추가 관련 기능을 처리하는 클래스"""

    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.buddy_success_count = 0  # 서로이웃 추가 성공 카운트
        self.buddy_available = False  # 서로이웃 추가 가능 여부

    def _handle_alerts(self):
        """알림창 처리"""
        try:
            # 알림창이 있는지 체크
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            self.logger.info(f"알림창 감지: {alert_text}")
            alert.accept()  # 확인 버튼 클릭
            return True
        except:
            # 알림창이 없으면 무시
            return False

    def _handle_popup(self, blog_id):
        """이웃추가 팝업창 처리"""
        try:
            # 팝업창이 나타날 때까지 잠시 대기
            time.sleep(1)

            # 새 창/팝업 확인
            if len(self.driver.window_handles) > 1:
                self.logger.info("새 팝업창으로 전환")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                time.sleep(0.5)

            # radio_bothbuddy 요소 찾기 (서로이웃)
            try:
                radio_bothbuddy = self.driver.find_element(
                    By.CLASS_NAME, "radio_bothbuddy")

                # span 내부의 input 태그에서 disabled 속성 확인
                try:
                    input_element = radio_bothbuddy.find_element(
                        By.TAG_NAME, "input")
                    is_disabled = input_element.get_attribute("disabled")

                    # disabled 속성이 있으면 (값이 "disabled"이거나 빈 문자열)
                    if is_disabled:
                        self.logger.info(
                            f"❌ [{blog_id}] 서로이웃 비활성화됨 (disabled 속성), 다음 아이디로 이동")
                        self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
                        # 팝업창 닫기
                        self.driver.close()
                        if len(self.driver.window_handles) > 0:
                            self.driver.switch_to.window(
                                self.driver.window_handles[0])
                        return False
                    else:
                        self.buddy_available = True  # 서로이웃 추가 가능으로 설정
                except NoSuchElementException:
                    self.logger.warning(
                        f"radio_bothbuddy 내부의 input 요소를 찾을 수 없음: {blog_id}")
                    # input을 찾을 수 없어도 계속 진행 (가능한 것으로 간주)
                    self.buddy_available = True

                # disabled가 아니면 서로이웃 label 클릭
                try:
                    label_bothbuddy = self.driver.find_element(
                        By.CSS_SELECTOR, 'label[for="each_buddy_add"]')
                    label_bothbuddy.click()
                    self.logger.info(f"🔄 [{blog_id}] 서로이웃 선택 완료")
                    time.sleep(0.5)
                except:
                    self.logger.info("서로이웃 label 클릭 실패")

                # '다음' 버튼 찾아서 클릭
                try:
                    next_button = self.driver.find_element(
                        By.XPATH, "//button[contains(text(), '다음')]")
                    next_button.click()
                    self.logger.info("'다음' 버튼 클릭 성공")
                    time.sleep(0.5)

                    # alert 창 처리 (이미 신청 진행중인 경우)
                    alert_handled = self._handle_alerts()
                    if alert_handled:
                        self.logger.info("❌ 이미 서로이웃 신청이 진행중입니다 - 건너뛰기")
                        self.buddy_available = False  # 서로이웃 추가 불가능으로 설정

                        # 브라우저 상태 안전한 초기화
                        self._safe_browser_reset()
                        return False

                    # 서로이웃 메시지 입력 처리
                    buddy_message_success = self._handle_buddy_message()

                    return buddy_message_success
                except NoSuchElementException:
                    # 다른 방법으로 다음 버튼 찾기
                    try:
                        next_button = self.driver.find_element(
                            By.XPATH, "//*[contains(text(), '다음')]")
                        next_button.click()
                        self.logger.info("'다음' 버튼 클릭 성공 (대체 방법)")
                        time.sleep(0.5)

                        # alert 창 처리 (이미 신청 진행중인 경우)
                        alert_handled = self._handle_alerts()
                        if alert_handled:
                            self.logger.info("❌ 이미 서로이웃 신청이 진행중입니다 - 건너뛰기")
                            self.buddy_available = False  # 서로이웃 추가 불가능으로 설정

                           # 브라우저 상태 안전한 초기화
                            self._safe_browser_reset()
                            return False

                        # 서로이웃 메시지 입력 처리
                        self._handle_buddy_message()

                        return True
                    except:
                        self.logger.warning("'다음' 버튼을 찾을 수 없음")
                        return False

            except NoSuchElementException:
                self.logger.warning(f"radio_bothbuddy 요소를 찾을 수 없음: {blog_id}")
                self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
                return False

        except Exception as e:
            self.logger.error(f"팝업창 처리 중 오류: {e}")
            self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
            return False

    def _safe_browser_reset(self):
        """브라우저 상태 안전한 초기화"""
        try:
            # 현재 열려있는 창들 확인
            current_handles = self.driver.window_handles
            self.logger.info(f"현재 열린 창 개수: {len(current_handles)}")

            if len(current_handles) > 1:
                # 팝업창이 있으면 닫기
                try:
                    self.driver.close()
                    time.sleep(0.5)
                    # 메인 창으로 전환
                    remaining_handles = self.driver.window_handles
                    if remaining_handles:
                        self.driver.switch_to.window(remaining_handles[0])
                        self.logger.info("팝업창 닫고 메인창으로 전환 완료")
                except Exception as close_error:
                    self.logger.warning(f"팝업창 닫기 실패: {close_error}")
                    # 실패해도 메인창으로 전환 시도
                    try:
                        main_handles = self.driver.window_handles
                        if main_handles:
                            self.driver.switch_to.window(main_handles[0])
                    except:
                        pass

            # 안전한 페이지로 이동하여 상태 초기화
            try:
                self.driver.get("https://blog.naver.com")
                time.sleep(1)
                self.logger.info("🔄 alert 처리 후 브라우저 상태 초기화 완룜")
            except Exception as nav_error:
                self.logger.warning(f"페이지 이동 실패, 대체 방법 시도: {nav_error}")
                # 대체 방법: 현재 페이지 새로고침
                try:
                    self.driver.refresh()
                    time.sleep(1)
                except:
                    pass

        except Exception as reset_error:
            self.logger.warning(f"브라우저 초기화 중 예외: {reset_error}")

    def _handle_buddy_message(self):
        """서로이웃 메시지 입력 처리"""
        try:
            # 설정에서 서로이웃 메시지 가져오기
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            neighbor_message = config_manager.get(
                'neighbor_message', '안녕하세요! {nickname}님 서로이웃 해요!')

            self.logger.info(f"서로이웃 메시지 설정: {neighbor_message}")

            # 닉네임 변수가 있는지 확인
            if '{nickname}' in neighbor_message:
                try:
                    # name_buddy 요소에서 닉네임 추출
                    name_buddy = self.driver.find_element(
                        By.CLASS_NAME, "name_buddy")
                    nickname = name_buddy.get_attribute("innerHTML")
                    self.logger.info(f"닉네임 추출: {nickname}")

                    # 닉네임으로 변수 치환
                    final_message = neighbor_message.replace(
                        '{nickname}', nickname)
                except:
                    self.logger.warning("닉네임 추출 실패, 원본 메시지 사용")
                    final_message = neighbor_message.replace('{nickname}', '')
            else:
                final_message = neighbor_message

            self.logger.info(f"최종 메시지: {final_message}")

            # textarea에 메시지 입력
            try:
                message_textarea = self.driver.find_element(By.ID, "message")
                message_textarea.clear()
                message_textarea.send_keys(final_message)
                self.logger.info(f"🔄 서로이웃 메시지 입력 완료: {final_message[:20]}...")

                time.sleep(0.5)

                # 최종 '다음' 버튼 클릭 (서로이웃 신청 완료)
                try:
                    final_next_button = self.driver.find_element(
                        By.CSS_SELECTOR, 'a.button_next._addBothBuddy')
                    final_next_button.click()
                    self.logger.info("최종 '다음' 버튼 클릭 - 서로이웃 신청 완료")
                    time.sleep(1)

                    # 팝업창 닫기
                    self._close_popup_and_return()

                    # 서로이웃 추가 성공 카운트 증가
                    self.buddy_success_count += 1
                    self.logger.info(
                        f"✅ 서로이웃 추가 성공 (총 {self.buddy_success_count}명)")
                    return True

                except NoSuchElementException:
                    self.logger.warning("최종 '다음' 버튼을 찾을 수 없음")
                    # 팝업창 닫기
                    self._close_popup_and_return()
                    return False
                except Exception as e:
                    self.logger.error(f"최종 '다음' 버튼 클릭 중 오류: {e}")
                    # 팝업창 닫기
                    self._close_popup_and_return()
                    return False

            except NoSuchElementException:
                self.logger.warning("메시지 textarea를 찾을 수 없음")
                return False
            except Exception as e:
                self.logger.error(f"메시지 입력 중 오류: {e}")
                return False

        except Exception as e:
            self.logger.error(f"서로이웃 메시지 처리 중 오류: {e}")
            return False

    def _close_popup_and_return(self):
        """팝업창 닫고 메인 창으로 돌아가기"""
        try:
            # 현재 창이 팝업창인지 확인
            if len(self.driver.window_handles) > 1:
                # 팝업창 닫기
                self.driver.close()
                self.logger.info("팝업창 닫기 완료")

                # 메인 창으로 전환
                if len(self.driver.window_handles) > 0:
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    self.logger.info("메인 창으로 전환 완료")

                    # iframe에서 나가기 (혹시 iframe 안에 있을 경우)
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass

            time.sleep(1)
            return True

        except Exception as e:
            self.logger.error(f"팝업창 닫기 중 오류: {e}")
            return False

    def add_buddy_to_blog(self, blog_id):
        """특정 블로그에 서로이웃 추가 - 이웃추가 버튼 직접 클릭 방식"""
        try:
            # 메인 블로그 페이지로 이동
            main_blog_url = f"https://blog.naver.com/{blog_id}"
            self.logger.info(f"🔄 [{blog_id}] 서로이웃 추가 시작...")
            self.logger.info(f"메인 블로그 페이지로 이동: {blog_id}")
            self.driver.get(main_blog_url)
            time.sleep(0.5)

            # 알림창 체크 및 처리
            if self._handle_alerts():
                time.sleep(0.5)

            # iframe 확인 및 전환
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                self.logger.info(f"iframe 내부로 전환: {blog_id}")
                self.driver.switch_to.frame(iframes[0])
                time.sleep(0.5)

            # 이웃추가 버튼 찾기 및 클릭 - ActionChains 마우스 시뮬레이션
            try:
                # btn_area 클래스를 가진 div 찾기
                btn_area = self.driver.find_element(By.CLASS_NAME, "btn_area")
                self.logger.info(
                    f"btn_area div 발견, ActionChains 마우스 시뮬레이션으로 클릭: {blog_id}")
                # btn_area 내부의 첫번째 a태그 찾기
                a_tags = btn_area.find_elements(By.TAG_NAME, "a")
                if not a_tags:
                    raise NoSuchElementException(
                        f"btn_area 내부에 a태그가 없음: {blog_id}")

                first_a_tag = a_tags[0]
                self.logger.info(
                    f"btn_area 내부 첫번째 a태그 발견 (총 {len(a_tags)}개): {blog_id}")

                # 이웃추가 버튼 클릭 재시도 로직 (최대 3번)
                max_click_attempts = 3
                popup_opened = False

                for attempt in range(max_click_attempts):
                    self.logger.info(
                        f"이웃추가 버튼 클릭 시도 {attempt + 1}/{max_click_attempts}: {blog_id}")

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", first_a_tag)
                    time.sleep(0.5)

                    # 첫번째 a태그 직접 클릭
                    first_a_tag.click()
                    time.sleep(1)  # 팝업 열리기 대기 시간

                    # 알림창 또는 팝업 처리
                    alert_handled = self._handle_alerts()
                    if alert_handled:
                        self.logger.info(
                            f"❌ [{blog_id}] 이미 서로이웃 신청이 진행중입니다 - 다음 블로그로 이동")
                        self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
                        # iframe에서 나가기
                        self.driver.switch_to.default_content()
                        return False

                    time.sleep(0.5)

                    # 팝업창이 열렸는지 확인 (새 창 또는 URL 변경)
                    if len(self.driver.window_handles) > 1 or "BuddyAdd.naver" in self.driver.current_url:
                        popup_opened = True
                        self.logger.info(
                            f"팝업창 열림 확인됨 (시도 {attempt + 1}): {blog_id}")
                        break
                    else:
                        self.logger.warning(
                            f"팝업창 열림 확인 안됨 (시도 {attempt + 1}): {blog_id}")
                        if attempt < max_click_attempts - 1:
                            time.sleep(0.5)  # 재시도 전 잠시 대기

                if not popup_opened:
                    self.logger.error(
                        f"이웃추가 버튼 클릭 {max_click_attempts}번 시도했으나 팝업창이 열리지 않음: {blog_id}")
                    self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
                    # iframe에서 나가기
                    self.driver.switch_to.default_content()
                    return False

                # 팝업창 처리
                self.logger.info(f"🔄 [{blog_id}] 팝업창 확인 및 처리 중...")
                popup_handled = self._handle_popup(blog_id)
                if popup_handled:
                    self.logger.info(f"✅ [{blog_id}] 팝업창 처리 완료")
                else:
                    self.logger.info(f"❌ [{blog_id}] 팝업창 없음 또는 처리 실패")

            except NoSuchElementException:
                self.logger.warning(f"btn_area div가 존재하지 않음: {blog_id}")
                self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
                # iframe에서 나가기
                self.driver.switch_to.default_content()
                return False

            except Exception as e:
                self.logger.error(f"iframe 내부 처리 중 오류: {e}")
                self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
                # iframe에서 나가기
                self.driver.switch_to.default_content()
                return False

        except Exception as e:
            self.logger.error(f"서로이웃 추가 중 오류 ({blog_id}): {e}")
            self.buddy_available = False  # 서로이웃 추가 불가능으로 설정
            # iframe에서 나가기 (안전장치)
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def get_buddy_success_count(self):
        """현재까지 성공한 서로이웃 추가 수 반환"""
        return self.buddy_success_count

    def reset_buddy_count(self):
        """서로이웃 추가 성공 카운트 초기화"""
        self.buddy_success_count = 0
