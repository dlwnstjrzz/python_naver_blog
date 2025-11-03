from gui.extracted_ids_window import ExtractedIdsWindow
from automation import BlogAutomation
from utils.config_manager import ConfigManager
import sys
import os
import threading
from datetime import datetime

# PyQt5 임포트
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QRadioButton, QGroupBox, QGridLayout,
                             QTabWidget, QMessageBox, QProgressBar, QSpinBox,
                             QButtonGroup, QCheckBox, QInputDialog, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

# 프로젝트 루트 경로를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# 추출된 ID 관리 창 import


class AutomationWorker(QThread):
    """자동화 작업을 별도 스레드에서 실행"""
    progress_updated = pyqtSignal(str)  # 진행 상황 업데이트
    finished = pyqtSignal(int, int)     # 완료 시 (성공 수, 전체 수)
    error_occurred = pyqtSignal(str)    # 오류 발생
    cleanup_done = pyqtSignal()         # 드라이버 정리 완료

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.blog_automation = None

    def run(self):
        added_count = 0
        total_found = 0
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
                target_count = self.config_manager.get(
                    'neighbor_collection_count')
                start_page = self.config_manager.get('start_page', 1)

                if target_count is None:
                    self.error_occurred.emit(
                        "수집 개수가 설정되지 않았습니다. 키워드 검색 탭에서 수집 개수를 설정해주세요.")
                    return

                self.progress_updated.emit(f"블로그 검색 중... (키워드: {keyword})")
                collected_blogs = self.blog_automation.search_and_collect_blogs(
                    keyword, target_count, start_page)

                if not collected_blogs:
                    self.error_occurred.emit("블로그 검색 및 수집에 실패했습니다.")
                    return

                blog_ids = [blog.get('blog_name') for blog in collected_blogs if blog.get('blog_name')]
                total_found = len(blog_ids)

                if total_found == 0:
                    self.progress_updated.emit("⚠️ 새로운 블로그 아이디를 찾지 못했습니다.")
                    added_count = 0
                else:
                    added_count = self.blog_automation.extracted_ids_manager.add_extracted_ids(
                        blog_ids, status="대기")
                    duplicates = total_found - added_count
                    self.progress_updated.emit(
                        f"✅ 아이디 추출 완료: 총 {total_found}개 (신규 {added_count}개, 기존 {duplicates}개)")

                self.finished.emit(added_count, total_found)

            elif loading_method == "neighbor_connect":
                # 이웃커넥트 방식
                blog_url = self.config_manager.get('base_blog_url', '')
                if not blog_url:
                    self.error_occurred.emit("블로그 URL이 설정되지 않았습니다.")
                    return

                self.progress_updated.emit(f"이웃커넥트 수집 중... (URL: {blog_url})")
                success, message, neighbor_urls = self.blog_automation.collect_neighbor_blogs(
                    blog_url)

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
                            # 메인 블로그 URL (서로이웃 추가는 메인 블로그에서 처리됨)
                            'post_url': url
                        })
                        blog_names.append(blog_id)

                if not collected_blogs:
                    self.error_occurred.emit("수집된 이웃 블로그가 없습니다.")
                    return

                # 수집된 블로그 이름들을 로그에 표시
                self.progress_updated.emit(
                    f"📋 수집된 이웃 블로그들: {', '.join(blog_names[:10])}{'...' if len(blog_names) > 10 else ''}")
                if len(blog_names) > 10:
                    self.progress_updated.emit(
                        f"📋 총 {len(blog_names)}개 블로그 수집 완료")

                blog_ids = [data.get('blog_name') for data in collected_blogs if data.get('blog_name')]
                total_found = len(blog_ids)

                if total_found == 0:
                    self.progress_updated.emit("⚠️ 새로운 블로그 아이디를 찾지 못했습니다.")
                    added_count = 0
                else:
                    added_count = self.blog_automation.extracted_ids_manager.add_extracted_ids(
                        blog_ids, status="대기")
                    duplicates = total_found - added_count
                    self.progress_updated.emit(
                        f"✅ 아이디 추출 완료: 총 {total_found}개 (신규 {added_count}개, 기존 {duplicates}개)")

                self.finished.emit(added_count, total_found)

            else:
                self.error_occurred.emit("지원하지 않는 수집 방식입니다.")

        except Exception as e:
            self.error_occurred.emit(f"오류 발생: {str(e)}")
        finally:
            if self.blog_automation:
                try:
                    self.blog_automation.cleanup_driver()
                except:
                    pass
            self.cleanup_done.emit()


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

        # 창 크기를 유연하게 설정 (DPI 스케일링 적용됨)
        self.setMinimumSize(550, 620)  # 최소 크기 설정
        self.resize(650, 700)  # 초기 크기 (DPI에 따라 자동 스케일링됨)

        # 화면 중앙에 위치시키기
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(int((screen.width() - size.width()) / 2),
                  int((screen.height() - size.height()) / 2))

        # 윈도우 아이콘 설정
        try:
            import os
            import sys
            from PyQt5.QtGui import QIcon

            # PyInstaller 실행 파일에서의 경로 처리
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))

            # ICO 파일을 우선 시도, 없으면 PNG 사용
            ico_path = os.path.join(base_path, "image", "logo.ico")
            if os.path.exists(ico_path):
                self.setWindowIcon(QIcon(ico_path))
        except:
            pass

        # 메인 컬러 스킴 설정
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
                color: white;
            }
            QTabWidget {
                background-color: #1a1a1a;
                color: white;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #333;
                color: white;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #fe4847;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #555;
            }
            QGroupBox {
                color: white;
                border: 2px solid #333;
                border-radius: 5px;
                margin: 10px 0px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0px 5px 0px 5px;
                color: #fe4847;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 2px solid #fe4847;
            }
            QSpinBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QSpinBox:focus {
                border: 2px solid #fe4847;
            }
            QTextEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QTextEdit:focus {
                border: 2px solid #fe4847;
            }
            QRadioButton {
                color: white;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 13px;
                height: 13px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #555;
                border-radius: 7px;
                background-color: #333;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #fe4847;
                border-radius: 7px;
                background-color: #fe4847;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #555;
                border-radius: 2px;
                background-color: #333;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #fe4847;
                border-radius: 2px;
                background-color: #fe4847;
            }
            QPushButton {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
                border: 1px solid #777;
            }
            QPushButton:pressed {
                background-color: #222;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                color: white;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #fe4847;
                border-radius: 2px;
            }
            QMessageBox {
                background-color: #1a1a1a;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                background-color: transparent;
            }
            QMessageBox QPushButton {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #555;
                border: 1px solid #777;
            }
            QMessageBox QPushButton:pressed {
                background-color: #222;
            }
            QInputDialog {
                background-color: #1a1a1a;
                color: white;
            }
            QInputDialog QLabel {
                color: white;
            }
            QInputDialog QSpinBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QInputDialog QSpinBox:focus {
                border: 2px solid #fe4847;
            }
            QInputDialog QPushButton {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 60px;
            }
            QInputDialog QPushButton:hover {
                background-color: #555;
                border: 1px solid #777;
            }
            QInputDialog QPushButton:pressed {
                background-color: #222;
            }
            QProgressDialog {
                background-color: #1a1a1a;
                color: white;
            }
            QProgressDialog QLabel {
                color: white;
            }
            QProgressDialog QPushButton {
                background-color: #fe4847;
                color: white;
                border: 1px solid #fe4847;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 60px;
            }
            QProgressDialog QPushButton:hover {
                background-color: #e63946;
                border: 1px solid #e63946;
            }
            QProgressDialog QPushButton:pressed {
                background-color: #d62828;
            }
            QProgressDialog QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                color: white;
                background-color: #333;
            }
            QProgressDialog QProgressBar::chunk {
                background-color: #fe4847;
                border-radius: 2px;
            }
        """)

        # 기본 폰트 설정 (크기 축소)
        font_default = QFont()
        font_default.setPointSize(10)  # 기본 폰트 크기 줄임

        # 메인 위젯 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 로고 섹션 생성
        logo_layout = QHBoxLayout()

        # 로고 이미지
        logo_label = QLabel()

        try:
            from PyQt5.QtGui import QPixmap

            # PyInstaller 실행 파일에서의 경로 처리
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))

            # 로고 파일 경로
            logo_path = os.path.join(base_path, "image", "logo.ico")
            print(f"DEBUG: logo_path = {logo_path}")
            print(f"DEBUG: logo file exists = {os.path.exists(logo_path)}")

            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                print(f"DEBUG: pixmap.isNull() = {pixmap.isNull()}")
                if not pixmap.isNull():
                    # 로고 크기 조절 (50x50)
                    scaled_pixmap = pixmap.scaled(
                        50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    logo_label.setPixmap(scaled_pixmap)
                    print("DEBUG: 로고 이미지 로드 성공")
                else:
                    print("DEBUG: pixmap이 null입니다")
                    logo_label.setText("로고")
                    logo_label.setStyleSheet(
                        "color: #fe4847; font-size: 16px; font-weight: bold;")
            else:
                print("DEBUG: 로고 파일이 존재하지 않습니다")
                logo_label.setText("로고")
                logo_label.setStyleSheet(
                    "color: #fe4847; font-size: 16px; font-weight: bold;")

        except Exception:
            logo_label.setText("로고")
            logo_label.setStyleSheet(
                "color: #fe4847; font-size: 16px; font-weight: bold;")

        # 슬로건 이미지 레이블
        slogan_label = QLabel()

        try:
            from PyQt5.QtGui import QPixmap

            # PyInstaller 실행 파일에서의 경로 처리
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))

            slogan_path = os.path.join(base_path, "image", "slogan.png")

            if os.path.exists(slogan_path):
                pixmap = QPixmap(slogan_path)
                if not pixmap.isNull():
                    # 슬로건 이미지 크기 조절
                    scaled_pixmap = pixmap.scaled(
                        400, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    slogan_label.setPixmap(scaled_pixmap)
                else:
                    # 이미지 로드 실패시 텍스트로 대체
                    slogan_label.setText("자동화로 시간을 지배하라")
                    slogan_label.setStyleSheet("""
                        color: white;
                        font-size: 20px;
                        font-weight: bold;
                        margin-left: 12px;
                    """)
            else:
                # 이미지 파일이 없으면 텍스트로 대체
                slogan_label.setText("자동화로 시간을 지배하라")
                slogan_label.setStyleSheet("""
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    margin-left: 12px;
                """)
        except Exception:
            # 오류 발생시 텍스트로 대체
            slogan_label.setText("자동화로 시간을 지배하라")
            slogan_label.setStyleSheet("""
                color: white;
                font-size: 20px;
                font-weight: bold;
                margin-left: 12px;
            """)

        logo_layout.addStretch()  # 왼쪽 공간 채우기
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(slogan_label)
        logo_layout.addStretch()  # 오른쪽 공간 채우기

        # 탭 위젯 생성
        tab_widget = QTabWidget()
        tab_widget.setFont(font_default)

        # 탭 추가
        tab1 = self.create_account_and_search_tab()
        tab2 = self.create_settings_tab()
        tab3 = self.create_automation_tab()

        tab_widget.addTab(tab1, "1. 진짜 되냐?")
        tab_widget.addTab(tab2, "2. 상세 설정")
        tab_widget.addTab(tab3, "3. 자동화 실행")

        # 메인 레이아웃
        main_layout = QVBoxLayout(main_widget)
        main_layout.addLayout(logo_layout)
        main_layout.addSpacing(10)  # 로고와 탭 사이 간격
        main_layout.addWidget(tab_widget)

        # 하단 버튼들
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)  # 버튼 영역 상단 여백

        self.save_button = QPushButton("설정 저장")
        self.save_button.setMinimumHeight(32)
        save_font = QFont()
        save_font.setPointSize(10)  # 버튼 폰트 크기 줄임
        self.save_button.setFont(save_font)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #fe4847;
                color: white;
                border: 1px solid #fe4847;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e63946;
                border: 1px solid #e63946;
            }
            QPushButton:pressed {
                background-color: #d62828;
            }
        """)
        self.save_button.clicked.connect(self.save_settings)

        # 서이추 신청 자동 취소 버튼 추가
        self.auto_cancel_btn = QPushButton("서이추 신청 자동 취소")
        self.auto_cancel_btn.setMinimumHeight(32)
        self.auto_cancel_btn.setFont(save_font)
        self.auto_cancel_btn.clicked.connect(self.start_auto_cancel)
        self.auto_cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #fe4847;
                color: white;
                border: 1px solid #fe4847;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e63946;
                border: 1px solid #e63946;
            }
            QPushButton:pressed {
                background-color: #d62828;
            }
        """)

        button_layout.addStretch()
        button_layout.addWidget(self.auto_cancel_btn)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

    def create_account_and_search_tab(self):
        """계정 설정 및 검색 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        font_default = QFont()
        font_default.setPointSize(10)  # 기본 폰트 크기

        # 계정 정보 그룹
        account_group = QGroupBox("계정 정보")
        account_group.setFont(font_default)
        account_layout = QGridLayout(account_group)

        id_label = QLabel("네이버 ID:")
        id_label.setFont(font_default)
        account_layout.addWidget(id_label, 0, 0)
        self.id_edit = QLineEdit()
        self.id_edit.setFont(font_default)
        account_layout.addWidget(self.id_edit, 0, 1)

        pwd_label = QLabel("비밀번호:")
        pwd_label.setFont(font_default)
        account_layout.addWidget(pwd_label, 1, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setFont(font_default)
        self.password_edit.setEchoMode(QLineEdit.Password)
        account_layout.addWidget(self.password_edit, 1, 1)

        layout.setContentsMargins(10, 10, 10, 10)  # 탭 내부 여백 줄임
        layout.setSpacing(10)  # 그룹간 간격 줄임

        layout.addWidget(account_group)

        # 수집 방식 그룹
        method_group = QGroupBox("수집 방식")
        method_group.setFont(font_default)
        method_layout = QVBoxLayout(method_group)

        self.method_group = QButtonGroup()

        self.keyword_radio = QRadioButton("키워드 검색")
        self.keyword_radio.setFont(font_default)
        self.keyword_radio.setChecked(True)
        self.keyword_radio.toggled.connect(self.on_method_changed)
        self.method_group.addButton(self.keyword_radio, 0)
        method_layout.addWidget(self.keyword_radio)

        self.connect_radio = QRadioButton("이웃 커넥트")
        self.connect_radio.setFont(font_default)
        self.connect_radio.toggled.connect(self.on_method_changed)
        self.method_group.addButton(self.connect_radio, 1)
        method_layout.addWidget(self.connect_radio)

        layout.addWidget(method_group)

        # 키워드 검색 그룹
        self.keyword_group = QGroupBox("키워드 검색 설정")
        self.keyword_group.setFont(font_default)
        keyword_layout = QGridLayout(self.keyword_group)
        keyword_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내부 여백 줄임
        keyword_layout.setSpacing(10)  # 그룹 내 요소간 간격 줄임

        keyword_label = QLabel("검색 키워드:")
        keyword_label.setFont(font_default)
        keyword_layout.addWidget(keyword_label, 0, 0)
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setFont(font_default)
        self.keyword_edit.setMinimumHeight(30)  # 입력창 높이 줄임
        keyword_layout.addWidget(self.keyword_edit, 0, 1)

        count_label = QLabel("수집 개수:")
        count_label.setFont(font_default)
        keyword_layout.addWidget(count_label, 1, 0)
        self.collection_count_spin = QSpinBox()
        self.collection_count_spin.setFont(font_default)
        self.collection_count_spin.setMinimumHeight(30)  # 스핀박스 높이 줄임
        self.collection_count_spin.setRange(1, 1000)
        self.collection_count_spin.setValue(10)
        keyword_layout.addWidget(self.collection_count_spin, 1, 1)

        page_label = QLabel("시작 페이지:")
        page_label.setFont(font_default)
        keyword_layout.addWidget(page_label, 2, 0)
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setFont(font_default)
        self.start_page_spin.setMinimumHeight(30)  # 스핀박스 높이 줄임
        self.start_page_spin.setRange(1, 100)
        self.start_page_spin.setValue(1)
        keyword_layout.addWidget(self.start_page_spin, 2, 1)

        layout.addWidget(self.keyword_group)

        # 이웃 커넥트 그룹
        self.connect_group = QGroupBox("이웃 커넥트 설정")
        self.connect_group.setFont(font_default)
        connect_layout = QGridLayout(self.connect_group)
        connect_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내부 여백 줄임
        connect_layout.setSpacing(10)  # 그룹 내 요소간 간격 줄임

        blog_label = QLabel("기준 블로그 URL:")
        blog_label.setFont(font_default)
        connect_layout.addWidget(blog_label, 0, 0)
        self.base_blog_edit = QLineEdit()
        self.base_blog_edit.setFont(font_default)
        self.base_blog_edit.setMinimumHeight(30)  # 입력창 높이 줄임
        connect_layout.addWidget(self.base_blog_edit, 0, 1)

        neighbor_label = QLabel("이웃 개수:")
        neighbor_label.setFont(font_default)
        connect_layout.addWidget(neighbor_label, 1, 0)
        self.neighbor_count_spin = QSpinBox()
        self.neighbor_count_spin.setFont(font_default)
        self.neighbor_count_spin.setMinimumHeight(30)  # 스핀박스 높이 줄임
        self.neighbor_count_spin.setRange(1, 1000)
        self.neighbor_count_spin.setValue(10)
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
        layout.setContentsMargins(10, 10, 10, 10)  # 탭 내부 여백 줄임
        layout.setSpacing(10)  # 그룹간 간격 줄임

        # 서로이웃 메시지 그룹
        message_group = QGroupBox("서로이웃 메시지")
        font_default = QFont()
        font_default.setPointSize(10)  # 기본 폰트 크기
        message_group.setFont(font_default)
        message_layout = QVBoxLayout(message_group)
        message_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내부 여백 줄임
        message_layout.setSpacing(4)  # 그룹 내 요소간 간격 더 줄임

        msg_label = QLabel("{nickname} = 추가하는 이웃의 닉네임")
        msg_label.setFont(font_default)
        message_layout.addWidget(msg_label)
        self.neighbor_message_edit = QTextEdit()
        self.neighbor_message_edit.setFont(font_default)
        self.neighbor_message_edit.setMaximumHeight(28)
        self.neighbor_message_edit.setText("안녕하세요! {nickname}님 서로이웃 해요!")
        message_layout.addWidget(self.neighbor_message_edit)

        layout.addWidget(message_group)

        # 공감/댓글 옵션 그룹
        interaction_group = QGroupBox("공감/댓글 옵션")
        interaction_group.setFont(font_default)
        interaction_layout = QVBoxLayout(interaction_group)
        interaction_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내부 여백 줄임
        interaction_layout.setSpacing(8)  # 그룹 내 요소간 간격 줄임

        # 공감/댓글 체크박스 가로 배치
        checkbox_layout = QHBoxLayout()

        # 공감 체크박스
        self.like_checkbox = QCheckBox("공감하기")
        self.like_checkbox.setFont(font_default)
        self.like_checkbox.setChecked(True)  # 기본값 True
        checkbox_layout.addWidget(self.like_checkbox)

        # 댓글 체크박스
        self.comment_checkbox = QCheckBox("댓글 작성")
        self.comment_checkbox.setFont(font_default)
        self.comment_checkbox.setChecked(True)  # 기본값 True
        self.comment_checkbox.toggled.connect(self.on_comment_checkbox_toggled)
        checkbox_layout.addWidget(self.comment_checkbox)

        checkbox_layout.addStretch()  # 오른쪽 공간 채우기
        interaction_layout.addLayout(checkbox_layout)

        # 댓글 세부 옵션 그룹 (댓글 체크박스가 체크된 경우에만 표시)
        self.comment_detail_group = QGroupBox("댓글 세부 옵션")
        self.comment_detail_group.setFont(font_default)
        comment_detail_layout = QVBoxLayout(self.comment_detail_group)
        comment_detail_layout.setContentsMargins(15, 15, 15, 15)
        comment_detail_layout.setSpacing(10)

        # 댓글 타입 라디오 버튼과 비밀댓글 체크박스를 가로로 배치
        comment_options_layout = QHBoxLayout()

        self.comment_type_group = QButtonGroup()

        self.ai_radio = QRadioButton("AI 댓글")
        self.ai_radio.setFont(font_default)
        self.ai_radio.setChecked(True)
        self.ai_radio.toggled.connect(self.on_ai_comment_toggled)
        self.comment_type_group.addButton(self.ai_radio, 0)
        comment_options_layout.addWidget(self.ai_radio)

        self.random_radio = QRadioButton("랜덤 멘트")
        self.random_radio.setFont(font_default)
        self.random_radio.toggled.connect(self.on_random_comment_toggled)
        self.comment_type_group.addButton(self.random_radio, 1)
        comment_options_layout.addWidget(self.random_radio)

        # 비밀댓글 체크박스 추가 (가로 배치)
        self.secret_comment_checkbox = QCheckBox("비밀댓글 달기")
        self.secret_comment_checkbox.setFont(font_default)
        comment_options_layout.addWidget(self.secret_comment_checkbox)

        comment_options_layout.addStretch()  # 오른쪽 공간 채우기
        comment_detail_layout.addLayout(comment_options_layout)

        # AI 댓글용 Gemini API 키 입력칸
        self.gemini_api_layout = QHBoxLayout()
        self.gemini_api_label = QLabel("Gemini API 키:")
        self.gemini_api_label.setFont(font_default)
        self.gemini_api_layout.addWidget(self.gemini_api_label)

        self.gemini_api_edit = QLineEdit()
        self.gemini_api_edit.setFont(font_default)
        self.gemini_api_edit.setPlaceholderText("Gemini API 키를 입력하세요...")
        self.gemini_api_edit.setEchoMode(QLineEdit.Password)  # 비밀번호처럼 숨김 처리
        self.gemini_api_layout.addWidget(self.gemini_api_edit)

        comment_detail_layout.addLayout(self.gemini_api_layout)

        # 랜덤 댓글 입력창 (랜덤 멘트 선택 시에만 표시)
        self.random_label = QLabel("랜덤 댓글 목록:")
        self.random_label.setFont(font_default)
        comment_detail_layout.addWidget(self.random_label)
        self.random_comments_edit = QTextEdit()
        self.random_comments_edit.setFont(font_default)
        self.random_comments_edit.setMaximumHeight(80)
        default_comments = [
            "좋은 글 잘 읽었어요! {nickname}님",
            "유익한 정보 감사해요~ {nickname}님!",
            "정말 도움이 되는 글이네요 {nickname}님 ㅎㅎ",
            "오늘도 좋은 하루 되세요 {nickname}님!",
            "항상 좋은 글 감사드려요 {nickname}님^^"
        ]
        self.random_comments_edit.setText('\n'.join(default_comments))
        comment_detail_layout.addWidget(self.random_comments_edit)

        interaction_layout.addWidget(self.comment_detail_group)
        layout.addWidget(interaction_group)

        # 체류 시간 그룹
        wait_group = QGroupBox("체류 시간")
        wait_group.setFont(font_default)
        wait_layout = QHBoxLayout(wait_group)
        wait_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내부 여백 줄임
        wait_layout.setSpacing(8)  # 그룹 내 요소간 간격 줄임

        wait_label = QLabel("기본 10초 + 추가 시간:")
        wait_label.setFont(font_default)
        wait_layout.addWidget(wait_label)
        self.wait_time_spin = QSpinBox()
        self.wait_time_spin.setFont(font_default)
        self.wait_time_spin.setMinimumHeight(30)  # 스핀박스 높이 줄임
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
        layout.setContentsMargins(10, 10, 10, 10)  # 탭 내부 여백 줄임
        layout.setSpacing(10)  # 그룹간 간격 줄임

        # 현재 설정 표시 그룹
        status_group = QGroupBox("현재 설정")
        font_default = QFont()
        font_default.setPointSize(10)  # 기본 폰트 크기
        status_group.setFont(font_default)
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내부 여백 줄임

        self.status_label = QLabel("설정을 확인하세요.")
        self.status_label.setFont(font_default)
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_group)

        # 실행 컨트롤 (소제목 제거)
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        control_layout.setSpacing(10)

        self.start_button = QPushButton("아이디 추출하기")
        self.start_button.setMinimumHeight(50)
        button_font = QFont()
        button_font.setPointSize(12)  # 버튼 폰트 크기 조정
        button_font.setBold(True)
        self.start_button.setFont(button_font)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #fe4847;
                color: white;
                border: 2px solid #fe4847;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e63946;
                border: 2px solid #e63946;
                transform: scale(1.02);
            }
            QPushButton:pressed {
                background-color: #d62828;
                border: 2px solid #d62828;
            }
        """)
        self.start_button.clicked.connect(self.toggle_automation)
        control_layout.addWidget(self.start_button)

        self.view_extracted_users_btn = QPushButton("추출한 계정 보기")
        self.view_extracted_users_btn.setMinimumHeight(40)
        self.view_extracted_users_btn.setFont(button_font)
        self.view_extracted_users_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #444;
                border: 2px solid #666;
            }
            QPushButton:pressed {
                background-color: #222;
                border: 2px solid #222;
            }
        """)
        self.view_extracted_users_btn.clicked.connect(self.show_extracted_users)
        control_layout.addWidget(self.view_extracted_users_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(font_default)
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        layout.addLayout(control_layout)

        # 로그 그룹
        log_group = QGroupBox("실행 로그")
        log_group.setFont(font_default)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(15, 15, 15, 15)  # 그룹 내부 여백 줄임

        self.log_text = QTextEdit()
        self.log_text.setFont(font_default)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # 라이선스 설정 그룹
        license_group = QGroupBox("활성화 코드 설정")
        license_group.setFont(font_default)
        license_layout = QVBoxLayout(license_group)
        license_layout.setContentsMargins(15, 15, 15, 15)
        license_layout.setSpacing(10)

        # 라이선스 정보와 상태를 가로로 배치
        license_info_layout = QHBoxLayout()

        license_info_label = QLabel("활성화 코드는 주문조회 페이지에서 확인 가능합니다.")
        license_info_label.setFont(font_default)
        license_info_layout.addWidget(license_info_label)

        # 라이선스 상태 표시 레이블
        self.license_status_label = QLabel("활성화 상태: 미확인")
        self.license_status_label.setFont(font_default)
        license_info_layout.addWidget(self.license_status_label)

        license_info_layout.addStretch()  # 오른쪽 공간 채우기
        license_layout.addLayout(license_info_layout)

        # 라이선스 키 입력과 검증 버튼을 가로로 배치
        license_input_layout = QHBoxLayout()

        self.license_key_edit = QLineEdit()
        self.license_key_edit.setFont(font_default)
        self.license_key_edit.setMinimumHeight(30)
        self.license_key_edit.setPlaceholderText("활성화 코드를 입력하세요...")
        license_input_layout.addWidget(self.license_key_edit)

        self.validate_license_btn = QPushButton("활성화 코드 검증")
        self.validate_license_btn.setFont(font_default)
        self.validate_license_btn.setMinimumHeight(30)
        self.validate_license_btn.clicked.connect(self.validate_license_key)
        license_input_layout.addWidget(self.validate_license_btn)

        license_layout.addLayout(license_input_layout)

        layout.addWidget(license_group)

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
                self.config_manager.get('neighbor_collection_count') or 10)
            self.start_page_spin.setValue(
                self.config_manager.get('start_page', 1))

            self.base_blog_edit.setText(
                self.config_manager.get('base_blog_url', ''))
            self.neighbor_count_spin.setValue(
                self.config_manager.get('neighbor_count') or 10)

            # 방식에 따라 해당 그룹 표시
            self.on_method_changed()

            # 상세 설정
            self.neighbor_message_edit.setText(self.config_manager.get(
                'neighbor_message', '안녕하세요! {nickname}님 서로이웃 해요!'))

            # 공감/댓글 체크박스 설정
            self.like_checkbox.setChecked(
                self.config_manager.get('enable_like', True))
            self.comment_checkbox.setChecked(
                self.config_manager.get('enable_comment', True))

            # 댓글 타입 설정
            comment_type = self.config_manager.get('comment_type', 'ai')
            if comment_type == 'ai':
                self.ai_radio.setChecked(True)
            else:  # 'random'
                self.random_radio.setChecked(True)

            random_comments = self.config_manager.get('random_comments', [])
            if random_comments:
                self.random_comments_edit.setText('\n'.join(random_comments))

            # 비밀댓글 옵션
            self.secret_comment_checkbox.setChecked(
                self.config_manager.get('secret_comment', False))

            # Gemini API 키 로드
            self.gemini_api_edit.setText(
                self.config_manager.get('gemini_api_key', ''))

            self.wait_time_spin.setValue(
                self.config_manager.get('wait_time', 0))

            # 라이선스 설정 로드
            license_settings = self.config_manager.get('license_settings', {})
            self.license_key_edit.setText(
                license_settings.get('license_key', ''))
            self.update_license_status()

            # 체크박스 토글 상태 업데이트
            self.on_comment_checkbox_toggled()

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

            # 비밀댓글 옵션
            self.config_manager.set(
                'secret_comment', self.secret_comment_checkbox.isChecked())

            # Gemini API 키
            self.config_manager.set(
                'gemini_api_key', self.gemini_api_edit.text().strip())

            self.config_manager.set('wait_time', self.wait_time_spin.value())

            # 라이선스 설정 저장
            license_settings = self.config_manager.get('license_settings', {})
            license_settings['license_key'] = self.license_key_edit.text(
            ).strip()
            self.config_manager.set('license_settings', license_settings)

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

        # 공감/댓글 체크박스 설정
        self.config_manager.set('enable_like', self.like_checkbox.isChecked())
        self.config_manager.set(
            'enable_comment', self.comment_checkbox.isChecked())

        # 댓글 타입 설정
        comment_type = 'ai' if self.ai_radio.isChecked() else 'random'
        self.config_manager.set('comment_type', comment_type)

        # 랜덤 댓글
        random_comments_text = self.random_comments_edit.toPlainText().strip()
        random_comments = [
            line.strip() for line in random_comments_text.split('\n') if line.strip()]
        self.config_manager.set('random_comments', random_comments)

        # 비밀댓글 옵션
        self.config_manager.set(
            'secret_comment', self.secret_comment_checkbox.isChecked())

        # Gemini API 키
        self.config_manager.set(
            'gemini_api_key', self.gemini_api_edit.text().strip())

        self.config_manager.set('wait_time', self.wait_time_spin.value())

        # 라이선스 설정
        license_settings = self.config_manager.get('license_settings', {})
        license_settings['license_key'] = self.license_key_edit.text().strip()
        self.config_manager.set('license_settings', license_settings)

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
            collection_count = self.config_manager.get(
                'neighbor_collection_count')
            status_text += f"수집 개수: {collection_count if collection_count else '미설정'}개"
        else:
            base_url = self.config_manager.get('base_blog_url', '')
            status_text += f"기준 블로그: {base_url if base_url else '미설정'}\n"
            neighbor_count = self.config_manager.get('neighbor_count')
            status_text += f"이웃 개수: {neighbor_count if neighbor_count else '미설정'}개"

        self.status_label.setText(status_text)

    def show_extracted_users(self):
        """추출된 계정 관리 창 표시"""
        try:
            # PyQt5 앱이 실행 중인지 확인
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                QMessageBox.warning(self, "경고", "PyQt5 애플리케이션이 초기화되지 않았습니다.")
                return

            extracted_ids_window = ExtractedIdsWindow(self)
            extracted_ids_window.exec_()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            QMessageBox.critical(
                self, "오류", f"추출된 계정 창을 여는 중 오류가 발생했습니다:\n{str(e)}")

    def start_auto_cancel(self):
        """서이추 신청 자동 취소 시작"""
        try:
            # 네이버 아이디 확인
            naver_id = self.config_manager.get('naver_id', '').strip()
            if not naver_id:
                QMessageBox.warning(
                    self, "⚠️ 경고", "🔑 네이버 아이디가 설정되지 않았습니다.\n\n계정 설정을 먼저 해주세요.")
                return

            # 페이지 선택 다이얼로그 표시
            input_dialog = QInputDialog(self)
            input_dialog.setWindowTitle("📄 페이지 선택")
            input_dialog.setLabelText("🔙 뒤에서부터 몇 페이지를 취소할까요?")
            input_dialog.setIntValue(1)
            input_dialog.setIntMinimum(1)
            input_dialog.setIntMaximum(50)
            input_dialog.setIntStep(1)
            input_dialog.setInputMode(QInputDialog.IntInput)

            # 버튼 텍스트 변경
            input_dialog.setOkButtonText("확인")
            input_dialog.setCancelButtonText("취소")

            ok = input_dialog.exec_()
            pages = input_dialog.intValue()

            if not ok:
                return

            # 확인 다이얼로그
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("❓ 중요 확인")
            msg_box.setText(
                f"🚨 뒤에서부터 {pages}페이지의 서이추 신청을 모두 취소하시겠습니까?\n\n⚠️ 이 작업은 취소할 수 없습니다.")
            msg_box.setIcon(QMessageBox.Question)

            # 커스텀 버튼 추가
            execute_btn = msg_box.addButton("실행하기", QMessageBox.YesRole)
            cancel_btn = msg_box.addButton("취소", QMessageBox.NoRole)

            msg_box.exec_()

            if msg_box.clickedButton() == execute_btn:
                self.execute_auto_cancel(naver_id, pages)

        except Exception as e:
            QMessageBox.critical(
                self, "❌ 오류", f"😱 자동 취소 시작 중 오류가 발생했습니다:\n\n{str(e)}")

    def execute_auto_cancel(self, naver_id, pages):
        """서이추 신청 자동 취소 실행"""
        try:
            # 프로그레스 다이얼로그 생성
            progress = QProgressDialog(
                f"🚫 {pages}페이지 서이추 신청 취소 중...", "중단하기", 0, pages, self)
            progress.setWindowTitle("🔄 서이추 신청 자동 취소")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumWidth(400)
            progress.setMinimumHeight(120)

            # 프로그레스 다이얼로그 폰트 설정
            font = progress.font()
            font.setPointSize(10)
            progress.setFont(font)

            progress.show()

            # 블로그 자동화 인스턴스 생성
            from automation.blog_automation import BlogAutomation
            automation = BlogAutomation(headless=False)

            if not automation.setup_driver():
                QMessageBox.critical(self, "오류", "브라우저 설정에 실패했습니다.")
                return

            # 네이버 로그인
            naver_password = self.config_manager.get('naver_password', '')
            if not automation.login(naver_id, naver_password):
                QMessageBox.critical(self, "오류", "네이버 로그인에 실패했습니다.")
                automation.close()
                return

            # 서이추 신청 취소 실행
            from automation.buddy_cancel_manager import BuddyCancelManager
            cancel_manager = BuddyCancelManager(
                automation.get_driver(), automation.logger)

            success_count = 0
            for page_num in range(pages):
                if progress.wasCanceled():
                    break

                progress.setValue(page_num)
                progress.setLabelText(f"🔄 페이지 {page_num + 1}/{pages} 처리 중...")

                if cancel_manager.cancel_buddy_requests_page(naver_id):
                    success_count += 1

            progress.setValue(pages)
            automation.close()

            # 결과 메시지
            if success_count == pages:
                QMessageBox.information(self, "✅ 완료",
                                        f"🎉 서이추 신청 취소 완료!\n\n📊 결과: {success_count}/{pages}페이지 성공")
            else:
                QMessageBox.information(self, "⚠️ 부분 완료",
                                        f"📊 서이추 신청 취소 결과\n\n성공: {success_count}/{pages}페이지\n일부 페이지에서 문제가 발생했을 수 있습니다.")

        except Exception as e:
            QMessageBox.critical(
                self, "오류", f"자동 취소 실행 중 오류가 발생했습니다:\n{str(e)}")
            try:
                automation.close()
            except:
                pass

    def on_comment_checkbox_toggled(self):
        """댓글 체크박스 상태 변경 시 호출"""
        is_comment_enabled = self.comment_checkbox.isChecked()

        # 댓글 체크박스가 체크된 경우에만 세부 옵션 표시
        self.comment_detail_group.setVisible(is_comment_enabled)

        # AI 댓글이 선택되었고 댓글이 활성화된 경우에만 API 키 입력칸 표시
        if is_comment_enabled:
            self.on_ai_comment_toggled()
            self.on_random_comment_toggled()

    def on_ai_comment_toggled(self):
        """AI 댓글 라디오 버튼 상태 변경 시 호출"""
        is_ai_selected = self.ai_radio.isChecked()
        is_comment_enabled = self.comment_checkbox.isChecked()

        # AI 댓글이 선택되고 댓글이 활성화된 경우에만 Gemini API 키 입력칸 표시
        show_api_key = is_ai_selected and is_comment_enabled
        self.gemini_api_label.setVisible(show_api_key)
        self.gemini_api_edit.setVisible(show_api_key)

    def on_random_comment_toggled(self):
        """랜덤 댓글 라디오 버튼 상태 변경 시 호출"""
        is_random_selected = self.random_radio.isChecked()
        is_comment_enabled = self.comment_checkbox.isChecked()

        # 랜덤 멘트가 선택되고 댓글이 활성화된 경우에만 랜덤 댓글 목록 표시
        show_random_comments = is_random_selected and is_comment_enabled
        self.random_label.setVisible(show_random_comments)
        self.random_comments_edit.setVisible(show_random_comments)

    def toggle_automation(self):
        """아이디 추출 시작/중지"""
        if not self.is_running:
            # 자동화 시작 전에 현재 설정을 자동으로 저장
            try:
                self.save_current_settings()
                self.log_message("✅ 설정 자동 저장 완료")
            except Exception as e:
                QMessageBox.critical(
                    self, "오류", f"설정 저장 중 오류가 발생했습니다: {str(e)}")
                return

            # 라이선스 검증
            if not self.validate_license_before_start():
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
                    QMessageBox.warning(
                        self, "설정 부족", "기준 블로그 URL을 먼저 설정해주세요.")
                    return

            # 자동화 시작
            self.is_running = True
            self.start_button.setText("추출 중지")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 무한 진행바

            self.log_message("=== 아이디 추출 시작 ===")

            # 워커 스레드 시작
            self.automation_worker = AutomationWorker(self.config_manager)
            self.automation_worker.progress_updated.connect(self.log_message)
            self.automation_worker.finished.connect(
                self.on_automation_finished)
            self.automation_worker.error_occurred.connect(
                self.on_automation_error)
            self.automation_worker.cleanup_done.connect(
                self.on_worker_cleanup_done)
            self.automation_worker.start()

        else:
            # 추출 중지
            self.stop_automation(force=True)

    def stop_automation(self, force: bool = False):
        """아이디 추출 중지"""
        self.is_running = False
        self.start_button.setText("아이디 추출하기")
        self.progress_bar.setVisible(False)

        if self.automation_worker:
            if force and self.automation_worker.isRunning():
                self.automation_worker.requestInterruption()
                self.log_message("🛑 아이디 추출 중지 요청 전송")

            if not self.automation_worker.isRunning():
                self.on_worker_cleanup_done()

        self.log_message("=== 아이디 추출 중지 ===")

    def on_automation_finished(self, success_count, total_count):
        """아이디 추출 완료 처리"""
        self.stop_automation()

        duplicate_count = max(total_count - success_count, 0)

        self.log_message("=== 아이디 추출 완료 ===")
        self.log_message(
            f"📊 추출 결과: 총 {total_count}개, 신규 {success_count}개, 기존 {duplicate_count}개")

        QMessageBox.information(
            self,
            "추출 완료",
            f"아이디 추출이 완료되었습니다.\n\n"
            f"총 추출: {total_count}개\n"
            f"신규 저장: {success_count}개\n"
            f"기존 아이디: {duplicate_count}개"
        )

    def on_automation_error(self, error_msg):
        """아이디 추출 오류 처리"""
        self.stop_automation()
        self.log_message(f"❌ 오류: {error_msg}")
        QMessageBox.critical(self, "오류", error_msg)

    def on_worker_cleanup_done(self):
        """워커 스레드 종료 후 참조 정리"""
        QTimer.singleShot(0, self._finalize_worker_cleanup)

    def _finalize_worker_cleanup(self):
        """워커 종료 이후 안전하게 참조 해제"""
        if not self.automation_worker:
            return

        if self.automation_worker.isRunning():
            QTimer.singleShot(50, self._finalize_worker_cleanup)
            return

        self.automation_worker.deleteLater()
        self.automation_worker = None

    def log_message(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"

        self.log_text.append(formatted_message)

        # 자동 스크롤
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def validate_license_key(self):
        """라이선스 키 검증 버튼 클릭 시 실행"""
        license_key = self.license_key_edit.text().strip()

        if not license_key:
            QMessageBox.warning(self, "입력 오류", "활성화 코드를 먼저 입력해주세요.")
            return

        try:
            from utils.license_validator import validate_license

            # 로딩 다이얼로그 표시
            loading_dialog = QProgressDialog("코드 검증 중...", "취소", 0, 0, self)
            loading_dialog.setWindowTitle("활성화 코드 검증")
            loading_dialog.setWindowModality(Qt.WindowModal)
            loading_dialog.show()

            # 라이선스 검증 실행
            result = validate_license(license_key)
            loading_dialog.close()

            if result['valid']:
                QMessageBox.information(
                    self, "검증 완료", f"✅ {result['message']}")
                # 검증 성공 시 설정 저장
                license_settings = self.config_manager.get(
                    'license_settings', {})
                license_settings['license_key'] = license_key
                license_settings['last_validation'] = datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')
                self.config_manager.set('license_settings', license_settings)
                self.config_manager.save_config()
            else:
                QMessageBox.warning(self, "검증 실패", f"❌ {result['message']}")

            self.update_license_status()

        except ImportError:
            QMessageBox.critical(self, "오류", "활성화 코드 검증 모듈을 찾을 수 없습니다.")
        except Exception as e:
            loading_dialog.close()
            QMessageBox.critical(
                self, "오류", f"활성화 코드 검증 중 오류가 발생했습니다:\n{str(e)}")

    def update_license_status(self):
        """라이선스 상태 업데이트"""
        license_key = self.license_key_edit.text().strip()

        if not license_key:
            self.license_status_label.setText("활성화 상태: 미입력")
            self.license_status_label.setStyleSheet("color: gray;")
            return

        try:
            from utils.license_validator import validate_license
            result = validate_license(license_key)

            if result['valid']:
                days_remaining = result.get('days_remaining', 0)
                if days_remaining <= 7:
                    self.license_status_label.setText(
                        f"활성화 상태: 곧 만료 ({days_remaining}일 남음)")
                    self.license_status_label.setStyleSheet("color: orange;")
                else:
                    self.license_status_label.setText(
                        f"활성화 상태: 유효 ({days_remaining}일 남음)")
                    self.license_status_label.setStyleSheet("color: green;")
            else:
                self.license_status_label.setText("활성화 상태: 무효/만료")
                self.license_status_label.setStyleSheet("color: red;")

        except Exception:
            self.license_status_label.setText("활성화 상태: 확인 불가")
            self.license_status_label.setStyleSheet("color: gray;")

    def validate_license_before_start(self):
        """자동화 시작 전 라이선스 검증"""
        license_key = self.license_key_edit.text().strip()

        if not license_key:
            QMessageBox.warning(self, "코드 필요",
                                "활성화 코드가 필요합니다.\n상세 설정 탭에서 활성화 코드를 입력하고 검증해주세요.")
            return False

        try:
            from utils.license_validator import validate_license
            result = validate_license(license_key)

            if not result['valid']:
                QMessageBox.warning(self, "라이선스 오류",
                                    f"코드가 유효하지 않습니다.\n\n{result['message']}")
                return False

            # 만료 임박 경고
            days_remaining = result.get('days_remaining', 0)
            if days_remaining <= 7:
                reply = QMessageBox.question(
                    self, "코드 만료 임박",
                    f"활성화 코드가 {days_remaining}일 후 만료됩니다.\n\n계속 진행하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.No:
                    return False

            return True

        except Exception as e:
            QMessageBox.critical(self, "코드 검증 오류",
                                 f"활성화 코드 검증 중 오류가 발생했습니다:\n{str(e)}")
            return False


if __name__ == "__main__":

    # 그래도 실행하고 싶다면
    try:
        # DPI 인식 및 자동 스케일링 활성화
        import os
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

        # 고해상도 디스플레이 지원 설정
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)

        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        print("대신 'python run_gui.py'를 사용해보세요.")
