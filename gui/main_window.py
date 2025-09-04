import tkinter as tk
from tkinter import messagebox, scrolledtext
import sys
import os
import threading

# 프로젝트 루트 경로를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.config_manager import ConfigManager
from automation.naver_login import NaverLogin


class MainWindow:
    """메인 GUI 윈도우"""
    
    # 상수 정의
    WINDOW_SIZES = {
        'step1': '600x500',
        'step2': '700x900'
    }
    
    FONT_CONFIG = {
        'family': 'Malgun Gothic',
        'size': 18,
        'weight': 'normal'
    }

    def __init__(self):
        self.root = tk.Tk()
        self.config_manager = ConfigManager()
        self.is_running = False
        self.current_step = 1
        
        # 위젯 참조 저장용
        self.widgets = {}
        self.variables = {}
        
        self._initialize_app()
    
    def _initialize_app(self):
        """애플리케이션 초기화"""
        self.init_variables()
        self.setup_fonts()
        self.setup_window()
        self.create_step1_widgets()
        self.load_settings()

    def init_variables(self):
        """위젯 참조 변수들 초기화"""
        # 1단계 위젯들
        self.widgets['step1'] = {}
        # 2단계 위젯들  
        self.widgets['step2'] = {}
        # 변수들
        self.variables['loading_method'] = 'keyword'

    def setup_fonts(self):
        """기본 폰트 설정"""
        font_tuple = (self.FONT_CONFIG['family'], 
                     self.FONT_CONFIG['size'], 
                     self.FONT_CONFIG['weight'])
        self.root.option_add('*Font', font_tuple)
        self.root.tk.call('tk', 'scaling', 1.0)

    def setup_window(self):
        """윈도우 설정"""
        self.root.title("네이버 블로그 자동화")
        self.root.geometry(self.WINDOW_SIZES['step1'])
        self.root.resizable(True, True)
        self.center_window()

    def center_window(self):
        """창을 화면 중앙에 배치"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    # ========== 헬퍼 메서드들 ==========
    
    def _create_text_input(self, parent, label_text, height=1, width=None):
        """텍스트 입력창 생성 헬퍼"""
        frame = tk.Frame(parent)
        frame.pack(fill='x', pady=8, padx=10)
        
        tk.Label(frame, text=label_text).pack(anchor='w')
        
        text_kwargs = {'height': height, 'wrap': tk.NONE}
        if width:
            text_kwargs['width'] = width
            
        text_widget = tk.Text(frame, **text_kwargs)
        text_widget.pack(fill='x', pady=(5, 0))
        
        return text_widget
    
    def _create_section_frame(self, parent, title, pady=(0, 15)):
        """섹션 프레임 생성 헬퍼"""
        frame = tk.LabelFrame(parent, text=title)
        frame.pack(fill='x', pady=pady, padx=5)
        return frame
    
    def _clear_widgets(self):
        """모든 위젯 제거"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_step1_widgets(self):
        """1단계 기본 UI"""
        # 제목
        title_label = tk.Label(
            self.root,
            text="네이버 블로그 자동화 - 1단계: 기본 설정"
        )
        title_label.pack(pady=(20, 30))

        # 메인 프레임
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # 계정 정보 섹션
        self.create_account_section(main_frame)

        # 수집 방식 섹션
        self.create_method_section(main_frame)

        # 버튼 섹션
        self.create_step1_buttons(main_frame)

    def create_account_section(self, parent):
        """계정 정보 섹션"""
        account_frame = self._create_section_frame(parent, "계정 정보")
        
        # ID 입력창
        self.widgets['step1']['id_text'] = self._create_text_input(
            account_frame, "네이버 ID:", height=1
        )
        
        # 비밀번호 입력창
        self.widgets['step1']['password_text'] = self._create_text_input(
            account_frame, "비밀번호:", height=1
        )
        
        # 편의를 위한 직접 참조
        self.id_text = self.widgets['step1']['id_text']
        self.password_text = self.widgets['step1']['password_text']

    def create_method_section(self, parent):
        """수집 방식 섹션"""
        method_frame = self._create_section_frame(parent, "수집 방식")
        
        radio_frame = tk.Frame(method_frame)
        radio_frame.pack(fill='x', pady=8, padx=10)
        
        # 라디오 버튼 설정
        self.variables['loading_method'] = "keyword"
        
        # 라디오 버튼 생성
        self.keyword_radio = tk.Radiobutton(
            radio_frame,
            text="키워드 검색",
            value="keyword",
            command=lambda: self.set_loading_method("keyword")
        )
        self.keyword_radio.pack(anchor='w', pady=2)

        self.connect_radio = tk.Radiobutton(
            radio_frame,
            text="이웃 커넥트",
            value="neighbor_connect",
            command=lambda: self.set_loading_method("neighbor_connect")
        )
        self.connect_radio.pack(anchor='w', pady=2)
        
        # 기본 선택
        self.keyword_radio.select()
        
        # 편의를 위한 직접 참조
        self.loading_method = self.variables['loading_method']

    def set_loading_method(self, method):
        """라디오 버튼 선택 처리"""
        self.loading_method = method

    def create_step1_buttons(self, parent):
        """1단계 버튼들"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill='x', pady=(20, 0))

        # 설정 저장 버튼
        tk.Button(
            button_frame,
            text="설정 저장",
            command=self.save_step1_settings,
            width=12
        ).pack(side='right', padx=(10, 0))

        # 다음 단계 버튼
        tk.Button(
            button_frame,
            text="다음 단계",
            command=self.go_to_step2,
            width=12
        ).pack(side='right')

    def create_step2_widgets(self):
        """2단계 기본 UI"""
        self._clear_widgets()
        self.root.geometry(self.WINDOW_SIZES['step2'])

        # 헤더
        header_frame = tk.Frame(self.root)
        header_frame.pack(fill='x', pady=(20, 10), padx=20)

        tk.Button(
            header_frame,
            text="← 이전",
            command=self.go_back_to_step1,
            width=8
        ).pack(side='left')

        tk.Label(
            header_frame,
            text="네이버 블로그 자동화 - 2단계: 상세 설정"
        ).pack(side='right')

        # 메인 프레임
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # 검색 설정
        if hasattr(self, 'loading_method'):
            if self.loading_method == "keyword":
                self.create_keyword_section(main_frame)
            elif self.loading_method == "neighbor_connect":
                self.create_connect_section(main_frame)

        # 공통 설정 섹션
        self.create_common_section(main_frame)

        # 로그창
        self.create_log_section(main_frame)

        # 버튼
        self.create_step2_buttons(main_frame)

    def create_keyword_section(self, parent):
        """키워드 검색 설정"""
        # 키워드 검색 프레임
        keyword_frame = tk.LabelFrame(
            parent, text="키워드 검색 설정")
        keyword_frame.pack(fill='x', pady=(0, 15), padx=5)

        # 가로 배치를 위한 메인 프레임
        main_frame = tk.Frame(keyword_frame)
        main_frame.pack(fill='x', pady=8, padx=10)

        # 검색 키워드 (왼쪽)
        kw_frame = tk.Frame(main_frame)
        kw_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        tk.Label(kw_frame, text="검색 키워드:").pack(anchor='w')
        self.keyword_text = tk.Text(kw_frame, height=1, wrap=tk.NONE)
        self.keyword_text.pack(fill='x', pady=(5, 0))

        # 블로그 개수 (오른쪽)
        count_frame = tk.Frame(main_frame)
        count_frame.pack(side='left', fill='y', padx=(10, 0))

        tk.Label(count_frame, text="수집할 블로그 개수:").pack(anchor='w')
        self.blog_count_text = tk.Text(count_frame, height=1, wrap=tk.NONE, width=15)
        self.blog_count_text.pack(pady=(5, 0))
        self.blog_count_text.insert('1.0', "10")

    def create_connect_section(self, parent):
        """이웃 커넥트 설정"""
        # 이웃 커넥트 프레임
        connect_frame = tk.LabelFrame(
            parent, text="이웃 커넥트 설정")
        connect_frame.pack(fill='x', pady=(0, 15), padx=5)

        # 가로 배치를 위한 메인 프레임
        main_frame = tk.Frame(connect_frame)
        main_frame.pack(fill='x', pady=8, padx=10)

        # 기준 블로그 URL (왼쪽)
        url_frame = tk.Frame(main_frame)
        url_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        tk.Label(url_frame, text="기준 블로그 URL:").pack(anchor='w')
        self.base_blog_text = tk.Text(url_frame, height=1, wrap=tk.NONE)
        self.base_blog_text.pack(fill='x', pady=(5, 0))

        # 이웃 개수 (오른쪽)
        neighbor_frame = tk.Frame(main_frame)
        neighbor_frame.pack(side='left', fill='y', padx=(10, 0))

        tk.Label(neighbor_frame, text="수집할 이웃 개수:").pack(anchor='w')
        self.neighbor_count_text = tk.Text(neighbor_frame, height=1, wrap=tk.NONE, width=15)
        self.neighbor_count_text.pack(pady=(5, 0))
        self.neighbor_count_text.insert('1.0', "20")

    def create_common_section(self, parent):
        """공통 설정 섹션"""
        # 서로이웃 메시지 설정
        message_frame = tk.LabelFrame(
            parent, text="서로이웃 추가 메시지")
        message_frame.pack(fill='x', pady=(15, 10), padx=5)

        msg_inner = tk.Frame(message_frame)
        msg_inner.pack(fill='x', pady=8, padx=10)

        tk.Label(msg_inner, text="메시지 ({nickname} 변수 사용 가능):").pack(anchor='w')
        self.neighbor_message_text = tk.Text(
            msg_inner, 
            
            height=3, 
            wrap=tk.WORD
        )
        self.neighbor_message_text.pack(fill='x', pady=(5, 0))
        self.neighbor_message_text.insert('1.0', "안녕하세요! {nickname}님 서로이웃 해요!")

        # 댓글 옵션 설정
        comment_frame = tk.LabelFrame(
            parent, text="댓글 작성 옵션")
        comment_frame.pack(fill='x', pady=(0, 10), padx=5)

        # 라디오 버튼들을 가로로 배치
        radio_frame = tk.Frame(comment_frame)
        radio_frame.pack(fill='x', pady=8, padx=10)

        # 댓글 옵션 상태 저장용 변수
        self.comment_option_var = tk.StringVar(value="ai")

        self.ai_radio = tk.Radiobutton(
            radio_frame,
            text="AI로 작성",
            variable=self.comment_option_var,
            value="ai"
        )
        self.ai_radio.pack(side='left', padx=(0, 20))

        self.random_radio = tk.Radiobutton(
            radio_frame,
            text="랜덤 멘트 자동 작성",
            variable=self.comment_option_var,
            value="random"
        )
        self.random_radio.pack(side='left', padx=(0, 20))

        self.none_radio = tk.Radiobutton(
            radio_frame,
            text="댓글 작성 안함",
            variable=self.comment_option_var,
            value="none"
        )
        self.none_radio.pack(side='left')

        # 랜덤 댓글 입력창 (무조건 표시)
        self.random_comments_frame = tk.Frame(comment_frame)
        self.random_comments_frame.pack(fill='x', pady=(10, 8), padx=10)
        
        tk.Label(self.random_comments_frame, text="랜덤 댓글 목록 ({nickname} 변수 사용 가능):").pack(anchor='w')
        
        self.random_comments_text = tk.Text(
            self.random_comments_frame, 
            height=5, 
            wrap=tk.WORD
        )
        self.random_comments_text.pack(fill='x', pady=(5, 0))
        
        # 기본 랜덤 댓글 5개
        default_comments = [
            "좋은 글 잘 읽었어요! {nickname}님",
            "유익한 정보 감사해요~ {nickname}님!",
            "정말 도움이 되는 글이네요 {nickname}님 ㅎㅎ",
            "오늘도 좋은 하루 되세요 {nickname}님!",
            "항상 좋은 글 감사드려요 {nickname}님^^"
        ]
        self.random_comments_text.insert('1.0', '\n'.join(default_comments))

        # 체류 시간 설정
        wait_frame = tk.LabelFrame(
            parent, text="체류 시간 설정")
        wait_frame.pack(fill='x', pady=(0, 10), padx=5)

        wait_inner = tk.Frame(wait_frame)
        wait_inner.pack(fill='x', pady=8, padx=10)

        # 설명과 입력창을 가로로 배치
        tk.Label(wait_inner, text="기본 체류 시간: 20초 + 추가 시간 (초):").pack(side='left')
        self.wait_time_text = tk.Text(wait_inner, height=1, wrap=tk.NONE, width=10)
        self.wait_time_text.pack(side='left', padx=(10, 0))
        
        # 숫자만 입력 가능하게 바인딩
        self.wait_time_text.bind('<KeyPress>', self.validate_number_input)



    def create_log_section(self, parent):
        """로그창 섹션"""
        # 로그 프레임
        log_frame = tk.LabelFrame(parent, text="실행 로그")
        log_frame.pack(fill='both', expand=True, pady=(15, 10), padx=5)
        
        # 스크롤바가 있는 텍스트 위젯
        log_inner = tk.Frame(log_frame)
        log_inner.pack(fill='both', expand=True, pady=8, padx=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_inner,
            height=6,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.log_text.pack(fill='both', expand=True)

    def create_step2_buttons(self, parent):
        """2단계 버튼들"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill='x', pady=(20, 0))

        # 설정 저장 버튼
        tk.Button(
            button_frame,
            text="설정 저장",
            command=self.save_settings,
            
            width=12
        ).pack(side='right', padx=(10, 0))

        # 자동화 시작 버튼
        self.start_button = tk.Button(
            button_frame,
            text="자동화 시작",
            command=self.toggle_automation,
            
            width=12
        )
        self.start_button.pack(side='right')

    def load_settings(self):
        """저장된 설정 불러오기 - Text 위젯 방식"""
        try:
            # 1단계 설정들
            if hasattr(self, 'id_text'):
                self.id_text.delete('1.0', tk.END)
                self.id_text.insert('1.0', self.config_manager.get('naver_id', ''))
            
            if hasattr(self, 'password_text'):
                self.password_text.delete('1.0', tk.END)
                self.password_text.insert('1.0', self.config_manager.get('naver_password', ''))

            # 라디오 버튼 설정
            if hasattr(self, 'loading_method'):
                method = self.config_manager.get('loading_method', 'keyword')
                self.loading_method = method
                if hasattr(self, 'keyword_radio') and hasattr(self, 'connect_radio'):
                    if method == "keyword":
                        self.keyword_radio.select()
                    else:
                        self.connect_radio.select()

            # 2단계 설정들
            if self.current_step == 2:
                # 검색 설정
                if hasattr(self, 'keyword_text'):
                    self.keyword_text.delete('1.0', tk.END)
                    self.keyword_text.insert('1.0', self.config_manager.get('search_keyword', ''))
                
                if hasattr(self, 'blog_count_text'):
                    self.blog_count_text.delete('1.0', tk.END)
                    self.blog_count_text.insert('1.0', str(self.config_manager.get('blog_count', 10)))
                
                if hasattr(self, 'base_blog_text'):
                    self.base_blog_text.delete('1.0', tk.END)
                    self.base_blog_text.insert('1.0', self.config_manager.get('base_blog_url', ''))
                
                if hasattr(self, 'neighbor_count_text'):
                    self.neighbor_count_text.delete('1.0', tk.END)
                    self.neighbor_count_text.insert('1.0', str(self.config_manager.get('neighbor_count', 20)))

                # 서로이웃 메시지
                if hasattr(self, 'neighbor_message_text'):
                    neighbor_msg = self.config_manager.get('neighbor_message', '안녕하세요! {nickname}님 서로이웃 해요!')
                    self.neighbor_message_text.delete('1.0', tk.END)
                    self.neighbor_message_text.insert('1.0', neighbor_msg)
                
                # 댓글 옵션
                if hasattr(self, 'comment_option_var'):
                    option = self.config_manager.get('comment_option', 'ai')
                    self.comment_option_var.set(option)
                
                # 랜덤 댓글 목록
                if hasattr(self, 'random_comments_text'):
                    random_comments = self.config_manager.get('random_comments', [])
                    if random_comments:
                        self.random_comments_text.delete('1.0', tk.END)
                        self.random_comments_text.insert('1.0', '\n'.join(random_comments))
                
                # 체류시간
                if hasattr(self, 'wait_time_text'):
                    wait_time = self.config_manager.get('wait_time', '')
                    self.wait_time_text.delete('1.0', tk.END)
                    self.wait_time_text.insert('1.0', str(wait_time) if wait_time else '')
        except Exception as e:
            pass

    def go_to_step2(self):
        """2단계로 이동"""
        if not self._validate_step1_inputs():
            return
            
        self.save_step1_settings()
        self.current_step = 2
        self.create_step2_widgets()
        self.load_settings()

    def go_back_to_step1(self):
        """1단계로 돌아가기"""
        self.current_step = 1

        self._clear_widgets()
        self.root.geometry(self.WINDOW_SIZES['step1'])

        # 1단계 위젯 재생성
        self.create_step1_widgets()
        self.load_settings()

    def save_step1_settings(self):
        """1단계 설정 저장"""
        try:
            self.config_manager.set('naver_id', self.id_text.get('1.0', tk.END).strip())
            self.config_manager.set('naver_password', self.password_text.get('1.0', tk.END).strip())
            self.config_manager.set('loading_method', self.loading_method)

            if self.config_manager.save_config():
                messagebox.showinfo("저장 완료", "1단계 설정이 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("저장 실패", "설정 저장에 실패했습니다.")

    def save_settings(self):
        """2단계 설정 저장"""
        try:
            # 기본 정보 (안전하게 저장)
            try:
                if hasattr(self, 'id_text') and self.id_text.winfo_exists():
                    self.config_manager.set('naver_id', self.id_text.get('1.0', tk.END).strip())
                if hasattr(self, 'password_text') and self.password_text.winfo_exists():
                    self.config_manager.set('naver_password', self.password_text.get('1.0', tk.END).strip())
            except tk.TclError:
                # 위젯이 파괴된 경우 설정에서 가져오기
                pass
            
            self.config_manager.set('loading_method', self.loading_method)

            # 검색 방식별 설정
            if self.loading_method == "keyword":
                try:
                    if hasattr(self, 'keyword_text') and self.keyword_text.winfo_exists():
                        self.config_manager.set('search_keyword', self.keyword_text.get('1.0', tk.END).strip())
                    if hasattr(self, 'blog_count_text') and self.blog_count_text.winfo_exists():
                        blog_count_text = self.blog_count_text.get('1.0', tk.END).strip()
                        if blog_count_text:
                            self.config_manager.set('blog_count', int(blog_count_text))
                except tk.TclError:
                    pass
            elif self.loading_method == "neighbor_connect":
                try:
                    if hasattr(self, 'base_blog_text') and self.base_blog_text.winfo_exists():
                        self.config_manager.set('base_blog_url', self.base_blog_text.get('1.0', tk.END).strip())
                    if hasattr(self, 'neighbor_count_text') and self.neighbor_count_text.winfo_exists():
                        neighbor_count_text = self.neighbor_count_text.get('1.0', tk.END).strip()
                        if neighbor_count_text:
                            self.config_manager.set('neighbor_count', int(neighbor_count_text))
                except tk.TclError:
                    pass

            # 공통 설정
            try:
                if hasattr(self, 'neighbor_message_text') and self.neighbor_message_text.winfo_exists():
                    neighbor_message = self.neighbor_message_text.get('1.0', tk.END).strip()
                    self.config_manager.set('neighbor_message', neighbor_message)
                if hasattr(self, 'comment_option_var'):
                    self.config_manager.set('comment_option', self.comment_option_var.get())
                
                # 랜덤 댓글
                if hasattr(self, 'comment_option_var') and self.comment_option_var.get() == "random":
                    if hasattr(self, 'random_comments_text') and self.random_comments_text.winfo_exists():
                        random_comments_text = self.random_comments_text.get('1.0', tk.END).strip()
                        random_comments = [line.strip() for line in random_comments_text.split('\n') if line.strip()]
                        self.config_manager.set('random_comments', random_comments)
                
                # 체류시간
                if hasattr(self, 'wait_time_text') and self.wait_time_text.winfo_exists():
                    wait_time_text = self.wait_time_text.get('1.0', tk.END).strip()
                    if wait_time_text:
                        self.config_manager.set('wait_time', int(wait_time_text))
            except tk.TclError:
                pass

            if self.config_manager.save_config():
                messagebox.showinfo("저장 완료", "설정이 저장되었습니다.")
        except ValueError as e:
            messagebox.showerror("입력 오류", "숫자를 올바르게 입력해주세요.")
        except Exception as e:
            messagebox.showerror("저장 실패", f"설정 저장에 실패했습니다: {str(e)}")

    # ========== 설정 및 검증 메서드들 ==========
    
    def validate_number_input(self, event):
        """숫자만 입력 허용하는 검증 함수"""
        if event.keysym in ['BackSpace', 'Delete', 'Tab', 'Return', 'Left', 'Right', 'Up', 'Down']:
            return True
        if event.char.isdigit():
            return True
        return "break"
    
    def _validate_step1_inputs(self):
        """1단계 입력 값 검증"""
        if not self.id_text.get('1.0', tk.END).strip():
            messagebox.showerror("입력 오류", "네이버 ID를 입력해주세요.")
            return False
        if not self.password_text.get('1.0', tk.END).strip():
            messagebox.showerror("입력 오류", "비밀번호를 입력해주세요.")
            return False
        return True
    
    def _get_text_widget_value(self, widget_name, default=''):
        """텍스트 위젯에서 값 추출"""
        if hasattr(self, widget_name):
            widget = getattr(self, widget_name)
            return widget.get('1.0', tk.END).strip()
        return default
    
    def _set_text_widget_value(self, widget_name, value):
        """텍스트 위젯에 값 설정"""
        if hasattr(self, widget_name):
            widget = getattr(self, widget_name)
            widget.delete('1.0', tk.END)
            widget.insert('1.0', str(value) if value else '')

    def log_message(self, message):
        """로그창에 메시지 출력"""
        if hasattr(self, 'log_text'):
            from datetime import datetime
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_message = f"[{timestamp}] {message}\n"
            
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.config(state=tk.DISABLED)
            self.log_text.see(tk.END)

    def toggle_automation(self):
        """자동화 시작/중지"""
        if not self.is_running:
            # 설정 저장
            self.save_settings()

            # 상태 변경
            self.is_running = True
            self.start_button.config(text="자동화 중지")
            self.log_message("자동화를 시작합니다...")
            self.log_message("설정이 저장되었습니다.")
            
            # 네이버 로그인 시작
            self.start_naver_login()
        else:
            # 상태 변경
            self.is_running = False
            self.start_button.config(text="자동화 시작")
            self.log_message("자동화가 중지되었습니다.")
    
    def start_naver_login(self):
        """네이버 로그인 실행 (별도 스레드에서)"""
        try:
            # config_manager에서 저장된 값 사용
            naver_id = self.config_manager.get('naver_id', '')
            naver_password = self.config_manager.get('naver_password', '')
            
            if not naver_id or not naver_password:
                self.log_message("네이버 ID 또는 비밀번호가 설정에 저장되지 않았습니다.")
                self.log_message("설정을 저장한 후 다시 시도해주세요.")
                self.is_running = False
                self.start_button.config(text="자동화 시작")
                return
            
            self.log_message("네이버 로그인 페이지를 열고 있습니다...")
            
            # 별도 스레드에서 로그인 실행 (값을 파라미터로 전달)
            login_thread = threading.Thread(
                target=self._login_worker, 
                args=(naver_id, naver_password),
                daemon=True
            )
            login_thread.start()
            
        except Exception as e:
            self.log_message(f"로그인 시작 중 오류: {str(e)}")
            self.is_running = False
            self.start_button.config(text="자동화 시작")
    
    def _login_worker(self, naver_id, naver_password):
        """로그인 작업 스레드"""
        try:
            # 네이버 로그인 객체 생성 및 실행 (직접 타이핑 방식 우선)
            self.naver_login = NaverLogin()
            success = self.naver_login.login(naver_id, naver_password, use_clipboard=False)
            
            # GUI 업데이트는 메인 스레드에서 실행
            self.root.after(0, self._login_completed, success, self.naver_login)
                
        except Exception as e:
            # GUI 업데이트는 메인 스레드에서 실행
            self.root.after(0, self._login_error, str(e))
    
    def _login_completed(self, success, naver_login):
        """로그인 완료 처리 (메인 스레드에서 실행)"""
        if success:
            self.log_message("네이버 로그인이 완료되었습니다.")
            
            # 키워드 검색 시작
            keyword = self.config_manager.get('search_keyword', '')
            loading_method = self.config_manager.get('loading_method', 'keyword')
            
            if loading_method == "keyword" and keyword:
                self.log_message(f"블로그 검색을 시작합니다. 키워드: {keyword}")
                
                # 별도 스레드에서 블로그 검색 실행
                search_thread = threading.Thread(
                    target=self._blog_search_worker,
                    args=(naver_login, keyword),
                    daemon=True
                )
                search_thread.start()
            else:
                self.log_message("키워드가 설정되지 않았거나 다른 수집 방식이 선택되었습니다.")
                
        else:
            self.log_message("네이버 로그인에 실패했습니다.")
            self.is_running = False
            self.start_button.config(text="자동화 시작")
    
    def _blog_search_worker(self, naver_login, keyword):
        """블로그 검색 작업 스레드"""
        try:
            success = naver_login.navigate_to_blog_search(keyword)
            self.root.after(0, self._blog_search_completed, success, keyword)
        except Exception as e:
            self.root.after(0, self._blog_search_error, str(e))
    
    def _blog_search_completed(self, success, keyword):
        """블로그 검색 완료 처리"""
        if success:
            self.log_message(f"키워드 '{keyword}' 검색이 완료되었습니다.")
        else:
            self.log_message(f"키워드 '{keyword}' 검색에 실패했습니다.")
    
    def _blog_search_error(self, error_msg):
        """블로그 검색 오류 처리"""
        self.log_message(f"블로그 검색 중 오류 발생: {error_msg}")
    
    def _login_error(self, error_msg):
        """로그인 오류 처리 (메인 스레드에서 실행)"""
        self.log_message(f"로그인 중 오류 발생: {error_msg}")
        self.is_running = False
        self.start_button.config(text="자동화 시작")

    def run(self):
        """GUI 실행"""
        self.root.mainloop()
