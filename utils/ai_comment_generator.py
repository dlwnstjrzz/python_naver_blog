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
                    f"Gemini API 초기화 시작 - API 키 길이: {len(self.api_key)}")

            if not self.api_key or len(self.api_key) < 10:
                raise ValueError(f"유효하지 않은 API 키: 길이 {len(self.api_key)}")

            genai.configure(api_key=self.api_key)
            if self.logger:
                self.logger.info("genai.configure() 완료")

            self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
            if self.logger:
                self.logger.info(" Gemini API 초기화 완료 - GenerativeModel 생성 성공")
        except Exception as e:
            if self.logger:
                self.logger.error(
                    f" Gemini API 초기화 실패 - 예외 타입: {type(e).__name__}")
                self.logger.error(f" 오류 메시지: {str(e)}")
                import traceback
                self.logger.error(f" 전체 스택 트레이스:\n{traceback.format_exc()}")
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
            self.logger.info(" AI 댓글 생성 시작")

        if not self.model:
            if self.logger:
                self.logger.error(" Gemini 모델이 초기화되지 않았습니다 - model is None")
            return None

        if not blog_content.strip():
            if self.logger:
                self.logger.warning(
                    f" 블로그 내용이 비어있습니다 - 내용 길이: {len(blog_content)}")
            return None

        try:
            if self.logger:
                self.logger.info(
                    f" 블로그 내용 분석 중 - 제목: '{blog_title[:30]}...', 본문 길이: {len(blog_content)}")

            # 프롬프트 구성
            prompt = self._create_comment_prompt(blog_content, blog_title)
            if self.logger:
                self.logger.info(f" 프롬프트 생성 완료 - 길이: {len(prompt)}")

            # Gemini API 호출
            if self.logger:
                self.logger.info(" Gemini API 호출 시작")

            response = self.model.generate_content(prompt)

            if self.logger:
                self.logger.info(" Gemini API 응답 수신 완료")
                self.logger.info(f" 응답 객체 타입: {type(response)}")
                self.logger.info(
                    f" 응답 hasattr text: {hasattr(response, 'text')}")

            if hasattr(response, 'text') and response.text:
                if self.logger:
                    self.logger.info(f" 응답 텍스트 길이: {len(response.text)}")
                    self.logger.info(f" 원본 응답: '{response.text}'")

                comment = response.text.strip()
                # 댓글 길이 및 형식 검증
                comment = self._validate_and_clean_comment(comment)

                if self.logger:
                    self.logger.info(f" AI 댓글 생성 완료: '{comment}'")

                return comment
            else:
                if self.logger:
                    self.logger.warning(" Gemini API에서 빈 응답을 받았습니다")
                    if hasattr(response, 'text'):
                        self.logger.warning(
                            f" response.text 내용: '{response.text}'")
                    else:
                        self.logger.warning(" response 객체에 text 속성이 없음")
                    # 추가 디버깅 정보
                    if hasattr(response, 'candidates'):
                        self.logger.info(
                            f" response.candidates: {response.candidates}")
                    if hasattr(response, 'prompt_feedback'):
                        self.logger.info(
                            f" response.prompt_feedback: {response.prompt_feedback}")
                return None

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f" AI 댓글 생성 중 오류 - 예외 타입: {type(e).__name__}")
                self.logger.error(f" 오류 메시지: {str(e)}")
                import traceback
                self.logger.error(f" 전체 스택 트레이스:\n{traceback.format_exc()}")
            return None

    def _create_comment_prompt(self, blog_content: str, blog_title: str = "") -> str:
        """댓글 생성을 위한 프롬프트 작성"""

        title_part = f"제목: {blog_title}\n\n" if blog_title else ""

        prompt = f"""임무: 중립적 독자의 자연스러운 댓글 생성
당신은 방금 흥미로운 블로그 글을 읽은 일반적인 인터넷 사용자입니다.
당신의 임무는 입력된 블로그 글을 완벽히 이해하고, 진짜 사람이 쓴 것처럼 친근하고 짧은 댓글을 작성하는 것입니다.
.
블로그 글 본문 내용은 다음과 같음.
{title_part}내용:
{blog_content[:2000]}  

스타일 및 제약 조건 (필수 준수)
1.  말투/톤: 친근하고 편안한 구어체를 사용하세요. (예: ~네요, ~군요, ~해볼게요)
2.  AI 금지어: '매우 유익한 정보입니다', '깊이 있는 분석', '다음 글도 기대됩니다'와 같은 AI 특유의 정형화된 표현은 절대 사용하지 마세요.
3.  구체적 언급 (핵심): 댓글은 단순히 칭찬하는 것을 넘어, 본문의 특정 내용(가장 인상 깊었던 핵심 문장/단락)을 반드시 1회 이상 구체적으로 언급하며 공감하세요.
4.  감정 표현: 글을 읽고 느낀 놀라움, 재미, 또는 깨달음 등등 하나의 감정을 담아 표현하세요.
5.  길이: 댓글은 최소 1문장, 최대 2문장을 넘지 않도록 간결하게 작성하세요.
6.  생동감: 댓글의 분위기에 맞는 이모티콘 1~2개를 자연스럽게 섞어 사용하세요.
7.  출력 형식: 오직 댓글 내용만 출력하세요.

요청
위 조건을 완벽히 충족하는, 사람이 쓴 것 같은 자연스러운 댓글을 생성해 주세요:"""

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
            self.logger.info(f" AI 댓글 생성 실패, 기본 댓글 사용: {selected_comment}")

        return selected_comment
