from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QMessageBox, QHeaderView, QAbstractItemView,
                             QCheckBox, QLineEdit, QFileDialog, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from utils.extracted_ids_manager import ExtractedIdsManager


class ExtractedIdsWindow(QDialog):
    """추출된 블로그 아이디 관리 창"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.extracted_ids_manager = ExtractedIdsManager()
        self.setWindowTitle("추출된 블로그 아이디 관리")
        self.setGeometry(200, 200, 800, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.load_extracted_ids()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 폰트 설정
        font_24px = QFont()
        font_24px.setPointSize(18)
        
        # 제목
        title_label = QLabel("추출된 블로그 아이디 목록")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 통계 정보
        self.stats_label = QLabel()
        self.stats_label.setFont(font_24px)
        self.stats_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.stats_label)
        
        # 검색 필터
        filter_group = QGroupBox("필터 및 검색")
        filter_group.setFont(font_24px)
        filter_layout = QHBoxLayout(filter_group)
        
        search_label = QLabel("검색:")
        search_label.setFont(font_24px)
        filter_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setFont(font_24px)
        self.search_edit.setPlaceholderText("블로그 아이디로 검색...")
        self.search_edit.textChanged.connect(self.filter_table)
        filter_layout.addWidget(self.search_edit)
        
        # 상태 필터 체크박스
        self.show_success_cb = QCheckBox("성공만 표시")
        self.show_success_cb.setFont(font_24px)
        self.show_success_cb.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.show_success_cb)
        
        self.show_fail_cb = QCheckBox("실패만 표시")
        self.show_fail_cb.setFont(font_24px)
        self.show_fail_cb.stateChanged.connect(self.filter_table)
        filter_layout.addWidget(self.show_fail_cb)
        
        layout.addWidget(filter_group)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setFont(font_24px)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["선택", "블로그 아이디", "서이추 상태", "처리 날짜"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        # 테이블 헤더 설정
        header = self.table.horizontalHeader()
        header.setFont(font_24px)
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
        self.select_all_btn.setFont(font_24px)
        self.select_all_btn.clicked.connect(self.select_all_items)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("전체 해제")
        self.deselect_all_btn.setFont(font_24px)
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)
        button_layout.addWidget(self.deselect_all_btn)
        
        # 선택된 항목 삭제
        self.delete_selected_btn = QPushButton("선택 삭제")
        self.delete_selected_btn.setFont(font_24px)
        self.delete_selected_btn.clicked.connect(self.delete_selected_items)
        button_layout.addWidget(self.delete_selected_btn)
        
        # 전체 삭제
        self.delete_all_btn = QPushButton("전체 삭제")
        self.delete_all_btn.setFont(font_24px)
        self.delete_all_btn.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        self.delete_all_btn.clicked.connect(self.delete_all_items)
        button_layout.addWidget(self.delete_all_btn)
        
        layout.addLayout(button_layout)
        
        # 내보내기 및 닫기 버튼
        bottom_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("텍스트로 내보내기")
        self.export_btn.setFont(font_24px)
        self.export_btn.clicked.connect(self.export_to_text)
        bottom_layout.addWidget(self.export_btn)
        
        bottom_layout.addStretch()
        
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.setFont(font_24px)
        self.refresh_btn.clicked.connect(self.load_extracted_ids)
        bottom_layout.addWidget(self.refresh_btn)
        
        self.close_btn = QPushButton("닫기")
        self.close_btn.setFont(font_24px)
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
    
    def load_extracted_ids(self):
        """추출된 아이디 목록 로드"""
        extracted_ids = self.extracted_ids_manager.get_all_extracted_ids()
        stats = self.extracted_ids_manager.get_statistics()
        
        # 통계 정보 업데이트
        if stats['total_count'] > 0:
            self.stats_label.setText(
                f"총 {stats['total_count']:,}개 아이디 | "
                f"성공: {stats['success_count']:,}개 | "
                f"실패: {stats['fail_count']:,}개 | "
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
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, id_item)
            
            # 서이추 상태
            status = data.get('status', '성공')
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            
            # 상태에 따른 색상 설정
            if status == '성공':
                status_item.setBackground(QColor(144, 238, 144))  # 연한 초록색
            elif status == '실패':
                status_item.setBackground(QColor(255, 182, 193))  # 연한 빨간색
            
            self.table.setItem(row, 2, status_item)
            
            # 처리 날짜
            extraction_date = data.get('date', '알 수 없음')
            date_item = QTableWidgetItem(extraction_date)
            date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, date_item)
        
        # 테이블 높이 조정
        self.table.resizeRowsToContents()
    
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