from automation import BlogAutomation
from utils.config_manager import ConfigManager
import sys
import os
import threading
from datetime import datetime

# PyQt5 임포트
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                 QTextEdit, QRadioButton, QGroupBox, QGridLayout,
                                 QTabWidget, QMessageBox, QProgressBar, QSpinBox,
                                 QButtonGroup)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QIcon
except ImportError:
    print("PyQt5가 설치되지 않았습니다. 다음 명령어로 설치해주세요:")
    print("pip install PyQt5")
    sys.exit(1)

# 프로젝트 루트 경로를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


class AutomationWorker(QThread):
    """자동화 작업을 별도 스레드에서 실행"""
    progress_updated = pyqtSignal(str)  # 진행 상황 업데이트
    finished = pyqtSignal(int, int)     # 완료 시 (성공 수, 전체 수)
    error_occurred = pyqtSignal(str)    # 오류 발생

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.blog_automation = None

    def run(self):
        try:
            # 설정 파일을 다시 로드하여 최신 설정 반영
            self.config_manager.config = self.config_manager.load_config()
            
            # 설정 로드
            naver_id = self.config_manager.get('naver_id', '')
            naver_password = self.config_manager.get('naver_password', '')

            if not naver_id or not naver_password:
                self.error_occurred.emit("계정 정보가 설정되지 않았습니다.")
                return

            # 1. 네이버 로그인
            self.progress_updated.emit("네이버 로그인 중...")
            self.blog_automation = BlogAutomation()
            success = self.blog_automation.login(
                naver_id, naver_password, max_retries=2)

            if not success:
                self.error_occurred.emit("네이버 로그인에 실패했습니다.")
                return

            self.progress_updated.emit("✅ 네이버 로그인 성공")

            # 2. 블로그 검색
            loading_method = self.config_manager.get(
                'loading_method', 'keyword')

            if loading_method == "keyword":
                keyword = self.config_manager.get('search_keyword', '')
                if not keyword:
                    self.error_occurred.emit("검색 키워드가 설정되지 않았습니다.")
                    return

                # 설정값 가져오기
                target_count = self.config_manager.get('neighbor_collection_count', 10)
                start_page = self.config_manager.get('start_page', 1)
                
                self.progress_updated.emit(f"블로그 검색 중... (키워드: {keyword})")
                collected_blogs = self.blog_automation.search_and_collect_blogs(
                    keyword, target_count, start_page)

                if not collected_blogs:
                    self.error_occurred.emit("블로그 검색 및 수집에 실패했습니다.")
                    return

                self.progress_updated.emit(
                    f"✅ 블로그 검색 및 수집 완료: {len(collected_blogs)}개")

                # 4. 서로이웃 추가
                self.progress_updated.emit("서로이웃 추가 시작...")

                def progress_callback(current, total, blog_name):
                    self.progress_updated.emit(
                        f"[{current}/{total}] {blog_name} 처리 중...")

                success_count, total_count = self.blog_automation.process_blog_automation(
                    collected_blogs, progress_callback)
                
                # 자동화 완료 후 브라우저 정리
                if self.blog_automation:
                    self.blog_automation.cleanup_driver()
                
                self.finished.emit(success_count, total_count)

            elif loading_method == "neighbor_connect":
                # 이웃커넥트 방식
                blog_url = self.config_manager.get('base_blog_url', '')
                if not blog_url:
                    self.error_occurred.emit("블로그 URL이 설정되지 않았습니다.")
                    return

                self.progress_updated.emit(f"이웃커넥트 수집 중... (URL: {blog_url})")
                success, message, neighbor_urls = self.blog_automation.collect_neighbor_blogs(blog_url)
                
                if not success:
                    self.error_occurred.emit(f"이웃커넥트 수집 실패: {message}")
                    return

                self.progress_updated.emit(f"✅ {message}")
                
                # 이웃 URL들을 블로그 데이터 형태로 변환 (키워드 검색과 동일한 형태)
                collected_blogs = []
                blog_names = []  # 블로그 이름 리스트
                for url in neighbor_urls:
                    # URL에서 블로그 아이디 추출
                    if "blog.naver.com/" in url:
                        blog_id = url.split("blog.naver.com/")[1].rstrip('/')
                        collected_blogs.append({
                            'blog_name': blog_id,
                            'post_url': url  # 메인 블로그 URL (서로이웃 추가는 메인 블로그에서 처리됨)
                        })
                        blog_names.append(blog_id)

                if not collected_blogs:
                    self.error_occurred.emit("수집된 이웃 블로그가 없습니다.")
                    return

                # 수집된 블로그 이름들을 로그에 표시
                self.progress_updated.emit(f"📋 수집된 이웃 블로그들: {', '.join(blog_names[:10])}{'...' if len(blog_names) > 10 else ''}")
                if len(blog_names) > 10:
                    self.progress_updated.emit(f"📋 총 {len(blog_names)}개 블로그 수집 완료")

                # 4. 서로이웃 추가
                self.progress_updated.emit("서로이웃 추가 시작...")

                def progress_callback(current, total, blog_name):
                    self.progress_updated.emit(
                        f"[{current}/{total}] {blog_name} 처리 중...")

                success_count, total_count = self.blog_automation.process_blog_automation(
                    collected_blogs, progress_callback)
                
                # 자동화 완료 후 브라우저 정리
                if self.blog_automation:
                    self.blog_automation.cleanup_driver()
                
                self.finished.emit(success_count, total_count)
                
            else:
                self.error_occurred.emit("지원하지 않는 수집 방식입니다.")

        except Exception as e:
            # 오류 발생 시에도 브라우저 정리
            if self.blog_automation:
                try:
                    self.blog_automation.cleanup_driver()
                except:
                    pass
            self.error_occurred.emit(f"오류 발생: {str(e)}")


class MainWindow(QMainWindow):
    """PyQt5 기반 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.automation_worker = None
        self.is_running = False

        self.init_ui()
        # load_settings는 UI 초기화 후에 호출
        QTimer.singleShot(0, self.load_settings)

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("네이버 블로그 자동화")
        self.setGeometry(100, 100, 800, 700)  # 창 크기 줄임

        # 30px 폰트 설정
        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px
        
        # 메인 위젯 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 탭 위젯 생성
        tab_widget = QTabWidget()
        tab_widget.setFont(font_30px)

        # 탭 추가
        tab1 = self.create_account_and_search_tab()
        tab2 = self.create_settings_tab()
        tab3 = self.create_automation_tab()

        tab_widget.addTab(tab1, "1. 계정 및 검색 설정")
        tab_widget.addTab(tab2, "2. 상세 설정")
        tab_widget.addTab(tab3, "3. 자동화 실행")

        # 메인 레이아웃
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(tab_widget)

        # 하단 버튼들
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)  # 버튼 영역 상단 여백

        self.save_button = QPushButton("설정 저장")
        self.save_button.setMinimumHeight(60)
        save_font = QFont()
        save_font.setPointSize(22)  # 저장 버튼도 30px로 통일
        self.save_button.setFont(save_font)
        self.save_button.clicked.connect(self.save_settings)

        button_layout.addStretch()
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

    def create_account_and_search_tab(self):
        """계정 설정 및 검색 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px

        # 계정 정보 그룹
        account_group = QGroupBox("계정 정보")
        account_group.setFont(font_30px)
        account_layout = QGridLayout(account_group)

        id_label = QLabel("네이버 ID:")
        id_label.setFont(font_30px)
        account_layout.addWidget(id_label, 0, 0)
        self.id_edit = QLineEdit()
        self.id_edit.setFont(font_30px)
        account_layout.addWidget(self.id_edit, 0, 1)

        pwd_label = QLabel("비밀번호:")
        pwd_label.setFont(font_30px)
        account_layout.addWidget(pwd_label, 1, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setFont(font_30px)
        self.password_edit.setEchoMode(QLineEdit.Password)
        account_layout.addWidget(self.password_edit, 1, 1)

        layout.setContentsMargins(15, 15, 15, 15)  # 탭 내부 여백
        layout.setSpacing(20)  # 그룹간 간격
        
        layout.addWidget(account_group)

        # 수집 방식 그룹
        method_group = QGroupBox("수집 방식")
        method_group.setFont(font_30px)
        method_layout = QVBoxLayout(method_group)

        self.method_group = QButtonGroup()

        self.keyword_radio = QRadioButton("키워드 검색")
        self.keyword_radio.setFont(font_30px)
        self.keyword_radio.setChecked(True)
        self.keyword_radio.toggled.connect(self.on_method_changed)
        self.method_group.addButton(self.keyword_radio, 0)
        method_layout.addWidget(self.keyword_radio)

        self.connect_radio = QRadioButton("이웃 커넥트")
        self.connect_radio.setFont(font_30px)
        self.connect_radio.toggled.connect(self.on_method_changed)
        self.method_group.addButton(self.connect_radio, 1)
        method_layout.addWidget(self.connect_radio)

        layout.addWidget(method_group)

        # 키워드 검색 그룹
        self.keyword_group = QGroupBox("키워드 검색 설정")
        self.keyword_group.setFont(font_30px)
        keyword_layout = QGridLayout(self.keyword_group)
        keyword_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백
        keyword_layout.setSpacing(15)  # 그룹 내 요소간 간격

        keyword_label = QLabel("검색 키워드:")
        keyword_label.setFont(font_30px)
        keyword_layout.addWidget(keyword_label, 0, 0)
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setFont(font_30px)
        self.keyword_edit.setMinimumHeight(50)  # 입력창 높이 증가
        keyword_layout.addWidget(self.keyword_edit, 0, 1)

        count_label = QLabel("수집 개수:")
        count_label.setFont(font_30px)
        keyword_layout.addWidget(count_label, 1, 0)
        self.collection_count_spin = QSpinBox()
        self.collection_count_spin.setFont(font_30px)
        self.collection_count_spin.setMinimumHeight(50)  # 스핀박스 높이 증가
        self.collection_count_spin.setRange(1, 1000)
        self.collection_count_spin.setValue(10)
        keyword_layout.addWidget(self.collection_count_spin, 1, 1)

        page_label = QLabel("시작 페이지:")
        page_label.setFont(font_30px)
        keyword_layout.addWidget(page_label, 2, 0)
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setFont(font_30px)
        self.start_page_spin.setMinimumHeight(50)  # 스핀박스 높이 증가
        self.start_page_spin.setRange(1, 100)
        self.start_page_spin.setValue(1)
        keyword_layout.addWidget(self.start_page_spin, 2, 1)

        layout.addWidget(self.keyword_group)

        # 이웃 커넥트 그룹
        self.connect_group = QGroupBox("이웃 커넥트 설정")
        self.connect_group.setFont(font_30px)
        connect_layout = QGridLayout(self.connect_group)
        connect_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백
        connect_layout.setSpacing(15)  # 그룹 내 요소간 간격

        blog_label = QLabel("기준 블로그 URL:")
        blog_label.setFont(font_30px)
        connect_layout.addWidget(blog_label, 0, 0)
        self.base_blog_edit = QLineEdit()
        self.base_blog_edit.setFont(font_30px)
        self.base_blog_edit.setMinimumHeight(50)  # 입력창 높이 증가
        connect_layout.addWidget(self.base_blog_edit, 0, 1)

        neighbor_label = QLabel("이웃 개수:")
        neighbor_label.setFont(font_30px)
        connect_layout.addWidget(neighbor_label, 1, 0)
        self.neighbor_count_spin = QSpinBox()
        self.neighbor_count_spin.setFont(font_30px)
        self.neighbor_count_spin.setMinimumHeight(50)  # 스핀박스 높이 증가
        self.neighbor_count_spin.setRange(1, 1000)
        self.neighbor_count_spin.setValue(20)
        connect_layout.addWidget(self.neighbor_count_spin, 1, 1)

        layout.addWidget(self.connect_group)
        
        # 초기 상태 설정 (키워드 검색이 기본)
        self.connect_group.setVisible(False)
        
        layout.addStretch()
        return tab

    def on_method_changed(self):
        """수집 방식 변경 이벤트 처리"""
        if self.keyword_radio.isChecked():
            self.keyword_group.setVisible(True)
            self.connect_group.setVisible(False)
        else:
            self.keyword_group.setVisible(False)
            self.connect_group.setVisible(True)

    def create_settings_tab(self):
        """상세 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)  # 탭 내부 여백
        layout.setSpacing(20)  # 그룹간 간격

        # 서로이웃 메시지 그룹
        message_group = QGroupBox("서로이웃 메시지")
        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px
        message_group.setFont(font_30px)
        message_layout = QVBoxLayout(message_group)
        message_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백
        message_layout.setSpacing(10)  # 그룹 내 요소간 간격

        msg_label = QLabel("메시지 ({nickname} 변수 사용 가능):")
        msg_label.setFont(font_30px)
        message_layout.addWidget(msg_label)
        self.neighbor_message_edit = QTextEdit()
        self.neighbor_message_edit.setFont(font_30px)
        self.neighbor_message_edit.setMaximumHeight(80)
        self.neighbor_message_edit.setText("안녕하세요! {nickname}님 서로이웃 해요!")
        message_layout.addWidget(self.neighbor_message_edit)

        layout.addWidget(message_group)

        # 댓글 옵션 그룹
        comment_group = QGroupBox("댓글 옵션")
        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px
        comment_group.setFont(font_30px)
        comment_layout = QVBoxLayout(comment_group)
        comment_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백
        comment_layout.setSpacing(10)  # 그룹 내 요소간 간격

        self.comment_group = QButtonGroup()

        self.ai_radio = QRadioButton("AI 댓글")
        self.ai_radio.setFont(font_30px)
        self.ai_radio.setChecked(True)
        self.comment_group.addButton(self.ai_radio, 0)
        comment_layout.addWidget(self.ai_radio)

        self.random_radio = QRadioButton("랜덤 멘트")
        self.random_radio.setFont(font_30px)
        self.comment_group.addButton(self.random_radio, 1)
        comment_layout.addWidget(self.random_radio)

        self.none_radio = QRadioButton("작성 안함")
        self.none_radio.setFont(font_30px)
        self.comment_group.addButton(self.none_radio, 2)
        comment_layout.addWidget(self.none_radio)

        # 랜덤 댓글 입력창
        random_label = QLabel("랜덤 댓글 목록 ({nickname} 사용 가능):")
        random_label.setFont(font_30px)
        comment_layout.addWidget(random_label)
        self.random_comments_edit = QTextEdit()
        self.random_comments_edit.setFont(font_30px)
        self.random_comments_edit.setMaximumHeight(120)
        default_comments = [
            "좋은 글 잘 읽었어요! {nickname}님",
            "유익한 정보 감사해요~ {nickname}님!",
            "정말 도움이 되는 글이네요 {nickname}님 ㅎㅎ",
            "오늘도 좋은 하루 되세요 {nickname}님!",
            "항상 좋은 글 감사드려요 {nickname}님^^"
        ]
        self.random_comments_edit.setText('\n'.join(default_comments))
        comment_layout.addWidget(self.random_comments_edit)

        layout.addWidget(comment_group)

        # 체류 시간 그룹
        wait_group = QGroupBox("체류 시간")
        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px
        wait_group.setFont(font_30px)
        wait_layout = QHBoxLayout(wait_group)
        wait_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백
        wait_layout.setSpacing(15)  # 그룹 내 요소간 간격

        wait_label = QLabel("기본 10초 + 추가 시간:")
        wait_label.setFont(font_30px)
        wait_layout.addWidget(wait_label)
        self.wait_time_spin = QSpinBox()
        self.wait_time_spin.setFont(font_30px)
        self.wait_time_spin.setMinimumHeight(50)  # 스핀박스 높이 증가
        self.wait_time_spin.setRange(0, 300)
        self.wait_time_spin.setValue(0)
        self.wait_time_spin.setSuffix("초")
        wait_layout.addWidget(self.wait_time_spin)
        wait_layout.addStretch()

        layout.addWidget(wait_group)
        layout.addStretch()

        return tab

    def create_automation_tab(self):
        """자동화 실행 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)  # 탭 내부 여백
        layout.setSpacing(20)  # 그룹간 간격

        # 현재 설정 표시 그룹
        status_group = QGroupBox("현재 설정")
        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px
        status_group.setFont(font_30px)
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백

        self.status_label = QLabel("설정을 확인하세요.")
        self.status_label.setFont(font_30px)
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_group)

        # 실행 컨트롤 그룹
        control_group = QGroupBox("실행 제어")
        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px
        control_group.setFont(font_30px)
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백
        control_layout.setSpacing(15)  # 그룹 내 요소간 간격

        self.start_button = QPushButton("자동화 시작")
        self.start_button.setMinimumHeight(80)
        button_font = QFont()
        button_font.setPointSize(22)  # 버튼도 30px로 통일
        button_font.setBold(True)
        self.start_button.setFont(button_font)
        self.start_button.clicked.connect(self.toggle_automation)
        control_layout.addWidget(self.start_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(font_30px)
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        layout.addWidget(control_group)

        # 로그 그룹
        log_group = QGroupBox("실행 로그")
        font_30px = QFont()
        font_30px.setPointSize(22)  # 22pt ≈ 30px
        log_group.setFont(font_30px)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(20, 20, 20, 20)  # 그룹 내부 여백

        self.log_text = QTextEdit()
        self.log_text.setFont(font_30px)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return tab

    def load_settings(self):
        """설정 불러오기"""
        try:
            # 계정 정보
            self.id_edit.setText(self.config_manager.get('naver_id', ''))
            self.password_edit.setText(
                self.config_manager.get('naver_password', ''))

            # 수집 방식
            method = self.config_manager.get('loading_method', 'keyword')
            if method == 'keyword':
                self.keyword_radio.setChecked(True)
            else:
                self.connect_radio.setChecked(True)

            # 검색 설정
            self.keyword_edit.setText(
                self.config_manager.get('search_keyword', ''))
            self.collection_count_spin.setValue(
                self.config_manager.get('neighbor_collection_count', 10))
            self.start_page_spin.setValue(
                self.config_manager.get('start_page', 1))

            self.base_blog_edit.setText(
                self.config_manager.get('base_blog_url', ''))
            self.neighbor_count_spin.setValue(
                self.config_manager.get('neighbor_count', 20))
            
            # 방식에 따라 해당 그룹 표시
            self.on_method_changed()

            # 상세 설정
            self.neighbor_message_edit.setText(self.config_manager.get(
                'neighbor_message', '안녕하세요! {nickname}님 서로이웃 해요!'))

            comment_option = self.config_manager.get('comment_option', 'ai')
            if comment_option == 'ai':
                self.ai_radio.setChecked(True)
            elif comment_option == 'random':
                self.random_radio.setChecked(True)
            else:
                self.none_radio.setChecked(True)

            random_comments = self.config_manager.get('random_comments', [])
            if random_comments:
                self.random_comments_edit.setText('\n'.join(random_comments))

            self.wait_time_spin.setValue(
                self.config_manager.get('wait_time', 0))

            self.update_status()

        except Exception as e:
            self.log_message(f"설정 로드 중 오류: {str(e)}")

    def save_settings(self):
        """설정 저장"""
        try:
            # 계정 정보
            self.config_manager.set('naver_id', self.id_edit.text().strip())
            self.config_manager.set(
                'naver_password', self.password_edit.text().strip())

            # 수집 방식
            method = 'keyword' if self.keyword_radio.isChecked() else 'neighbor_connect'
            self.config_manager.set('loading_method', method)

            # 검색 설정
            self.config_manager.set(
                'search_keyword', self.keyword_edit.text().strip())
            self.config_manager.set(
                'neighbor_collection_count', self.collection_count_spin.value())
            self.config_manager.set('start_page', self.start_page_spin.value())

            self.config_manager.set(
                'base_blog_url', self.base_blog_edit.text().strip())
            self.config_manager.set(
                'neighbor_count', self.neighbor_count_spin.value())

            # 상세 설정
            self.config_manager.set(
                'neighbor_message', self.neighbor_message_edit.toPlainText().strip())

            if self.ai_radio.isChecked():
                comment_option = 'ai'
            elif self.random_radio.isChecked():
                comment_option = 'random'
            else:
                comment_option = 'none'
            self.config_manager.set('comment_option', comment_option)

            # 랜덤 댓글
            random_comments_text = self.random_comments_edit.toPlainText().strip()
            random_comments = [
                line.strip() for line in random_comments_text.split('\n') if line.strip()]
            self.config_manager.set('random_comments', random_comments)

            self.config_manager.set('wait_time', self.wait_time_spin.value())

            # 설정 저장
            if self.config_manager.save_config():
                QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
                self.update_status()
            else:
                QMessageBox.warning(self, "저장 실패", "설정 저장에 실패했습니다.")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 중 오류가 발생했습니다: {str(e)}")

    def save_current_settings(self):
        """현재 UI의 설정을 저장 (자동화 시작 시 호출)"""
        # 계정 정보
        self.config_manager.set('naver_id', self.id_edit.text().strip())
        self.config_manager.set('naver_password', self.password_edit.text().strip())

        # 수집 방식
        method = 'keyword' if self.keyword_radio.isChecked() else 'neighbor_connect'
        self.config_manager.set('loading_method', method)

        # 검색 설정
        self.config_manager.set('search_keyword', self.keyword_edit.text().strip())
        self.config_manager.set('neighbor_collection_count', self.collection_count_spin.value())
        self.config_manager.set('start_page', self.start_page_spin.value())

        self.config_manager.set('base_blog_url', self.base_blog_edit.text().strip())
        self.config_manager.set('neighbor_count', self.neighbor_count_spin.value())

        # 상세 설정
        self.config_manager.set('neighbor_message', self.neighbor_message_edit.toPlainText().strip())

        if self.ai_radio.isChecked():
            comment_option = 'ai'
        elif self.random_radio.isChecked():
            comment_option = 'random'
        else:
            comment_option = 'none'
        self.config_manager.set('comment_option', comment_option)

        # 랜덤 댓글
        random_comments_text = self.random_comments_edit.toPlainText().strip()
        random_comments = [line.strip() for line in random_comments_text.split('\n') if line.strip()]
        self.config_manager.set('random_comments', random_comments)

        self.config_manager.set('wait_time', self.wait_time_spin.value())

        # 설정 저장
        if not self.config_manager.save_config():
            raise Exception("설정 파일 저장에 실패했습니다.")
        
        # 상태 업데이트
        self.update_status()

    def update_status(self):
        """현재 설정 상태 업데이트"""
        naver_id = self.config_manager.get('naver_id', '')
        method = self.config_manager.get('loading_method', 'keyword')
        keyword = self.config_manager.get('search_keyword', '')

        status_text = f"네이버 ID: {naver_id if naver_id else '미설정'}\n"
        status_text += f"수집 방식: {'키워드 검색' if method == 'keyword' else '이웃 커넥트'}\n"

        if method == 'keyword':
            status_text += f"검색 키워드: {keyword if keyword else '미설정'}\n"
            status_text += f"수집 개수: {self.config_manager.get('neighbor_collection_count', 10)}개"
        else:
            base_url = self.config_manager.get('base_blog_url', '')
            status_text += f"기준 블로그: {base_url if base_url else '미설정'}\n"
            status_text += f"이웃 개수: {self.config_manager.get('neighbor_count', 20)}개"

        self.status_label.setText(status_text)

    def toggle_automation(self):
        """자동화 시작/중지"""
        if not self.is_running:
            # 자동화 시작 전에 현재 설정을 자동으로 저장
            try:
                self.save_current_settings()
                self.log_message("✅ 설정 자동 저장 완료")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"설정 저장 중 오류가 발생했습니다: {str(e)}")
                return
            
            # 필수 설정 확인 (UI 값 기준으로)
            naver_id = self.id_edit.text().strip()
            naver_password = self.password_edit.text().strip()
            
            if not naver_id or not naver_password:
                QMessageBox.warning(self, "설정 부족", "네이버 계정 정보를 먼저 설정해주세요.")
                return

            # 수집 방식에 따른 필수 값 확인
            if self.keyword_radio.isChecked():
                keyword = self.keyword_edit.text().strip()
                if not keyword:
                    QMessageBox.warning(self, "설정 부족", "검색 키워드를 먼저 설정해주세요.")
                    return
            else:
                base_blog = self.base_blog_edit.text().strip()
                if not base_blog:
                    QMessageBox.warning(self, "설정 부족", "기준 블로그 URL을 먼저 설정해주세요.")
                    return

            # 자동화 시작
            self.is_running = True
            self.start_button.setText("자동화 중지")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 무한 진행바

            self.log_message("=== 자동화 시작 ===")

            # 워커 스레드 시작
            self.automation_worker = AutomationWorker(self.config_manager)
            self.automation_worker.progress_updated.connect(self.log_message)
            self.automation_worker.finished.connect(
                self.on_automation_finished)
            self.automation_worker.error_occurred.connect(
                self.on_automation_error)
            self.automation_worker.start()

        else:
            # 자동화 중지
            self.stop_automation()

    def stop_automation(self):
        """자동화 중지"""
        self.is_running = False
        self.start_button.setText("자동화 시작")
        self.progress_bar.setVisible(False)

        if self.automation_worker and self.automation_worker.isRunning():
            # 워커 스레드의 브라우저도 정리
            if hasattr(self.automation_worker, 'naver_login') and self.automation_worker.naver_login:
                try:
                    self.automation_worker.naver_login.cleanup_driver()
                except:
                    pass
            
            self.automation_worker.terminate()
            self.automation_worker.wait()

        self.log_message("=== 자동화 중지 ===")

    def on_automation_finished(self, success_count, total_count):
        """자동화 완료 처리"""
        self.stop_automation()

        success_rate = (success_count / total_count *
                        100) if total_count > 0 else 0

        self.log_message("=== 자동화 완료 ===")
        self.log_message(f"📊 결과: {success_count}/{total_count} 성공")
        self.log_message(f"📈 성공률: {success_rate:.1f}%")

        QMessageBox.information(self, "완료",
                                f"자동화가 완료되었습니다!\n\n"
                                f"성공: {success_count}/{total_count}\n"
                                f"성공률: {success_rate:.1f}%")

    def on_automation_error(self, error_msg):
        """자동화 오류 처리"""
        self.stop_automation()
        self.log_message(f"❌ 오류: {error_msg}")
        QMessageBox.critical(self, "오류", error_msg)

    def log_message(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"

        self.log_text.append(formatted_message)

        # 자동 스크롤
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


if __name__ == "__main__":

    # 그래도 실행하고 싶다면
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        print("대신 'python run_gui.py'를 사용해보세요.")
