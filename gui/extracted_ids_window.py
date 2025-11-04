from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QMessageBox, QHeaderView, QAbstractItemView,
                             QCheckBox, QLineEdit, QFileDialog, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from automation import BlogAutomation
from utils.extracted_ids_manager import ExtractedIdsManager
from utils.config_manager import ConfigManager
import random
import time


class NeighborAutomationWorker(QThread):
    """추출된 아이디로 서이추를 진행하는 워커"""

    progress_message = pyqtSignal(str)
    status_updated = pyqtSignal(str, bool, str)
    finished = pyqtSignal(int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, blog_ids, parent=None):
        super().__init__(parent)
        self.blog_ids = blog_ids
        self.config_manager = ConfigManager()
        self.blog_automation = None
        self.extracted_ids_manager = ExtractedIdsManager()

    def run(self):
        success_count = 0
        total_count = len(self.blog_ids)

        try:
            if total_count == 0:
                self.finished.emit(0, 0)
                return

            # 최신 설정 로드
            self.config_manager.config = self.config_manager.load_config()

            naver_id = self.config_manager.get('naver_id', '').strip()
            naver_password = self.config_manager.get('naver_password', '').strip()

            if not naver_id or not naver_password:
                self.error_occurred.emit("네이버 계정 정보가 설정되지 않았습니다.")
                return

            enable_like = self.config_manager.get('enable_like', True)
            enable_comment = self.config_manager.get('enable_comment', True)

            self.blog_automation = BlogAutomation()
            self.progress_message.emit("네이버 로그인 중...")

            if not self.blog_automation.login(naver_id, naver_password, max_retries=2):
                self.error_occurred.emit("네이버 로그인에 실패했습니다.")
                return

            self.progress_message.emit(" 네이버 로그인 성공")

            for index, blog_id in enumerate(self.blog_ids, 1):
                if self.isInterruptionRequested():
                    break

                blog_id = blog_id.strip()
                if not blog_id:
                    continue

                self.progress_message.emit(
                    f"[{index}/{total_count}] {blog_id} 서이추 시도 중...")

                try:
                    self.blog_automation.buddy_manager.buddy_available = False
                    addition_result = self.blog_automation.buddy_manager.add_buddy_to_blog_mobile(
                        blog_id)
                    success = addition_result and self.blog_automation.buddy_manager.buddy_available

                    if success:
                        success_count += 1

                        if enable_like or enable_comment:
                            moved = self.blog_automation.buddy_manager.navigate_to_latest_post_mobile(
                                blog_id)
                            if moved:
                                interaction_success = self.blog_automation.post_interaction.process_current_page_interaction(
                                    blog_id)
                                if interaction_success:
                                    self.progress_message.emit(
                                        f"   └ 게시글 상호작용 완료: {blog_id}")
                                else:
                                    self.progress_message.emit(
                                        f"   └ 게시글 상호작용 실패: {blog_id}")
                            else:
                                self.progress_message.emit(
                                    f"   └ 최신 게시글 이동 실패: {blog_id}")

                        self.extracted_ids_manager.update_status(
                            blog_id, success=True)
                        timestamp = self.extracted_ids_manager.extracted_ids.get(
                            blog_id, {}).get("date", "")
                        self.status_updated.emit(blog_id, True, timestamp)
                        self.progress_message.emit(
                            f"[{index}/{total_count}] {blog_id} 서이추 성공")
                    else:
                        self.extracted_ids_manager.update_status(
                            blog_id, success=False)
                        timestamp = self.extracted_ids_manager.extracted_ids.get(
                            blog_id, {}).get("date", "")
                        self.status_updated.emit(blog_id, False, timestamp)
                        self.progress_message.emit(
                            f"[{index}/{total_count}] {blog_id} 서이추 실패")

                except Exception as e:
                    try:
                        self.extracted_ids_manager.update_status(
                            blog_id, success=False)
                        timestamp = self.extracted_ids_manager.extracted_ids.get(
                            blog_id, {}).get("date", "")
                        self.status_updated.emit(blog_id, False, timestamp)
                    except Exception:
                        pass

                    self.progress_message.emit(
                        f"[{index}/{total_count}] {blog_id} 처리 중 오류: {str(e)}")

                if index < total_count:
                    time.sleep(random.uniform(1, 2))

            self.finished.emit(success_count, total_count)

        except Exception as e:
            self.error_occurred.emit(str(e))

        finally:
            if self.blog_automation:
                try:
                    self.blog_automation.cleanup_driver()
                except Exception:
                    pass


class ExtractedIdsWindow(QDialog):
    """추출된 블로그 아이디 관리 창"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.extracted_ids_manager = ExtractedIdsManager()
        self.setWindowTitle("추출된 계정 관리")

        # DPI 스케일링을 고려한 창 크기 설정
        self.setMinimumSize(800, 600)
        self.resize(900, 650)

        # 화면 중앙에 위치시키기
        if parent:
            # 부모 창을 기준으로 중앙 배치
            parent_geometry = parent.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - 900) // 2
            y = parent_geometry.y() + (parent_geometry.height() - 650) // 2
            self.move(x, y)
        else:
            # 화면 중앙에 배치
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.desktop().screenGeometry()
            size = self.geometry()
            self.move(int((screen.width() - size.width()) / 2),
                      int((screen.height() - size.height()) / 2))

        self.setModal(True)
        self.worker = None
        self.worker_running = False
        self._stop_requested = False
        self.active_security_popups = []

        # 다크 테마 적용
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: white;
            }
            QLabel {
                color: white;
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
            QTableWidget {
                background-color: #1a1a1a;
                color: white;
                gridline-color: #333;
                border: 1px solid #333;
                selection-background-color: #fe4847;
                alternate-background-color: #2a2a2a;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #333;
            }
            QTableWidget::item:selected {
                background-color: #fe4847;
                color: white;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
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
        """)

        self.setup_ui()
        self.load_extracted_ids()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 폰트 설정 (크기 축소)
        font_default = QFont()
        font_default.setPointSize(10)

        # 제목
        title_label = QLabel("추출된 계정 목록")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #fe4847; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 통계 정보
        self.stats_label = QLabel()
        self.stats_label.setFont(font_default)
        self.stats_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.stats_label)
        
        # 검색 필터
        filter_group = QGroupBox("필터 및 검색")
        filter_group.setFont(font_default)
        filter_layout = QHBoxLayout(filter_group)
        
        search_label = QLabel("검색:")
        search_label.setFont(font_default)
        filter_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setFont(font_default)
        self.search_edit.setPlaceholderText("블로그 아이디로 검색...")
        self.search_edit.textChanged.connect(self.filter_table)
        filter_layout.addWidget(self.search_edit)
        
        # 상태 필터 체크박스
        self.show_success_cb = QCheckBox("성공만 표시")
        self.show_success_cb.setFont(font_default)
        self.show_success_cb.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.show_success_cb)
        
        self.show_fail_cb = QCheckBox("실패만 표시")
        self.show_fail_cb.setFont(font_default)
        self.show_fail_cb.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.show_fail_cb)
        
        layout.addWidget(filter_group)
        
        # 상단 빠른 선택 버튼
        quick_select_layout = QHBoxLayout()
        self.select_50_btn = QPushButton("50개 선택")
        self.select_50_btn.setFont(font_default)
        self.select_50_btn.clicked.connect(lambda: self.select_top_items(50))
        quick_select_layout.addWidget(self.select_50_btn)

        self.select_100_btn = QPushButton("100개 선택")
        self.select_100_btn.setFont(font_default)
        self.select_100_btn.clicked.connect(lambda: self.select_top_items(100))
        quick_select_layout.addWidget(self.select_100_btn)

        quick_select_layout.addStretch()
        layout.addLayout(quick_select_layout)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setFont(font_default)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["선택", "블로그 아이디", "서이추 상태", "처리 날짜"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(True)
        
        # 테이블 헤더 설정
        header = self.table.horizontalHeader()
        header.setFont(font_default)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 100)
        
        layout.addWidget(self.table)
        
        # 버튼 그룹
        button_layout = QHBoxLayout()
        
        # 전체 선택/해제
        self.select_all_btn = QPushButton("전체 선택")
        self.select_all_btn.setFont(font_default)
        self.select_all_btn.clicked.connect(self.select_all_items)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("전체 해제")
        self.deselect_all_btn.setFont(font_default)
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)
        button_layout.addWidget(self.deselect_all_btn)
        
        # 선택된 항목 삭제
        self.delete_selected_btn = QPushButton("선택 삭제")
        self.delete_selected_btn.setFont(font_default)
        self.delete_selected_btn.clicked.connect(self.delete_selected_items)
        button_layout.addWidget(self.delete_selected_btn)
        
        # 전체 삭제
        self.delete_all_btn = QPushButton("전체 삭제")
        self.delete_all_btn.setFont(font_default)
        self.delete_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #fe4847;
                color: white;
                border: 1px solid #fe4847;
                border-radius: 5px;
                padding: 8px 16px;
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
        self.delete_all_btn.clicked.connect(self.delete_all_items)
        button_layout.addWidget(self.delete_all_btn)
        
        layout.addLayout(button_layout)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.start_neighbor_btn = QPushButton("서이추 시작하기")
        self.start_neighbor_btn.setFont(font_default)
        self.start_neighbor_btn.setMinimumHeight(36)
        self.start_neighbor_btn.setStyleSheet("""
            QPushButton {
                background-color: #fe4847;
                color: white;
                border: 1px solid #fe4847;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e63946;
                border: 1px solid #e63946;
            }
            QPushButton:pressed {
                background-color: #d62828;
            }
            QPushButton:disabled {
                background-color: #555;
                border: 1px solid #555;
                color: #999;
            }
        """)
        self.start_neighbor_btn.clicked.connect(self.toggle_neighbor_addition)
        action_layout.addWidget(self.start_neighbor_btn)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        self.status_label = QLabel("")
        self.status_label.setFont(font_default)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 내보내기 및 닫기 버튼
        bottom_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("텍스트로 내보내기")
        self.export_btn.setFont(font_default)
        self.export_btn.clicked.connect(self.export_to_text)
        bottom_layout.addWidget(self.export_btn)
        
        bottom_layout.addStretch()
        
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.setFont(font_default)
        self.refresh_btn.clicked.connect(self.load_extracted_ids)
        bottom_layout.addWidget(self.refresh_btn)
        
        self.close_btn = QPushButton("닫기")
        self.close_btn.setFont(font_default)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #fe4847;
                color: white;
                border: 1px solid #fe4847;
                border-radius: 5px;
                padding: 8px 16px;
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
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
        self._set_worker_running(False)

    def set_controls_enabled(self, enabled: bool):
        """서이추 실행 중 버튼 및 입력 제어"""
        buttons = [
            self.select_all_btn,
            self.deselect_all_btn,
            self.select_50_btn,
            self.select_100_btn,
            self.delete_selected_btn,
            self.delete_all_btn,
            self.export_btn,
            self.refresh_btn
        ]

        for button in buttons:
            button.setEnabled(enabled)

        self.table.setEnabled(enabled)
        self.search_edit.setEnabled(enabled)
        self.show_success_cb.setEnabled(enabled)
        self.show_fail_cb.setEnabled(enabled)
        self.close_btn.setEnabled(True)
        self.start_neighbor_btn.setEnabled(True)
    
    def _set_worker_running(self, running: bool):
        """서이추 진행 상태에 따른 버튼/플래그 업데이트"""
        self.worker_running = running
        if running:
            self.start_neighbor_btn.setText("서이추 중단하기")
            self.start_neighbor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff914d;
                    color: white;
                    border: 1px solid #ff914d;
                    border-radius: 6px;
                    padding: 8px 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff7f32;
                    border: 1px solid #ff7f32;
                }
                QPushButton:pressed {
                    background-color: #ff6a1a;
                }
                QPushButton:disabled {
                    background-color: #555;
                    border: 1px solid #555;
                    color: #999;
                }
            """)
        else:
            self.start_neighbor_btn.setText("서이추 시작하기")
            self.start_neighbor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fe4847;
                    color: white;
                    border: 1px solid #fe4847;
                    border-radius: 6px;
                    padding: 8px 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e63946;
                    border: 1px solid #e63946;
                }
                QPushButton:pressed {
                    background-color: #d62828;
                }
                QPushButton:disabled {
                    background-color: #555;
                    border: 1px solid #555;
                    color: #999;
                }
            """)
        self.start_neighbor_btn.setEnabled(True)
    
    def toggle_neighbor_addition(self):
        """서이추 시작/중단 토글"""
        if self.worker and self.worker.isRunning():
            self.stop_neighbor_addition()
        else:
            self.start_neighbor_addition()
    
    def stop_neighbor_addition(self):
        """서이추 중단 요청"""
        if not (self.worker and self.worker.isRunning()):
            return
        
        self._stop_requested = True
        self.status_label.setText("서이추 중단을 요청했습니다...")
        try:
            self.worker.requestInterruption()
        except Exception:
            pass
        self.start_neighbor_btn.setText("중단 처리 중...")
        self.start_neighbor_btn.setEnabled(False)
    
    def load_extracted_ids(self):
        """추출된 아이디 목록 로드"""
        self.extracted_ids_manager.reload()
        extracted_ids = self.extracted_ids_manager.get_all_extracted_ids()
        stats = self.extracted_ids_manager.get_statistics()
        
        # 통계 정보 업데이트
        if stats['total_count'] > 0:
            self.stats_label.setText(
                f"총 {stats['total_count']:,}개 아이디 | "
                f"성공: {stats['success_count']:,}개 | "
                f"실패: {stats['fail_count']:,}개 | "
                f"대기: {stats['pending_count']:,}개 | "
                f"최초: {stats['oldest_date']} | "
                f"최근: {stats['newest_date']}"
            )
        else:
            self.stats_label.setText("추출된 아이디가 없습니다.")
        
        # 테이블 설정
        self.table.setRowCount(len(extracted_ids))
        
        # 날짜순으로 정렬 (최신순)
        sorted_items = sorted(extracted_ids.items(), key=lambda x: x[1]['date'], reverse=True)
        
        for row, (blog_id, data) in enumerate(sorted_items):
            # 체크박스
            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, checkbox)
            
            # 블로그 아이디
            id_item = QTableWidgetItem(blog_id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
            self.table.setItem(row, 1, id_item)
            
            # 서이추 상태
            status = data.get('status', '성공')
            status_item = QTableWidgetItem()
            self._apply_status_style(status_item, status)
            self.table.setItem(row, 2, status_item)
            
            # 처리 날짜
            extraction_date = data.get('date', '알 수 없음')
            date_item = QTableWidgetItem(extraction_date)
            date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
            self.table.setItem(row, 3, date_item)
        
        # 테이블 높이 조정
        self.table.resizeRowsToContents()
        self.filter_table()

    def start_neighbor_addition(self):
        """선택된 아이디로 서이추 실행"""
        if self.worker and self.worker.isRunning():
            return

        self._stop_requested = False
        selected_ids = self.get_selected_blog_ids()

        if not selected_ids:
            QMessageBox.information(self, "안내", "서이추할 블로그 아이디를 선택해주세요.")
            return

        reply = QMessageBox.question(
            self,
            "서이추 시작",
            f"선택된 {len(selected_ids)}개 아이디에 대해 서이추를 진행하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        parent = self.parent()
        if parent and hasattr(parent, "validate_license_before_start"):
            if not parent.validate_license_before_start():
                return

        self.worker = NeighborAutomationWorker(selected_ids, self)
        self.worker.progress_message.connect(self.on_neighbor_progress)
        self.worker.status_updated.connect(self.on_neighbor_status_updated)
        self.worker.finished.connect(self.on_neighbor_finished)
        self.worker.error_occurred.connect(self.on_neighbor_error)

        self._set_worker_running(True)
        self.set_controls_enabled(False)
        self.status_label.setText("서이추 준비 중...")
        self.show_security_notice()
        self.worker.start()

    def show_security_notice(self):
        """보안문자 안내 팝업을 5초간 표시"""
        notice_text = ("자동입력 방지 문자 페이지가 나타날 경우\n"
                       "비밀번호 재입력과 보안문자 해제를 직접 입력해주세요.")

        popup = QMessageBox(self)
        popup.setWindowTitle("보안문자 안내")
        popup.setText(notice_text)
        popup.setIcon(QMessageBox.Information)
        popup.setStandardButtons(QMessageBox.Ok)
        popup.setModal(False)

        popup_font = QFont(popup.font())
        popup_font.setPointSize(popup_font.pointSize() + 2)
        popup.setFont(popup_font)
        popup.show()

        self.active_security_popups.append(popup)

        def remove_popup():
            if popup in self.active_security_popups:
                self.active_security_popups.remove(popup)

        popup.finished.connect(lambda _: remove_popup())

    def on_neighbor_progress(self, message: str):
        """서이추 진행 상황 업데이트"""
        self.status_label.setText(message)

    def on_neighbor_status_updated(self, blog_id: str, success: bool, timestamp: str):
        """테이블 상태 업데이트"""
        status_text = "성공" if success else "실패"

        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 1)
            if id_item and id_item.text() == blog_id:
                status_item = self.table.item(row, 2)
                if status_item is None:
                    status_item = QTableWidgetItem()
                    self.table.setItem(row, 2, status_item)

                self._apply_status_style(status_item, status_text)

                if timestamp:
                    date_item = self.table.item(row, 3)
                    if date_item is None:
                        date_item = QTableWidgetItem()
                        self.table.setItem(row, 3, date_item)
                    date_item.setText(timestamp)
                    date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable)

                checkbox = self.table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)
                break

    def on_neighbor_finished(self, success_count: int, total_count: int):
        """서이추 완료 처리"""
        self._set_worker_running(False)
        self.set_controls_enabled(True)
        self.worker = None

        fail_count = max(total_count - success_count, 0)
        summary = (f"서이추 완료: 총 {total_count}개 중 {success_count}개 성공 "
                   f"(실패 {fail_count}개)")
        if self._stop_requested:
            self.status_label.setText("서이추가 중단되었습니다. 진행된 결과는 목록에 반영되었습니다.")
        else:
            self.status_label.setText(summary)

        self.load_extracted_ids()
        self.filter_table()

        if not self._stop_requested:
            QMessageBox.information(
                self,
                "서이추 완료",
                f"서이추가 완료되었습니다.\n\n"
                f"총 대상: {total_count}개\n"
                f"성공: {success_count}개\n"
                f"실패: {fail_count}개"
            )
        self._stop_requested = False

    def on_neighbor_error(self, message: str):
        """서이추 실행 중 오류 처리"""
        self._set_worker_running(False)
        self.set_controls_enabled(True)
        self.worker = None
        self._stop_requested = False
        self.status_label.setText(f" 오류: {message}")
        QMessageBox.critical(self, "오류", message)

    def _apply_status_style(self, item: QTableWidgetItem, status: str):
        """상태 셀 스타일 적용"""
        item.setText(status)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)

        # 배경색은 기본 테마 유지, 글자색만 상태별로 구분
        if status == '성공':
            item.setForeground(QBrush(QColor(102, 255, 178)))  # 밝은 초록
        elif status == '실패':
            item.setForeground(QBrush(QColor(255, 105, 105)))  # 밝은 빨강
        elif status == '대기':
            item.setForeground(QBrush(QColor(200, 200, 200)))
        else:
            item.setForeground(QBrush(QColor(255, 255, 255)))


    def filter_table(self):
        """테이블 필터링"""
        search_text = self.search_edit.text().lower()
        show_success_only = self.show_success_cb.isChecked()
        show_fail_only = self.show_fail_cb.isChecked()
        
        for row in range(self.table.rowCount()):
            blog_id_item = self.table.item(row, 1)
            status_item = self.table.item(row, 2)
            
            should_show = True
            
            if blog_id_item:
                blog_id = blog_id_item.text().lower()
                # 검색어 필터
                if search_text and search_text not in blog_id:
                    should_show = False
            
            if status_item and should_show:
                status = status_item.text()
                # 상태 필터
                if show_success_only and show_fail_only:
                    # 둘 다 체크된 경우 모두 표시
                    pass
                elif show_success_only:
                    # 성공만 표시
                    if status != '성공':
                        should_show = False
                elif show_fail_only:
                    # 실패만 표시  
                    if status != '실패':
                        should_show = False
            
            self.table.setRowHidden(row, not should_show)
    
    def select_all_items(self):
        """전체 항목 선택"""
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                checkbox = self.table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def deselect_all_items(self):
        """전체 항목 선택 해제"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def select_top_items(self, count: int):
        """상단 N개 항목 선택"""
        if count <= 0:
            return

        self.deselect_all_items()
        selected = 0

        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue

            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
                selected += 1
                if selected >= count:
                    break
    
    def get_selected_blog_ids(self):
        """선택된 블로그 아이디들 반환"""
        selected_ids = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                blog_id_item = self.table.item(row, 1)
                if blog_id_item:
                    selected_ids.append(blog_id_item.text())
        return selected_ids
    
    def delete_selected_items(self):
        """선택된 항목들 삭제"""
        selected_ids = self.get_selected_blog_ids()
        
        if not selected_ids:
            QMessageBox.warning(self, "경고", "삭제할 항목을 선택해주세요.")
            return
        
        reply = QMessageBox.question(
            self, "확인", 
            f"선택된 {len(selected_ids)}개 아이디를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            removed_count = self.extracted_ids_manager.remove_multiple_ids(selected_ids)
            QMessageBox.information(self, "완료", f"{removed_count}개 아이디가 삭제되었습니다.")
            self.load_extracted_ids()
    
    def delete_all_items(self):
        """전체 항목 삭제"""
        total_count = self.extracted_ids_manager.get_extracted_count()
        
        if total_count == 0:
            QMessageBox.information(self, "정보", "삭제할 항목이 없습니다.")
            return
        
        reply = QMessageBox.question(
            self, "경고", 
            f"모든 추출된 아이디({total_count:,}개)를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.extracted_ids_manager.clear_all_extracted_ids():
                QMessageBox.information(self, "완료", "모든 아이디가 삭제되었습니다.")
                self.load_extracted_ids()
            else:
                QMessageBox.critical(self, "오류", "삭제 중 오류가 발생했습니다.")
    
    def export_to_text(self):
        """텍스트 파일로 내보내기"""
        total_count = self.extracted_ids_manager.get_extracted_count()
        
        if total_count == 0:
            QMessageBox.information(self, "정보", "내보낼 항목이 없습니다.")
            return
        
        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(
            self, "텍스트 파일로 내보내기", 
            "extracted_blog_ids.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            export_path = self.extracted_ids_manager.export_to_text(file_path)
            if export_path:
                QMessageBox.information(
                    self, "완료", 
                    f"추출된 아이디 목록이 저장되었습니다:\n{export_path}"
                )
            else:
                QMessageBox.critical(self, "오류", "내보내기 중 오류가 발생했습니다.")

    def closeEvent(self, event):
        """창 닫기 시 서이추 중단 요청"""
        if self.worker and self.worker.isRunning():
            self.stop_neighbor_addition()
            if not self.worker.wait(5000):
                try:
                    self.worker.terminate()
                    self.worker.wait(2000)
                except Exception:
                    pass
        if self.worker and not self.worker.isRunning():
            self.worker = None
            self._set_worker_running(False)
        super().closeEvent(event)
