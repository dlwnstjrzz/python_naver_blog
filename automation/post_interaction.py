import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from utils.ai_comment_generator import AICommentGenerator


class PostInteraction:
    """게시글 상호작용 관련 기능을 처리하는 클래스"""

    def __init__(self, driver, logger, buddy_manager=None):
        self.driver = driver
        self.logger = logger
        self.buddy_manager = buddy_manager
        self.ai_comment_generator = None
        # 미리 추출한 블로그 내용 저장
        self.extracted_title = ""
        self.extracted_content = ""
        # 미리 생성한 AI 댓글 저장
        self.pre_generated_ai_comment = None

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

    def _extract_blog_content(self):
        """모바일 페이지에서 블로그 게시글 제목과 본문 내용 추출"""
        try:
            current_url = self.driver.current_url
            self.logger.info(f" 블로그 내용 추출 시작 - 현재 URL: {current_url}")

            # 이미 추출된 내용이 있으면 사용
            if self.extracted_title or self.extracted_content:
                self.logger.info(
                    f" 미리 추출된 내용 사용 - 제목: {len(self.extracted_title)}자, 본문: {len(self.extracted_content)}자")
                if self.extracted_content:
                    self.logger.info(
                        f" 미리 추출된 본문 내용 (전체):\n{self.extracted_content}")
                return self.extracted_title, self.extracted_content

            # 모바일 페이지가 아니면 빈 값 반환
            if 'm.blog.naver.com' not in current_url:
                self.logger.warning(" 모바일 페이지가 아님 - 내용 추출 건너뜀")
                return "", ""

            self.logger.info(" 모바일 페이지에서 실시간 내용 추출")
            title = ""
            content = ""

            # 모바일 페이지에서 제목 추출
            try:
                title_selectors = [
                    "div.se-module.se-module-text.se-title-text",  # 새로운 네이버 블로그 제목 구조
                    "h3.title_post",  # 기존 모바일 제목
                    "h2.se-title"
                ]
                for selector in title_selectors:
                    self.logger.info(f" 모바일 제목 추출 시도: {selector}")
                    title_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, selector)
                    self.logger.info(
                        f" {selector} 요소 개수: {len(title_elements)}")
                    if title_elements:
                        title = title_elements[0].text.strip()
                        if title:
                            self.logger.info(
                                f" 모바일 제목 추출 성공 ({selector}): '{title[:50]}...'")
                            break
                if not title:
                    self.logger.warning(" 모든 모바일 제목 선택자에서 내용을 찾을 수 없음")
            except Exception as e:
                self.logger.error(f" 모바일 제목 추출 중 오류: {e}")

            # 모바일 페이지에서 본문 추출 - div.se-main-container 안의 p.se-text-paragraph들
            try:
                self.logger.info(
                    f" 모바일 본문 추출 시도: div.se-main-container 내부 p.se-text-paragraph")

                # div.se-main-container 찾기
                main_container = self.driver.find_elements(
                    By.CSS_SELECTOR, "div.se-main-container")
                self.logger.info(
                    f" div.se-main-container 요소 개수: {len(main_container)}")

                if main_container:
                    # 컨테이너 내부의 모든 p.se-text-paragraph 찾기
                    paragraphs = main_container[0].find_elements(
                        By.CSS_SELECTOR, "p.se-text-paragraph")
                    self.logger.info(
                        f" p.se-text-paragraph 개수: {len(paragraphs)}")

                    content_parts = []
                    for i, paragraph in enumerate(paragraphs):
                        try:
                            # 각 p 태그 안의 span 태그들 찾기
                            spans = paragraph.find_elements(
                                By.TAG_NAME, "span")
                            self.logger.debug(
                                f" p[{i}] 안의 span 개수: {len(spans)}")

                            paragraph_text = ""
                            for span in spans:
                                span_text = span.text.strip()
                                if span_text:
                                    paragraph_text += span_text + " "

                            if paragraph_text.strip():
                                content_parts.append(paragraph_text.strip())
                                self.logger.debug(
                                    f" p[{i}] 텍스트: '{paragraph_text.strip()[:100]}...'")
                        except Exception as e:
                            self.logger.debug(f" p[{i}] 처리 중 오류: {e}")

                    # 모든 문단 합치기
                    content = "\n".join(content_parts)

                    if content:
                        self.logger.info(
                            f" 모바일 본문 추출 성공: {len(content_parts)}개 문단, 총 {len(content)}자")
                        self.logger.info(f" 추출된 본문 내용 (전체):\n{content}")
                    else:
                        self.logger.warning(
                            " p.se-text-paragraph에서 텍스트를 찾을 수 없음")

                        # fallback: 전체 컨테이너 텍스트 시도
                        content = main_container[0].text.strip()
                        if content:
                            self.logger.info(
                                f" fallback으로 전체 컨테이너 텍스트 사용: {len(content)}자")
                            self.logger.info(
                                f" fallback 본문 내용 (전체):\n{content}")
                else:
                    self.logger.warning(" div.se-main-container를 찾을 수 없음")

                    # fallback: 다른 선택자들 시도
                    fallback_selectors = ["div.post_view", "div.post_ct"]
                    for selector in fallback_selectors:
                        self.logger.info(f" fallback 본문 추출 시도: {selector}")
                        fallback_elements = self.driver.find_elements(
                            By.CSS_SELECTOR, selector)
                        if fallback_elements:
                            content = fallback_elements[0].text.strip()
                            if content:
                                self.logger.info(
                                    f" fallback 본문 추출 성공 ({selector}): {len(content)}자")
                                break

                if not content:
                    self.logger.warning(" 모든 본문 추출 방법에서 내용을 찾을 수 없음")
            except Exception as e:
                self.logger.error(f" 모바일 본문 추출 중 오류: {e}")

            # 추가 디버깅: 페이지 소스 일부 확인
            if not title and not content:
                self.logger.warning(" 제목과 본문 모두 추출 실패 - 페이지 구조 확인")
                try:
                    page_source = self.driver.page_source[:1000]  # 첫 1000자만
                    self.logger.info(f" 페이지 소스 일부:\n{page_source}")
                except:
                    self.logger.error(" 페이지 소스 확인 실패")

            self.logger.info(
                f" 블로그 내용 추출 완료 - 제목 길이: {len(title)}, 본문 길이: {len(content)}")
            return title, content

        except Exception as e:
            self.logger.error(f" 블로그 내용 추출 중 전체 오류: {e}")
            import traceback
            self.logger.error(f" 스택 트레이스:\n{traceback.format_exc()}")
            return "", ""

    def _generate_comment_message(self, nickname, use_ai=False, gemini_api_key=None):
        """댓글 메시지 생성 (미리 생성된 AI 댓글 또는 랜덤)"""
        self.logger.info(
            f" 댓글 메시지 생성 시작 - AI 사용: {use_ai}, API 키 존재: {bool(gemini_api_key)}")

        # AI 댓글 모드이면 미리 생성된 댓글 사용
        if use_ai and gemini_api_key:
            if self.pre_generated_ai_comment:
                self.logger.info(
                    f" 미리 생성된 AI 댓글 사용: '{self.pre_generated_ai_comment}'")
                return self.pre_generated_ai_comment
            else:
                self.logger.warning(" 미리 생성된 AI 댓글이 없음 - 기본 댓글로 대체")
        else:
            if not use_ai:
                self.logger.info(" 일반 댓글 모드 선택됨")
            else:
                self.logger.warning(" AI 댓글 모드이지만 API 키가 없어서 일반 댓글로 대체")

        # 기본 랜덤 댓글 생성
        self.logger.info(" 기본 랜덤 댓글 생성")
        random_comment = self._generate_random_comment(nickname)
        self.logger.info(f" 기본 댓글 생성 완료: '{random_comment}'")
        return random_comment

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

    def process_current_page_interaction(self, blog_name):
        """현재 페이지에서 모바일 상호작용 처리 (이웃커넥트용 및 키워드검색용)"""
        try:
            # 현재 URL 확인
            current_url = self.driver.current_url
            self.logger.info(f" [{blog_name}] 현재 페이지 상호작용 시작...")
            self.logger.info(f" [{blog_name}] 현재 페이지 URL: {current_url}")

            # 모바일만 지원
            self.logger.info(f" [{blog_name}] 모바일 전용 상호작용 시작")
            return self.process_mobile_post_interaction(blog_name)

        except Exception as e:
            self.logger.error(f"현재 페이지 상호작용 중 오류 ({blog_name}): {e}")
            return False

    def process_mobile_post_interaction(self, blog_name):
        """모바일 게시글에서 공감, 댓글 처리"""
        try:
            # 현재 URL 확인
            current_url = self.driver.current_url
            self.logger.info(f" [{blog_name}] 모바일 게시글 상호작용 시작...")
            self.logger.info(f" [{blog_name}] 현재 페이지 URL: {current_url}")

            # 알림창 체크 및 처리
            if self._handle_alerts():
                time.sleep(0.5)

            # 닉네임 가져오기 (서이추할 때 저장된 닉네임 사용)
            nickname = self._get_saved_nickname(blog_name)

            # 설정에서 공감/댓글 옵션 확인
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            enable_like = config_manager.get('enable_like', True)
            enable_comment = config_manager.get('enable_comment', True)

            self.logger.info(
                f" [{blog_name}] 설정: 공감={enable_like}, 댓글={enable_comment}")

            # 둘 다 비활성화된 경우
            if not enable_like and not enable_comment:
                self.logger.info(f" [{blog_name}] 공감/댓글 모두 비활성화 - 아무것도 하지 않음")
                return True  # 성공으로 처리 (서이추는 완료되었으니까)

            # 공감만 활성화된 경우 (댓글은 비활성화) - 체류 없이 바로 공감만
            if enable_like and not enable_comment:
                self.logger.info(
                    f" [{blog_name}] 공감만 활성화 - 체류 없이 바로 공감 버튼 클릭")
                return self._click_simple_like_button(blog_name)

            # 댓글이 활성화된 경우 (공감과 함께 또는 댓글만) - 기존 로직 사용
            # div.section_t1까지 스크롤 및 체류시간 처리
            if self._mobile_scroll_to_like_section(blog_name):
                like_success = True
                comment_success = True

                # 공감 버튼 클릭 (활성화된 경우에만)
                if enable_like:
                    like_success = self._click_mobile_like_button(blog_name)
                else:
                    self.logger.info(f" [{blog_name}] 공감 비활성화 - 공감 버튼 건너뛰기")

                # 댓글 버튼 클릭 및 댓글 작성 (활성화된 경우에만)
                if enable_comment:
                    comment_success = self._handle_mobile_comment(
                        blog_name, nickname)
                else:
                    self.logger.info(f" [{blog_name}] 댓글 비활성화 - 댓글 작성 건너뛰기")

                return like_success and comment_success
            else:
                self.logger.warning(
                    f" [{blog_name}] div.section_t1 섹션을 찾을 수 없음")
                return False

        except Exception as e:
            self.logger.error(f"모바일 게시글 상호작용 중 오류 ({blog_name}): {e}")
            return False

    def _get_saved_nickname(self, blog_name):
        """서이추할 때 저장된 닉네임 가져오기"""
        try:
            if self.buddy_manager and hasattr(self.buddy_manager, 'current_nickname'):
                saved_nickname = self.buddy_manager.current_nickname
                if saved_nickname:
                    self.logger.info(
                        f" [{blog_name}] 저장된 닉네임 사용: {saved_nickname}")
                    return saved_nickname

            # 저장된 닉네임이 없으면 현재 페이지에서 추출 시도
            self.logger.info(f" [{blog_name}] 저장된 닉네임이 없어서 현재 페이지에서 추출 시도")
            return self._extract_mobile_nickname_fallback()

        except Exception as e:
            self.logger.warning(
                f" [{blog_name}] 닉네임 가져오기 중 오류: {e} - 기본값 사용")
            return "친구"

    def _extract_mobile_nickname_fallback(self):
        """모바일 페이지에서 닉네임 추출 (fallback)"""
        try:
            # strong.name > em 요소에서 닉네임 추출
            nickname_element = self.driver.find_element(
                By.CSS_SELECTOR, "strong.name > em")
            nickname = nickname_element.text.strip()
            self.logger.info(f"현재 페이지에서 닉네임 추출 완료: {nickname}")
            return nickname
        except:
            self.logger.warning("현재 페이지에서 닉네임 추출 실패 - 기본값 사용")
            return "친구"

    def _mobile_scroll_to_like_section(self, blog_name):
        """div.se-main-container 끝까지 스크롤 및 체류시간 처리 + 블로그 내용 미리 추출"""
        try:
            # 스크롤 시작 전에 블로그 내용 미리 추출
            self._extract_and_store_blog_content(blog_name)

            # 설정에서 체류 시간 가져오기
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            stay_time = config_manager.get('stay_time', 10)

            self.logger.info(f" [{blog_name}] 체류 시간 설정: {stay_time}초")

            # div.se-main-container 요소 찾기 및 끝까지 스크롤
            try:
                self.logger.info(
                    f" [{blog_name}] div.se-main-container 검색 중...")
                main_container = self.driver.find_element(
                    By.CSS_SELECTOR, "div.se-main-container")
                self.logger.info(f" [{blog_name}] div.se-main-container 발견")

                # 요소의 위치 정보 가져오기
                element_location = main_container.location
                element_size = main_container.size
                target_scroll_position = element_location['y'] + \
                    element_size['height']

                self.logger.info(
                    f" [{blog_name}] se-main-container 위치: {element_location['y']}px, 크기: {element_size['height']}px")
                self.logger.info(
                    f" [{blog_name}] 목표 스크롤 위치 (끝): {target_scroll_position}px")

                # 현재 스크롤 위치
                current_scroll = self.driver.execute_script(
                    "return window.pageYOffset")
                scroll_distance = target_scroll_position - current_scroll

                # 스크롤 단계 수 계산 (체류 시간에 맞게)
                scroll_steps = max(5, stay_time // 2)
                scroll_step_height = scroll_distance // scroll_steps if scroll_distance != 0 else 0
                step_delay = stay_time / scroll_steps

                self.logger.info(
                    f" [{blog_name}] 스크롤 계획: {scroll_steps}단계, 단계당 {step_delay:.1f}초")

                # 점진적 스크롤
                for step in range(scroll_steps):
                    target_scroll = current_scroll + \
                        (scroll_step_height * (step + 1))
                    target_scroll = min(target_scroll, target_scroll_position)

                    self.driver.execute_script(
                        f"window.scrollTo({{top: {target_scroll}, behavior: 'smooth'}});")
                    self.logger.debug(
                        f" [{blog_name}] 스크롤 단계 {step+1}/{scroll_steps}: {target_scroll}px")

                    time.sleep(step_delay)

                self.logger.info(
                    f" [{blog_name}] div.se-main-container 끝까지 스크롤 완료")
                return True

            except NoSuchElementException:
                self.logger.warning(
                    f" [{blog_name}] div.se-main-container를 찾을 수 없음")
                return False

        except Exception as e:
            self.logger.error(f"모바일 스크롤 처리 중 오류 ({blog_name}): {e}")
            return False

    def _extract_and_store_blog_content(self, blog_name):
        """모바일 페이지에서 블로그 제목과 본문 내용 미리 추출하여 저장하고 AI 댓글 생성"""
        try:
            self.logger.info(f" [{blog_name}] 블로그 내용 미리 추출 시작")

            current_url = self.driver.current_url
            self.logger.info(f" [{blog_name}] 현재 URL: {current_url}")

            # 제목 추출 시도
            title = ""
            title_selectors = [
                "div.se-module.se-module-text.se-title-text",  # 새로운 네이버 블로그 제목 구조
                "h3.title_post",  # 모바일 제목
                "h2.se-title",
                "h1.title",
                ".title"
            ]
            for selector in title_selectors:
                try:
                    self.logger.info(f" [{blog_name}] 제목 추출 시도: {selector}")
                    title_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, selector)
                    self.logger.info(
                        f" [{blog_name}] {selector} 요소 개수: {len(title_elements)}")
                    if title_elements:
                        title = title_elements[0].text.strip()
                        if title:
                            self.logger.info(
                                f" [{blog_name}] 제목 추출 성공 ({selector}): '{title[:50]}...'")
                            break
                except Exception as e:
                    self.logger.debug(
                        f" [{blog_name}] {selector} 제목 추출 중 오류: {e}")

            # 본문 추출 시도 - div.se-main-container 안의 p.se-text-paragraph들
            content = ""
            try:
                self.logger.info(
                    f" [{blog_name}] 본문 추출 시도: div.se-main-container 내부 p.se-text-paragraph")

                # div.se-main-container 찾기
                main_container = self.driver.find_elements(
                    By.CSS_SELECTOR, "div.se-main-container")
                self.logger.info(
                    f" [{blog_name}] div.se-main-container 요소 개수: {len(main_container)}")

                if main_container:
                    # 컨테이너 내부의 모든 p.se-text-paragraph 찾기
                    paragraphs = main_container[0].find_elements(
                        By.CSS_SELECTOR, "p.se-text-paragraph")
                    self.logger.info(
                        f" [{blog_name}] p.se-text-paragraph 개수: {len(paragraphs)}")

                    content_parts = []
                    for i, paragraph in enumerate(paragraphs):
                        try:
                            # 각 p 태그 안의 span 태그들 찾기
                            spans = paragraph.find_elements(
                                By.TAG_NAME, "span")
                            self.logger.debug(
                                f" [{blog_name}] p[{i}] 안의 span 개수: {len(spans)}")

                            paragraph_text = ""
                            for span in spans:
                                span_text = span.text.strip()
                                if span_text:
                                    paragraph_text += span_text + " "

                            if paragraph_text.strip():
                                content_parts.append(paragraph_text.strip())
                                self.logger.debug(
                                    f" [{blog_name}] p[{i}] 텍스트: '{paragraph_text.strip()[:100]}...'")
                        except Exception as e:
                            self.logger.debug(
                                f" [{blog_name}] p[{i}] 처리 중 오류: {e}")

                    # 모든 문단 합치기
                    content = "\n".join(content_parts)

                    if content:
                        self.logger.info(
                            f" [{blog_name}] 본문 추출 성공: {len(content_parts)}개 문단, 총 {len(content)}자")
                        self.logger.info(
                            f" [{blog_name}] 추출된 본문 내용 (전체):\n{content}")
                    else:
                        self.logger.warning(
                            f" [{blog_name}] p.se-text-paragraph에서 텍스트를 찾을 수 없음")

                        # fallback: 전체 컨테이너 텍스트 시도
                        content = main_container[0].text.strip()
                        if content:
                            self.logger.info(
                                f" [{blog_name}] fallback으로 전체 컨테이너 텍스트 사용: {len(content)}자")
                            self.logger.info(
                                f" [{blog_name}] fallback 본문 내용 (전체):\n{content}")
                else:
                    self.logger.warning(
                        f" [{blog_name}] div.se-main-container를 찾을 수 없음")

                    # fallback: 다른 선택자들 시도
                    fallback_selectors = ["div.post_view", "div.post_ct"]
                    for selector in fallback_selectors:
                        self.logger.info(
                            f" [{blog_name}] fallback 본문 추출 시도: {selector}")
                        fallback_elements = self.driver.find_elements(
                            By.CSS_SELECTOR, selector)
                        if fallback_elements:
                            content = fallback_elements[0].text.strip()
                            if content:
                                self.logger.info(
                                    f" [{blog_name}] fallback 본문 추출 성공 ({selector}): {len(content)}자")
                                break

            except Exception as e:
                self.logger.error(f" [{blog_name}] 본문 추출 중 오류: {e}")

            # 결과 저장
            self.extracted_title = title
            self.extracted_content = content

            # 추출된 전체 내용을 로그로 출력
            if title:
                self.logger.info(f" [{blog_name}] 추출된 제목 전체:\n{title}")
            if content:
                self.logger.info(f" [{blog_name}] 추출된 본문 전체:\n{content}")

            # 내용 추출이 성공하면 바로 AI 댓글 생성
            self._pre_generate_ai_comment(blog_name)

            self.logger.info(
                f" [{blog_name}] 블로그 내용 미리 추출 완료 - 제목: {len(title)}자, 본문: {len(content)}자")

            if not title and not content:
                # 디버깅을 위한 페이지 소스 일부 확인
                try:
                    page_source = self.driver.page_source[:2000]
                    self.logger.info(
                        f" [{blog_name}] 추출 실패, 페이지 소스 일부:\n{page_source}")
                except:
                    self.logger.error(f" [{blog_name}] 페이지 소스 확인도 실패")

        except Exception as e:
            self.logger.error(f" [{blog_name}] 블로그 내용 미리 추출 중 오류: {e}")
            import traceback
            self.logger.error(
                f" [{blog_name}] 스택 트레이스:\n{traceback.format_exc()}")
            self.extracted_title = ""
            self.extracted_content = ""

    def _pre_generate_ai_comment(self, blog_name):
        """스크롤 중에 AI 댓글을 미리 생성하여 저장"""
        try:
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()

            # 댓글이 비활성화된 경우 AI 댓글 생성 건너뛰기
            enable_comment = config_manager.get('enable_comment', True)
            if not enable_comment:
                self.logger.info(f" [{blog_name}] 댓글 기능 비활성화 - AI 댓글 생성 건너뛰기")
                return

            comment_type = config_manager.get('comment_type', 'ai')
            use_ai_comment = (comment_type == 'ai')
            gemini_api_key = config_manager.get('gemini_api_key', '')

            if not use_ai_comment or not gemini_api_key:
                self.logger.info(f" [{blog_name}] AI 댓글 생성 건너뜀 (AI 모드 아님)")
                return

            if not self.extracted_content:
                self.logger.warning(
                    f" [{blog_name}] 추출된 본문이 없어서 AI 댓글 생성 불가")
                return

            self.logger.info(f" [{blog_name}] AI 댓글 미리 생성 시작")

            # AI 댓글 생성기 초기화 (한 번만)
            if not self.ai_comment_generator or self.ai_comment_generator.api_key != gemini_api_key:
                self.logger.info(f" [{blog_name}] AI 댓글 생성기 초기화 중...")
                self.ai_comment_generator = AICommentGenerator(
                    gemini_api_key, self.logger)

            # 본문을 2000자로 제한
            content_for_ai = self.extracted_content[:2000]
            if len(self.extracted_content) > 2000:
                self.logger.info(
                    f" [{blog_name}] 본문을 2000자로 제한 (원본: {len(self.extracted_content)}자)")

            # AI 댓글 생성
            ai_comment = self.ai_comment_generator.generate_comment_with_fallback(
                content_for_ai, self.extracted_title)

            if ai_comment:
                self.pre_generated_ai_comment = ai_comment
                self.logger.info(
                    f" [{blog_name}] AI 댓글 미리 생성 완료: '{ai_comment}'")
            else:
                self.logger.warning(f" [{blog_name}] AI 댓글 미리 생성 실패")

        except Exception as e:
            self.logger.error(f" [{blog_name}] AI 댓글 미리 생성 중 오류: {e}")
            import traceback
            self.logger.error(
                f" [{blog_name}] 스택 트레이스:\n{traceback.format_exc()}")
            self.pre_generated_ai_comment = None

    def _click_mobile_like_button(self, blog_name):
        """모바일 공감 버튼 클릭"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            self.logger.info(
                f" [{blog_name}] div.like_area__afpHi 내부 공감 버튼 검색 중...")

            # div.like_area__afpHi 안에 있는 span.u_likeit_icons._icons 찾기
            like_area = self.driver.find_element(
                By.CSS_SELECTOR, "div.like_area__afpHi")
            like_icon = like_area.find_element(
                By.CSS_SELECTOR, "span.u_likeit_icons._icons")

            self.logger.info(
                f" [{blog_name}] 공감 아이콘 발견 (span.u_likeit_icons._icons)")

            # 공감 아이콘 클릭
            self.logger.info(f" [{blog_name}] 공감 아이콘 클릭 중...")
            like_icon.click()
            time.sleep(0.5)

            # ul.u_likeit_layer._faceLayer가 나타날 때까지 대기
            self.logger.info(
                f" [{blog_name}] 공감 레이어 (ul.u_likeit_layer._faceLayer) 대기 중...")
            wait = WebDriverWait(self.driver, 5)
            like_layer = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ul.u_likeit_layer._faceLayer")))
            self.logger.info(f" [{blog_name}] 공감 레이어 발견")

            # 공감 아이콘 위치를 기준으로 상대 위치 클릭 (위로 55px, 오른쪽으로 10px)
            self.logger.info(f" [{blog_name}] 공감 아이콘 기준 상대 위치 클릭 중...")
            
            # 클릭할 위치 계산 (시각적 표시용)
            like_icon_location = like_icon.location
            like_icon_size = like_icon.size
            center_x = like_icon_location['x'] + (like_icon_size['width'] // 2)
            center_y = like_icon_location['y'] + (like_icon_size['height'] // 2)
            target_x = center_x + 10
            target_y = center_y - 55
            
            # 클릭 위치에 빨간 점 표시 (디버깅용)
            self.driver.execute_script(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute';
                dot.style.left = '{target_x}px';
                dot.style.top = '{target_y}px';
                dot.style.width = '10px';
                dot.style.height = '10px';
                dot.style.backgroundColor = 'red';
                dot.style.borderRadius = '50%';
                dot.style.zIndex = '9999';
                dot.id = 'click-indicator-mobile';
                document.body.appendChild(dot);
                setTimeout(function() {{
                    var element = document.getElementById('click-indicator-mobile');
                    if (element) element.remove();
                }}, 3000);
            """)
            
            self.logger.info(f" [{blog_name}] 클릭 위치 표시: ({target_x}, {target_y})")
            
            # ActionChains로 공감 아이콘에서 상대적으로 이동하여 클릭
            actions = ActionChains(self.driver)
            actions.move_to_element(like_icon).move_by_offset(10, -55).click().perform()
            
            self.logger.info(f" [{blog_name}] 모바일 공감 완료")
            return True

        except NoSuchElementException as e:
            self.logger.warning(f" [{blog_name}] 모바일 공감 버튼을 찾을 수 없음: {e}")
            return False
        except Exception as e:
            self.logger.error(f"모바일 공감 버튼 클릭 중 오류 ({blog_name}): {e}")
            return False

    def _click_simple_like_button(self, blog_name):
        """간단 공감 버튼 클릭 (체류 없이 바로 공감만)"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            self.logger.info(
                f" [{blog_name}] 간단 공감 모드 - div.interact_section__y00DX 대기 중... (최대 10초)")

            # div.interact_section__y00DX.is_floating__hiq1u가 나타날 때까지 최대 10초 대기
            wait = WebDriverWait(self.driver, 10)
            interact_section = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.interact_section__y00DX.is_floating__hiq1u")))
            self.logger.info(f" [{blog_name}] div.interact_section__y00DX 발견")

            # div.interact_section__y00DX 안에 있는 span.u_likeit_icons 찾기
            self.logger.info(
                f" [{blog_name}] interact_section 내부 공감 아이콘 검색 중...")
            like_icon = interact_section.find_element(
                By.CSS_SELECTOR, "span.u_likeit_icons")
            self.logger.info(
                f" [{blog_name}] interact_section 내부 공감 아이콘 발견")

            # 여러 방법으로 공감 아이콘 클릭 시도
            self.logger.info(f" [{blog_name}] 공감 아이콘 클릭 시도 중...")

            # 방법 1: ActionChains 클릭
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.move_to_element(like_icon).click().perform()
                self.logger.info(f" [{blog_name}] ActionChains 클릭 완료")
            except Exception as e:
                self.logger.warning(
                    f" [{blog_name}] ActionChains 클릭 실패: {e}")

                # 방법 2: JavaScript 클릭
                try:
                    self.logger.info(f" [{blog_name}] JavaScript 클릭 시도...")
                    self.driver.execute_script(
                        "arguments[0].click();", like_icon)
                    self.logger.info(f" [{blog_name}] JavaScript 클릭 완료")
                except Exception as e2:
                    self.logger.error(
                        f" [{blog_name}] JavaScript 클릭도 실패: {e2}")

                    # 방법 3: 일반 클릭
                    try:
                        self.logger.info(f" [{blog_name}] 일반 클릭 시도...")
                        like_icon.click()
                        self.logger.info(f" [{blog_name}] 일반 클릭 완료")
                    except Exception as e3:
                        self.logger.error(f" [{blog_name}] 모든 클릭 방법 실패: {e3}")
                        return False

            time.sleep(1)  # 클릭 후 반응 시간

            # ul.u_likeit_layer._faceLayer가 나타날 때까지 대기
            self.logger.info(
                f" [{blog_name}] 공감 레이어 (ul.u_likeit_layer._faceLayer) 대기 중...")
            like_layer = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ul.u_likeit_layer._faceLayer")))
            self.logger.info(f" [{blog_name}] 공감 레이어 발견")

            # 공감 아이콘 위치를 기준으로 상대 위치 클릭 (위로 55px, 오른쪽으로 10px)
            self.logger.info(f" [{blog_name}] 공감 아이콘 기준 상대 위치 클릭 중...")
            
            # 클릭할 위치 계산 (시각적 표시용)
            like_icon_location = like_icon.location
            like_icon_size = like_icon.size
            center_x = like_icon_location['x'] + (like_icon_size['width'] // 2)
            center_y = like_icon_location['y'] + (like_icon_size['height'] // 2)
            target_x = center_x + 10
            target_y = center_y - 55
            
            # 클릭 위치에 빨간 점 표시 (디버깅용)
            self.driver.execute_script(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute';
                dot.style.left = '{target_x}px';
                dot.style.top = '{target_y}px';
                dot.style.width = '10px';
                dot.style.height = '10px';
                dot.style.backgroundColor = 'red';
                dot.style.borderRadius = '50%';
                dot.style.zIndex = '9999';
                dot.id = 'click-indicator-simple';
                document.body.appendChild(dot);
                setTimeout(function() {{
                    var element = document.getElementById('click-indicator-simple');
                    if (element) element.remove();
                }}, 3000);
            """)
            
            self.logger.info(f" [{blog_name}] 클릭 위치 표시: ({target_x}, {target_y})")
            
            # ActionChains로 공감 아이콘에서 상대적으로 이동하여 클릭
            actions = ActionChains(self.driver)
            actions.move_to_element(like_icon).move_by_offset(10, -55).click().perform()
            
            self.logger.info(f" [{blog_name}] 간단 공감 완룼")
            return True

        except Exception as e:
            self.logger.error(f"간단 공감 버튼 클릭 중 오류 ({blog_name}): {e}")
            return False

    def _handle_mobile_comment(self, blog_name, nickname):
        """모바일 댓글 처리 (댓글 옵션에 따라 건너뛰기 가능)"""
        try:
            # 이 함수는 이미 enable_comment가 True인 경우에만 호출됨

            # div.comment_area__nxrQe 버튼 찾기 및 클릭
            self.logger.info(
                f" [{blog_name}] div.comment_area__nxrQe 댓글 버튼 검색 중...")
            comment_button = self.driver.find_element(
                By.CSS_SELECTOR, "div.comment_area__nxrQe")
            self.logger.info(f" [{blog_name}] 모바일 댓글 버튼 발견")

            # 댓글 버튼 클릭
            self.logger.info(f" [{blog_name}] 모바일 댓글 버튼 클릭 중...")
            comment_button.click()
            time.sleep(1)  # 토스트 팝업 대기

            self.logger.info(f" [{blog_name}] 댓글 토스트 팝업 활성화")

            # 댓글 입력창에서 댓글 작성
            return self._write_mobile_comment(blog_name, nickname)

        except NoSuchElementException:
            self.logger.warning(
                f" [{blog_name}] div.comment_area__nxrQe 댓글 버튼을 찾을 수 없음")
            return False
        except Exception as e:
            self.logger.error(f"모바일 댓글 처리 중 오류 ({blog_name}): {e}")
            return False

    def _write_mobile_comment(self, blog_name, nickname):
        """모바일 댓글 작성"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # div.u_cbox_inbox가 나타날 때까지 대기 (댓글 팝업 로딩 대기)
            self.logger.info(
                f" [{blog_name}] div.u_cbox_inbox 대기 중... (최대 10초)")
            wait = WebDriverWait(self.driver, 10)
            inbox_element = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.u_cbox_inbox")))
            self.logger.info(f" [{blog_name}] div.u_cbox_inbox 발견")

            # ActionChains로 inbox 클릭
            self.logger.info(
                f" [{blog_name}] ActionChains로 div.u_cbox_inbox 클릭 중...")
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_to_element(inbox_element).click().perform()
            time.sleep(0.5)
            self.logger.info(
                f" [{blog_name}] div.u_cbox_inbox 클릭 완료 - 댓글 입력 모드 활성화")

            # 이제 댓글 입력창 찾기 (활성화된 상태)
            self.logger.info(f" [{blog_name}] 활성화된 댓글 입력창 검색 중...")
            comment_textarea = self.driver.find_element(
                By.CSS_SELECTOR, 'div[contenteditable="true"][data-area-code="RPC.input"]')
            self.logger.info(f" [{blog_name}] 활성화된 댓글 입력창 발견")

            # 설정에서 댓글 타입 옵션 확인
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            comment_type = config_manager.get('comment_type', 'ai')
            use_ai_comment = (comment_type == 'ai')
            gemini_api_key = config_manager.get('gemini_api_key', '')

            # 댓글 메시지 생성 (AI 또는 랜덤)
            comment_message = self._generate_comment_message(
                nickname if nickname else "친구", use_ai_comment, gemini_api_key)

            # ActionChains로 textarea 클릭 후 댓글 입력
            self.logger.info(
                f" [{blog_name}] ActionChains로 댓글 입력창 클릭 및 댓글 작성 중...")
            actions = ActionChains(self.driver)
            actions.move_to_element(comment_textarea).click().perform()
            time.sleep(1)  # 댓글 입력 UI 컴포넌트가 나타날 시간 확보

            # 댓글 텍스트 입력
            comment_textarea.send_keys(comment_message)
            time.sleep(0.5)

            # 추가 대기 시간 - 댓글 입력 후 UI 컴포넌트가 완전히 로드될 때까지
            self.logger.info(f" [{blog_name}] 댓글 입력 UI 컴포넌트 로딩 대기...")
            time.sleep(0.5)

            # 비밀댓글 옵션 확인 및 처리
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            is_secret_comment = config_manager.get('secret_comment', False)

            if is_secret_comment:
                # 비밀댓글 체크박스 찾기 및 클릭 (WebDriverWait 사용)
                try:
                    self.logger.info(f" [{blog_name}] 비밀댓글 체크박스 검색 중...")

                    # WebDriverWait로 요소가 나타날 때까지 대기 (최대 5초)
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC

                    wait = WebDriverWait(self.driver, 5)
                    secret_span = wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "span.u_cbox_secret_tag")))
                    secret_checkbox = secret_span.find_element(
                        By.CSS_SELECTOR, "input.u_cbox_secret_check")
                    self.logger.info(f" [{blog_name}] 비밀댓글 체크박스 발견")

                    # ActionChains로 비밀댓글 체크박스 클릭
                    self.logger.info(f" [{blog_name}] 비밀댓글 체크박스 클릭 중...")
                    actions = ActionChains(self.driver)
                    actions.move_to_element(secret_checkbox).click().perform()
                    time.sleep(0.3)

                    self.logger.info(f" [{blog_name}] 비밀댓글 체크박스 클릭 완료")
                except Exception as e:
                    self.logger.warning(
                        f" [{blog_name}] 비밀댓글 체크박스 처리 중 오류: {e} - 일반 댓글로 등록")

            # 댓글 등록 버튼 찾기 및 클릭 (WebDriverWait 사용)
            self.logger.info(f" [{blog_name}] 댓글 등록 버튼 검색 중...")
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                wait = WebDriverWait(self.driver, 5)
                submit_button = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button.u_cbox_btn_upload.__uis_naverComment_writeButton[data-action="write#request"]')))
                self.logger.info(f" [{blog_name}] 댓글 등록 버튼 발견")
            except Exception as e:
                self.logger.error(f" [{blog_name}] 댓글 등록 버튼을 찾을 수 없음: {e}")
                return False

            # ActionChains로 등록 버튼 클릭
            comment_type = "비밀댓글" if is_secret_comment else "일반댓글"
            self.logger.info(
                f" [{blog_name}] ActionChains로 {comment_type} 등록 버튼 클릭 중...")
            actions = ActionChains(self.driver)
            actions.move_to_element(submit_button).click().perform()
            time.sleep(1)

            self.logger.info(
                f" [{blog_name}] 모바일 {comment_type} 등록 완료: {comment_message}")
            return True

        except NoSuchElementException as e:
            self.logger.warning(f" [{blog_name}] 필수 요소를 찾을 수 없음: {e}")
            return False
        except Exception as e:
            self.logger.error(f"모바일 댓글 작성 중 오류 ({blog_name}): {e}")
            return False
