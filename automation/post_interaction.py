import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException


class PostInteraction:
    """게시글 상호작용 관련 기능을 처리하는 클래스"""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger

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

    def _natural_scrolling_and_stay(self, blog_name):
        """사용자 설정 체류 시간에 따른 자연스러운 스크롤링 - se-main-container 끝까지"""
        try:
            # 설정에서 체류 시간 가져오기 (기본값 10초)
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            stay_time = config_manager.get('stay_time', 10)

            self.logger.info(f"체류 시간 설정: {stay_time}초 - {blog_name}")

            # se-main-container 요소 위치 찾기 (본문 게시글)
            try:
                main_container = self.driver.find_element(
                    By.CSS_SELECTOR, 'div.se-main-container')
                # main-container 요소의 위치와 크기 정보 가져오기
                container_location = main_container.location
                container_size = main_container.size
                container_bottom = container_location['y'] + \
                    container_size['height']
                target_scroll_position = max(
                    0, container_bottom - 50)  # 컨테이너 끝에서 50px 여유

                self.logger.info(
                    f"se-main-container 위치: {container_location['y']}px, 크기: {container_size['height']}px")
                self.logger.info(
                    f"컨테이너 끝: {container_bottom}px, 목표 스크롤 위치: {target_scroll_position}px - {blog_name}")

            except NoSuchElementException:
                self.logger.warning(
                    f"se-main-container를 찾을 수 없음, 기본 스크롤 적용: {blog_name}")
                # main-container를 찾지 못하면 페이지 80%까지 스크롤
                total_height = self.driver.execute_script(
                    "return document.body.scrollHeight")
                viewport_height = self.driver.execute_script(
                    "return window.innerHeight")
                target_scroll_position = min(
                    total_height - viewport_height, total_height * 0.8)

            # 현재 스크롤 위치
            current_scroll = self.driver.execute_script(
                "return window.pageYOffset")

            # 스크롤할 필요가 있는지 확인
            if target_scroll_position <= current_scroll + 100:  # 이미 충분히 스크롤된 상태
                self.logger.info(f"이미 목표 위치에 도달, 체류 시간만 대기: {blog_name}")
                time.sleep(stay_time)
                return

            # 스크롤해야 할 거리 계산
            scroll_distance = target_scroll_position - current_scroll

            # 스크롤 단계 수 (체류 시간 동안 자연스럽게 스크롤)
            scroll_steps = max(5, stay_time // 2)  # 최소 5단계, 대략 2초마다 스크롤
            scroll_step_height = scroll_distance // scroll_steps
            step_delay = stay_time / scroll_steps

            self.logger.info(
                f"스크롤 계획: {scroll_steps}단계, 단계당 {step_delay:.1f}초, 총 거리: {scroll_distance}px - {blog_name}")

            for step in range(scroll_steps):
                # 점진적으로 스크롤 내리기
                target_scroll = current_scroll + \
                    (scroll_step_height * (step + 1))
                target_scroll = min(
                    target_scroll, target_scroll_position)  # 목표 위치를 넘지 않게

                # 부드러운 스크롤 효과
                self.driver.execute_script(
                    f"window.scrollTo({{top: {target_scroll}, behavior: 'smooth'}});")

                self.logger.debug(
                    f"스크롤 단계 {step+1}/{scroll_steps}: {target_scroll}px - {blog_name}")

                # 각 스크롤 단계마다 랜덤한 대기 시간 (더 자연스럽게)
                random_delay = step_delay + random.uniform(-0.5, 0.5)
                random_delay = max(0.5, random_delay)  # 최소 0.5초
                time.sleep(random_delay)

                # 마지막 단계면 정확히 목표 위치로
                if step == scroll_steps - 1:
                    self.driver.execute_script(
                        f"window.scrollTo({{top: {target_scroll_position}, behavior: 'smooth'}});")
                    time.sleep(0.5)

            self.logger.info(f"스크롤링 완료 - se-main-container 끝 도달: {blog_name}")

        except Exception as e:
            self.logger.error(f"자연스러운 스크롤링 중 오류 ({blog_name}): {e}")
            # 오류 발생 시 기본 체류 시간만 대기
            time.sleep(10)

    def _click_like_button(self, blog_name):
        """공감 버튼 클릭 - ActionChains 마우스 시뮬레이션 (재시도 포함)"""
        max_like_attempts = 3

        for attempt in range(max_like_attempts):
            try:
                print(
                    f"[DEBUG] 공감 버튼 클릭 시도 {attempt + 1}/{max_like_attempts}: {blog_name}")

                # 공감 버튼 span 찾기
                like_button = self.driver.find_element(
                    By.CSS_SELECTOR, 'span.u_ico._icon.pcol3')
                print(f"[DEBUG] 공감 버튼 발견: {like_button}")
                print(f"[DEBUG] 버튼 위치: {like_button.location}")
                print(f"[DEBUG] 버튼 크기: {like_button.size}")
                print(f"[DEBUG] 버튼 표시 여부: {like_button.is_displayed()}")

                # ActionChains로 마우스 시뮬레이션 클릭
                print(f"[DEBUG] ActionChains 준비 완료")

                # 요소가 화면에 보이도록 스크롤
                print(f"[DEBUG] 스크롤 시작")
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", like_button)
                time.sleep(0.5)
                print(f"[DEBUG] 스크롤 완료")

                # 스크롤 후 위치 다시 확인
                print(f"[DEBUG] 스크롤 후 버튼 위치: {like_button.location}")
                print(f"[DEBUG] 스크롤 후 버튼 표시 여부: {like_button.is_displayed()}")

                # 마우스 움직임과 클릭
                print(f"[DEBUG] ActionChains 클릭 시작")
                actions = ActionChains(self.driver)
                actions.move_to_element(like_button).pause(
                    0.5).click().perform()
                print(f"[DEBUG] ActionChains 클릭 완료")

                self.logger.info(
                    f"공감 버튼 클릭 완료 (ActionChains, 시도 {attempt + 1}): {blog_name}")
                return True

            except NoSuchElementException:
                print(
                    f"[DEBUG] 공감 버튼을 찾을 수 없음 (시도 {attempt + 1}): {blog_name}")
                self.logger.warning(
                    f"공감 버튼을 찾을 수 없음 (시도 {attempt + 1}): {blog_name}")
                if attempt < max_like_attempts - 1:
                    time.sleep(0.5)  # 재시도 전 잠시 대기
                    continue
                else:
                    return False
            except Exception as e:
                print(f"[DEBUG] 공감 버튼 클릭 중 예외 발생 (시도 {attempt + 1}): {e}")
                print(f"[DEBUG] 예외 타입: {type(e)}")
                self.logger.error(
                    f"공감 버튼 클릭 중 오류 (시도 {attempt + 1}, {blog_name}): {e}")
                if attempt < max_like_attempts - 1:
                    time.sleep(0.5)  # 재시도 전 잠시 대기
                    continue
                else:
                    return False

        return False

    def _extract_nickname_from_post(self):
        """게시글에서 닉네임 추출"""
        try:
            nickname_element = self.driver.find_element(By.ID, "nickNameArea")
            nickname = nickname_element.text.strip()
            self.logger.debug(f"닉네임 추출: {nickname}")
            return nickname
        except:
            self.logger.warning("닉네임 추출 실패")
            return "친구"

    def _generate_random_comment(self, nickname):
        """랜덤 댓글 메시지 생성 (ChromeDriver 호환)"""
        random_comments = [
            f"안녕하세요 {nickname}님! 좋은 글 감사합니다",
            f"{nickname}님의 글 항상 잘 보고 있어요!",
            f"좋은 정보 공유해주셔서 감사해요 {nickname}님!",
            f"{nickname}님 포스팅 너무 유익하네요!",
            f"항상 좋은 글 올려주시는 {nickname}님께 감사드려요!",
            f"{nickname}님 덕분에 많이 배워갑니다!",
            f"오늘도 좋은 하루 보내세요 {nickname}님!",
            f"{nickname}님의 블로그 구경 잘 하고 갑니다!",
            f"유익한 글 잘 읽었습니다 {nickname}님!",
            f"{nickname}님 블로그 자주 방문하게 되네요!",
            f"좋은 글 잘 읽고 갑니다 {nickname}님!",
            f"{nickname}님 블로그 정말 도움이 되네요!",
            f"오늘도 좋은 정보 얻어갑니다 {nickname}님!"
        ]

        selected_comment = random.choice(random_comments)

        # BMP 밖 문자(이모지 등) 제거
        # 안전한 문자만 유지 (한글, 영문, 숫자, 기본 특수문자)
        safe_comment = ''.join(char for char in selected_comment
                               if ord(char) < 65536 and char.isprintable())

        return safe_comment

    def _click_comment_button(self, blog_name, attempt):
        """댓글 버튼 클릭"""
        try:
            # 댓글 버튼 찾기 (area_comment div 직접 클릭)
            comment_button = self.driver.find_element(
                By.CSS_SELECTOR, 'div.area_comment.pcol2')

            # ActionChains로 마우스 시뮬레이션 클릭

            # 요소가 화면에 보이도록 스크롤 (부드럽게)
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", comment_button)
            time.sleep(0.5)

            # 마우스 움직임과 클릭
            actions = ActionChains(self.driver)
            actions.move_to_element(comment_button).pause(
                0.5).click().perform()

            self.logger.info(f"댓글 버튼 클릭 완료 (시도 {attempt}): {blog_name}")
            time.sleep(1)  # 댓글 입력창이 나타날 시간
            return True

        except NoSuchElementException:
            self.logger.warning(f"댓글 버튼을 찾을 수 없음 (시도 {attempt}): {blog_name}")
            return False
        except Exception as e:
            self.logger.error(
                f"댓글 버튼 클릭 중 오류 (시도 {attempt}, {blog_name}): {e}")
            return False

    def _write_comment_text(self, blog_name, attempt):
        """댓글 입력창에 텍스트 작성"""
        try:
            # 댓글 입력창 찾기
            comment_textarea = self.driver.find_element(
                By.CSS_SELECTOR, 'div.u_cbox_text.u_cbox_text_mention[contenteditable="true"]')

            # 닉네임 추출
            nickname = self._extract_nickname_from_post()

            # 랜덤 댓글 메시지 생성
            comment_message = self._generate_random_comment(nickname)

            # ActionChains로 댓글 입력창 클릭
            actions = ActionChains(self.driver)
            actions.move_to_element(comment_textarea).pause(
                0.3).click().perform()
            time.sleep(0.5)

            # 직접 타이핑
            comment_textarea.send_keys(comment_message)

            self.logger.info(
                f"댓글 입력 완료 (시도 {attempt}, {blog_name}): {comment_message}")
            time.sleep(1)
            return True

        except NoSuchElementException:
            self.logger.warning(f"댓글 입력창을 찾을 수 없음 (시도 {attempt}): {blog_name}")
            return False
        except Exception as e:
            self.logger.error(f"댓글 작성 중 오류 (시도 {attempt}, {blog_name}): {e}")
            return False

    def _submit_comment(self, blog_name, attempt):
        """댓글 등록 버튼 클릭"""
        try:
            submit_button = self.driver.find_element(
                By.CSS_SELECTOR, 'span.u_cbox_txt_upload')

            # 등록 버튼이 화면에 보이도록 스크롤
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", submit_button)
            time.sleep(0.5)

            # ActionChains로 클릭
            actions = ActionChains(self.driver)
            actions.move_to_element(submit_button).pause(0.5).click().perform()

            self.logger.info(f"댓글 등록 완료 (시도 {attempt}): {blog_name}")
            time.sleep(1)
            return True

        except NoSuchElementException:
            self.logger.warning(
                f"댓글 등록 버튼을 찾을 수 없음 (시도 {attempt}): {blog_name}")
            return False
        except Exception as e:
            self.logger.error(f"댓글 등록 중 오류 (시도 {attempt}, {blog_name}): {e}")
            return False

    def _add_comment(self, blog_name):
        """댓글 추가 - ActionChains 마우스 시뮬레이션 (재시도 포함)"""
        max_comment_attempts = 3

        for attempt in range(max_comment_attempts):
            try:
                self.logger.info(
                    f"댓글 추가 시도 {attempt + 1}/{max_comment_attempts}: {blog_name}")

                # 1단계: 댓글 버튼 찾기 및 클릭 (재시도)
                comment_button_clicked = self._click_comment_button(
                    blog_name, attempt + 1)
                if not comment_button_clicked:
                    if attempt < max_comment_attempts - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        return False

                # 2단계: 댓글 입력창 찾기 및 댓글 작성 (재시도)
                comment_written = self._write_comment_text(
                    blog_name, attempt + 1)
                if not comment_written:
                    if attempt < max_comment_attempts - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        return False

                # 3단계: 댓글 등록 버튼 클릭 (재시도)
                comment_submitted = self._submit_comment(
                    blog_name, attempt + 1)
                if comment_submitted:
                    self.logger.info(
                        f"댓글 추가 완료 (시도 {attempt + 1}): {blog_name}")
                    return True
                else:
                    if attempt < max_comment_attempts - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        return False

            except Exception as e:
                self.logger.error(
                    f"댓글 추가 중 오류 (시도 {attempt + 1}, {blog_name}): {e}")
                if attempt < max_comment_attempts - 1:
                    time.sleep(0.5)
                    continue
                else:
                    return False

        return False

    def process_post_interaction(self, post_url, blog_name):
        """게시글에서 자연스러운 스크롤링 후 공감, 댓글 처리"""
        try:
            self.logger.info(f"🔄 [{blog_name}] 게시글 상호작용 시작...")
            self.logger.info(f"게시글 접속: {post_url}")
            self.driver.get(post_url)
            time.sleep(0.5)

            # 알림창 체크 및 처리
            if self._handle_alerts():
                time.sleep(0.5)

            # iframe 확인 및 전환
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                self.logger.info(f"iframe 내부로 전환: {blog_name}")
                self.driver.switch_to.frame(iframes[0])
                time.sleep(0.5)

            # 사용자 설정 체류 시간에 따른 자연스러운 스크롤링
            self._natural_scrolling_and_stay(blog_name)

            # 공감 버튼 클릭
            like_success = self._click_like_button(blog_name)

            # 댓글 추가
            comment_success = self._add_comment(blog_name)

            # iframe에서 나가기
            self.driver.switch_to.default_content()

            return like_success or comment_success

        except Exception as e:
            self.logger.error(f"게시글 상호작용 중 오류 ({blog_name}): {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False