import google.generativeai as genai
import time
import random
from typing import Optional


class AICommentGenerator:
    """Gemini API를 사용한 AI 댓글 생성기"""

    def __init__(self, api_key: str, logger=None):
        """
        AI 댓글 생성기 초기화

        Args:
            api_key: Gemini API 키
            logger: 로거 인스턴스
        """
        self.api_key = api_key
        self.logger = logger
        self.model = None
        self._initialize_gemini()

    def _initialize_gemini(self):
        """Gemini API 초기화"""
        try:
            if self.logger:
                self.logger.info(
                    f"🔧 Gemini API 초기화 시작 - API 키 길이: {len(self.api_key)}")

            if not self.api_key or len(self.api_key) < 10:
                raise ValueError(f"유효하지 않은 API 키: 길이 {len(self.api_key)}")

            genai.configure(api_key=self.api_key)
            if self.logger:
                self.logger.info("🔧 genai.configure() 완료")

            self.model = genai.GenerativeModel('gemini-2.5-flash')
            if self.logger:
                self.logger.info("✅ Gemini API 초기화 완료 - GenerativeModel 생성 성공")
        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"❌ Gemini API 초기화 실패 - 예외 타입: {type(e).__name__}")
                self.logger.error(f"❌ 오류 메시지: {str(e)}")
                import traceback
                self.logger.error(f"❌ 전체 스택 트레이스:\n{traceback.format_exc()}")
            self.model = None

    def generate_comment(self, blog_content: str, blog_title: str = "") -> Optional[str]:
        """
        블로그 내용을 분석하여 적절한 댓글 생성

        Args:
            blog_content: 블로그 게시글 본문 내용
            blog_title: 블로그 게시글 제목 (선택)

        Returns:
            생성된 댓글 (1-2줄) 또는 None
        """
        if self.logger:
            self.logger.info("🤖 AI 댓글 생성 시작")

        if not self.model:
            if self.logger:
                self.logger.error("❌ Gemini 모델이 초기화되지 않았습니다 - model is None")
            return None

        if not blog_content.strip():
            if self.logger:
                self.logger.warning(
                    f"⚠️ 블로그 내용이 비어있습니다 - 내용 길이: {len(blog_content)}")
            return None

        try:
            if self.logger:
                self.logger.info(
                    f"📝 블로그 내용 분석 중 - 제목: '{blog_title[:30]}...', 본문 길이: {len(blog_content)}")

            # 프롬프트 구성
            prompt = self._create_comment_prompt(blog_content, blog_title)
            if self.logger:
                self.logger.info(f"📋 프롬프트 생성 완료 - 길이: {len(prompt)}")

            # Gemini API 호출
            if self.logger:
                self.logger.info("🌐 Gemini API 호출 시작")

            response = self.model.generate_content(prompt)

            if self.logger:
                self.logger.info("🌐 Gemini API 응답 수신 완료")
                self.logger.info(f"📨 응답 객체 타입: {type(response)}")
                self.logger.info(
                    f"📨 응답 hasattr text: {hasattr(response, 'text')}")

            if hasattr(response, 'text') and response.text:
                if self.logger:
                    self.logger.info(f"📨 응답 텍스트 길이: {len(response.text)}")
                    self.logger.info(f"📨 원본 응답: '{response.text}'")

                comment = response.text.strip()
                # 댓글 길이 및 형식 검증
                comment = self._validate_and_clean_comment(comment)

                if self.logger:
                    self.logger.info(f"🤖 AI 댓글 생성 완료: '{comment}'")

                return comment
            else:
                if self.logger:
                    self.logger.warning("⚠️ Gemini API에서 빈 응답을 받았습니다")
                    if hasattr(response, 'text'):
                        self.logger.warning(
                            f"⚠️ response.text 내용: '{response.text}'")
                    else:
                        self.logger.warning("⚠️ response 객체에 text 속성이 없음")
                    # 추가 디버깅 정보
                    if hasattr(response, 'candidates'):
                        self.logger.info(
                            f"📨 response.candidates: {response.candidates}")
                    if hasattr(response, 'prompt_feedback'):
                        self.logger.info(
                            f"📨 response.prompt_feedback: {response.prompt_feedback}")
                return None

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"❌ AI 댓글 생성 중 오류 - 예외 타입: {type(e).__name__}")
                self.logger.error(f"❌ 오류 메시지: {str(e)}")
                import traceback
                self.logger.error(f"❌ 전체 스택 트레이스:\n{traceback.format_exc()}")
            return None

    def _create_comment_prompt(self, blog_content: str, blog_title: str = "") -> str:
        """댓글 생성을 위한 프롬프트 작성"""

        title_part = f"제목: {blog_title}\n\n" if blog_title else ""

        prompt = f"""다음은 네이버 블로그 게시글입니다. 이 글을 읽고 자연스럽고 공감되는 댓글을 작성해주세요.

{title_part}내용:
{blog_content[:2000]}  

댓글 작성 가이드라인:
1. 1-2줄의 짧고 자연스러운 댓글, 최대 16자 이내로 짧게 작성
2. 블로그 내용에 대한 공감이나 긍정적인 반응
3. 과도하게 칭찬하지 말고 자연스럽게
4. 질문하지 말것
5. 한국어로 작성
6. 이모티콘은 사용하지 말 것
7. 존댓말 사용
8. 사람들이 안 쓸법한 이상한 비유법이나 칭찬 표현은 쓰지 말것.
9. 담백하고 짧은 칭찬 문구로 적을 것

댓글만 작성해주세요:"""

        return prompt

    def _validate_and_clean_comment(self, comment: str) -> str:
        """댓글 검증 및 정리"""
        # 줄바꿈을 공백으로 변경
        comment = comment.replace('\n', ' ').replace('\r', ' ')

        # 연속된 공백 제거
        comment = ' '.join(comment.split())

        # 길이 제한 (200자)
        if len(comment) > 200:
            comment = comment[:197] + "..."

        # 시작/끝 따옴표 제거
        comment = comment.strip('"').strip("'")

        return comment

    def get_fallback_comments(self) -> list:
        """AI 댓글 생성 실패시 사용할 기본 댓글들"""
        return [
            "좋은 글 잘 읽었습니다!",
            "유용한 정보 감사해요~",
            "공감되는 내용이네요!",
            "좋은 하루 되세요!",
            "잘 보고 갑니다!",
            "도움이 되는 글이네요!",
            "멋진 글 감사합니다!",
            "좋은 정보 공유해주셔서 고마워요!",
        ]

    def generate_comment_with_fallback(self, blog_content: str, blog_title: str = "") -> str:
        """
        AI 댓글 생성, 실패시 기본 댓글 반환

        Args:
            blog_content: 블로그 게시글 본문 내용
            blog_title: 블로그 게시글 제목 (선택)

        Returns:
            생성된 댓글 또는 기본 댓글
        """
        # AI 댓글 생성 시도
        ai_comment = self.generate_comment(blog_content, blog_title)

        if ai_comment:
            return ai_comment

        # 실패시 기본 댓글 중 랜덤 선택
        fallback_comments = self.get_fallback_comments()
        selected_comment = random.choice(fallback_comments)

        if self.logger:
            self.logger.info(f"🔄 AI 댓글 생성 실패, 기본 댓글 사용: {selected_comment}")

        return selected_comment
