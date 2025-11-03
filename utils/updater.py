#!/usr/bin/env python3
"""
자동 업데이트 모듈
서버에서 업데이트를 확인하고 다운로드하여 설치하는 기능 제공
"""

import os
import sys
import json
import zipfile
import shutil
import tempfile
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import requests
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from version import get_version, compare_versions
from utils.logger import setup_logger

class UpdateDownloadThread(QThread):
    """업데이트 다운로드를 위한 별도 스레드"""
    
    progress = pyqtSignal(int)  # 진행률 시그널
    status = pyqtSignal(str)   # 상태 메시지 시그널
    finished = pyqtSignal(bool, str)  # 완료 시그널 (성공여부, 메시지)
    
    def __init__(self, download_url: str, save_path: str):
        super().__init__()
        self.download_url = download_url
        self.save_path = save_path
        self.logger = setup_logger()
        
    def run(self):
        """업데이트 파일 다운로드 실행"""
        try:
            self.status.emit("업데이트 다운로드 중...")
            
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(self.save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress.emit(progress)
            
            self.status.emit("다운로드 완료")
            self.finished.emit(True, "업데이트 파일 다운로드가 완료되었습니다.")
            
        except Exception as e:
            self.logger.error(f"업데이트 다운로드 실패: {str(e)}")
            self.finished.emit(False, f"다운로드 실패: {str(e)}")

class GitHubReleaseUpdater:
    """GitHub Releases를 사용한 자동 업데이트 관리 클래스"""

    def __init__(self, config: Dict):
        """
        초기화

        Args:
            config: 업데이트 관련 설정 딕셔너리
        """
        self.config = config
        self.logger = setup_logger()
        self.current_version = get_version()

        # GitHub 설정
        self.github_repo = config.get('github_repo', 'dlwnstjrzz/python_naver_blog')
        self.github_token = config.get('github_token', '')  # 선택적, private repo용
        self.check_on_startup = config.get('check_update_on_startup', True)
        self.backup_enabled = config.get('backup_on_update', True)
        self.user_preserve_paths = set(config.get('preserve_paths', []))

        # GitHub API URL 구성
        self.api_base = f"https://api.github.com/repos/{self.github_repo}"

        # 경로 설정
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.backup_dir = self.project_root / 'backups'
        self.temp_dir = Path(tempfile.mkdtemp(prefix='naver_blog_update_'))

        self._initialize_preserve_targets()

        # 업데이트 전용 로그 설정
        self.setup_update_logger()

        # 배치 스크립트 경로 (exe 업데이트용)
        self.batch_script_path = None

        # 임시 파일 정리 지연 여부
        self.defer_cleanup = False

        # 시작 시간 기록
        self.start_time = time.time()

    def setup_update_logger(self):
        """업데이트 전용 로그 파일 설정"""
        try:
            import logging
            from datetime import datetime

            # 로그 디렉토리 설정
            if getattr(sys, 'frozen', False):
                # exe 파일로 실행되는 경우, exe 파일과 같은 디렉토리에 logs 폴더 생성
                log_dir = Path(os.path.dirname(sys.executable)) / "logs"
            else:
                # Python 스크립트로 실행되는 경우
                log_dir = self.project_root / "logs"

            log_dir.mkdir(exist_ok=True)

            # 업데이트 로그 파일명 (날짜별)
            today = datetime.now().strftime('%Y%m%d')
            self.update_log_file = log_dir / f"update_{today}.log"

            # 업데이트 전용 로거 생성
            self.update_logger = logging.getLogger('updater')
            self.update_logger.setLevel(logging.DEBUG)

            # 기존 핸들러 제거
            for handler in self.update_logger.handlers[:]:
                self.update_logger.removeHandler(handler)

            # 파일 핸들러 생성
            file_handler = logging.FileHandler(self.update_log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            # 로그 포맷 설정
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.update_logger.addHandler(file_handler)

            # 업데이트 시작 로그
            self.update_logger.info("=" * 60)
            self.update_logger.info("업데이트 프로세스 시작")
            self.update_logger.info(f"현재 버전: {self.current_version}")
            self.update_logger.info(f"GitHub 레포지토리: {self.github_repo}")
            self.update_logger.info(f"실행 환경: {'PyInstaller (exe)' if getattr(sys, 'frozen', False) else 'Python 스크립트'}")
            self.update_logger.info(f"프로젝트 루트: {self.project_root}")
            self.update_logger.info(f"백업 디렉토리: {self.backup_dir}")
            self.update_logger.info(f"임시 디렉토리: {self.temp_dir}")
            self.update_logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"업데이트 로거 설정 실패: {str(e)}")

    def log_update(self, level: str, message: str):
        """업데이트 로그 기록"""
        try:
            getattr(self.update_logger, level.lower())(message)
            # 일반 로거에도 기록
            getattr(self.logger, level.lower())(f"[UPDATE] {message}")
        except:
            self.logger.info(f"[UPDATE] {message}")

    def get_github_headers(self) -> Dict[str, str]:
        """GitHub API 요청 헤더 생성"""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Python-Naver-Blog-Updater'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
            
        return headers
    
    def get_latest_release(self) -> Optional[Dict]:
        """
        GitHub에서 최신 릴리스 정보 가져오기
        
        Returns:
            Optional[Dict]: 최신 릴리스 정보 또는 None
        """
        try:
            url = f"{self.api_base}/releases/latest"
            headers = self.get_github_headers()
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"GitHub API 요청 실패: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"릴리스 정보 가져오기 실패: {str(e)}")
            return None
    
    def parse_version_from_tag(self, tag_name: str) -> str:
        """
        태그명에서 버전 추출 (v1.0.0 -> 1.0.0)
        
        Args:
            tag_name: GitHub 릴리스 태그명
            
        Returns:
            str: 정제된 버전 문자열
        """
        if tag_name.startswith('v'):
            return tag_name[1:]
        return tag_name
    
    def find_update_asset(self, assets: List[Dict], release_info: Dict) -> Optional[Dict]:
        """
        릴리스 에셋에서 업데이트 파일 찾기

        Args:
            assets: GitHub 릴리스 에셋 목록
            release_info: 릴리스 정보

        Returns:
            Optional[Dict]: 업데이트 파일 에셋 정보
        """
        import platform

        # 현재 OS 확인
        current_os = platform.system().lower()
        if current_os == 'darwin':
            target_name = 'macos'
        elif current_os == 'windows':
            target_name = 'windows'
        else:
            target_name = 'linux'  # 기본값

        self.log_update('info', f"에셋 검색 시작 (대상 OS: {target_name})")

        # 우선순위 1: 현재 OS에 맞는 zip 파일 찾기
        for asset in assets:
            name = asset.get('name', '').lower()
            self.log_update('debug', f"에셋 검사: {name}")
            if name.endswith('.zip') and target_name in name and not name.startswith('source'):
                self.log_update('info', f"OS별 에셋 발견: {asset.get('name')}")
                return asset

        # 우선순위 2: 일반적인 zip 파일 (OS 구분 없이)
        self.log_update('info', "OS별 에셋을 찾을 수 없음. 일반 zip 파일 검색 중...")
        for asset in assets:
            name = asset.get('name', '').lower()
            if name.endswith('.zip') and not name.startswith('source'):
                self.log_update('info', f"일반 zip 에셋 발견: {asset.get('name')}")
                return asset
        
        # 우선순위 3: GitHub이 자동 생성하는 소스코드 zip 사용
        # 에셋이 없으면 소스코드 다운로드 URL 생성
        tag_name = release_info.get('tag_name', '')
        if tag_name:
            # GitHub 소스코드 zip 다운로드 URL 구성
            zipball_url = f"https://github.com/{self.github_repo}/archive/refs/tags/{tag_name}.zip"
            
            # 가상 에셋 정보 생성
            return {
                'name': f"{self.github_repo}-{tag_name}.zip",
                'browser_download_url': zipball_url,
                'size': 0,  # 크기 정보 없음
                'content_type': 'application/zip'
            }
                
        return None
    
    def check_for_updates(self) -> Tuple[bool, Optional[Dict]]:
        """
        GitHub Releases에서 업데이트 확인

        Returns:
            Tuple[bool, Optional[Dict]]: (업데이트 필요 여부, 업데이트 정보)
        """
        try:
            self.log_update('info', "업데이트 확인 시작")

            # 최신 릴리스 정보 가져오기
            self.log_update('info', f"GitHub API 요청: {self.api_base}/releases/latest")
            release_info = self.get_latest_release()
            if not release_info:
                self.log_update('warning', "릴리스 정보를 가져올 수 없습니다.")
                return False, None

            self.log_update('info', f"릴리스 정보 가져오기 성공")

            # 버전 정보 추출
            tag_name = release_info.get('tag_name', '')
            if not tag_name:
                self.log_update('warning', "릴리스 태그를 찾을 수 없습니다.")
                return False, None

            latest_version = self.parse_version_from_tag(tag_name)
            release_name = release_info.get('name', tag_name)
            release_body = release_info.get('body', '업데이트 내용이 없습니다.')

            self.log_update('info', f"현재 버전: {self.current_version}")
            self.log_update('info', f"최신 버전: {latest_version}")
            self.log_update('info', f"릴리스명: {release_name}")

            # 버전 비교
            version_compare = compare_versions(self.current_version, latest_version)
            self.log_update('info', f"버전 비교 결과: {version_compare} (음수: 업데이트 필요, 0: 동일, 양수: 최신)")

            if version_compare < 0:
                self.log_update('info', "새 버전 발견! 에셋 파일 검색 중...")

                # 다운로드 가능한 에셋 찾기
                assets = release_info.get('assets', [])
                self.log_update('info', f"릴리스 에셋 수: {len(assets)}")

                for i, asset in enumerate(assets):
                    self.log_update('info', f"에셋 {i+1}: {asset.get('name', 'Unknown')} ({asset.get('size', 0)} bytes)")

                update_asset = self.find_update_asset(assets, release_info)

                if not update_asset:
                    self.log_update('warning', "다운로드 가능한 업데이트 파일을 찾을 수 없습니다.")
                    return False, None

                self.log_update('info', f"선택된 업데이트 파일: {update_asset.get('name', 'Unknown')}")

                # 업데이트 정보 구성
                update_info = {
                    'version': latest_version,
                    'tag_name': tag_name,
                    'name': release_name,
                    'changelog': release_body,
                    'download_url': update_asset.get('browser_download_url'),
                    'file_size': update_asset.get('size', 0),
                    'file_name': update_asset.get('name'),
                    'published_at': release_info.get('published_at'),
                    'prerelease': release_info.get('prerelease', False)
                }

                self.log_update('info', f"업데이트 URL: {update_info['download_url']}")
                return True, update_info
            else:
                self.log_update('info', "이미 최신 버전입니다.")
                return False, None

        except Exception as e:
            self.log_update('error', f"GitHub 업데이트 확인 실패: {str(e)}")
            import traceback
            self.log_update('error', f"스택 트레이스: {traceback.format_exc()}")
            return False, None
    
    def show_update_dialog(self, update_info: Dict) -> bool:
        """
        업데이트 확인 대화상자 표시
        
        Args:
            update_info: 업데이트 정보
            
        Returns:
            bool: 사용자가 업데이트를 선택했는지 여부
        """
        try:
            version = update_info.get('version', 'Unknown')
            release_name = update_info.get('name', f'v{version}')
            changelog = update_info.get('changelog', '업데이트 내용이 없습니다.')
            file_name = update_info.get('file_name', 'update.zip')
            file_size = update_info.get('file_size', 0)
            published_at = update_info.get('published_at', '')
            is_prerelease = update_info.get('prerelease', False)
            
            # 파일 크기를 읽기 쉽게 변환
            size_text = ""
            if file_size > 0:
                if file_size > 1024 * 1024:  # MB
                    size_text = f" ({file_size / (1024 * 1024):.1f} MB)"
                elif file_size > 1024:  # KB
                    size_text = f" ({file_size / 1024:.1f} KB)"
                else:
                    size_text = f" ({file_size} bytes)"
            
            # 프리릴리스 표시
            prerelease_text = " (프리릴리스)" if is_prerelease else ""
            
            # 발행일 표시
            date_text = ""
            if published_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    date_text = f"\n발행일: {dt.strftime('%Y-%m-%d %H:%M')}"
                except:
                    pass
            
            message = f"""새로운 버전이 있습니다!

현재 버전: {self.current_version}
최신 버전: {version}{prerelease_text}
릴리스명: {release_name}
파일명: {file_name}{size_text}{date_text}

변경사항:
{changelog}

지금 업데이트하시겠습니까?"""
            
            reply = QMessageBox.question(
                None,
                '업데이트 알림',
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            return reply == QMessageBox.Yes
            
        except Exception as e:
            self.logger.error(f"업데이트 대화상자 표시 실패: {str(e)}")
            return False
    
    def create_backup(self) -> bool:
        """
        현재 프로그램 백업 생성

        Returns:
            bool: 백업 성공 여부
        """
        if not self.backup_enabled:
            self.log_update('info', "백업 기능이 비활성화되어 있습니다. 백업을 건너뜁니다.")
            return True

        try:
            self.log_update('info', f"백업 생성 시작: {self.project_root}")

            # 백업 디렉토리 생성
            self.backup_dir.mkdir(exist_ok=True)
            self.log_update('info', f"백업 디렉토리: {self.backup_dir}")

            # 백업 파일명 (현재 버전 + 타임스탬프)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_v{self.current_version}_{timestamp}.zip"
            backup_path = self.backup_dir / backup_filename
            self.log_update('info', f"백업 파일명: {backup_filename}")

            # 백업 대상 제외 목록
            exclude_patterns = {
                '__pycache__',
                '.git',
                '.DS_Store',
                'logs',
                'backups',
                'dist',
                'build',
                '.claude'
            }
            self.log_update('info', f"제외 패턴: {', '.join(exclude_patterns)}")

            # 백업할 파일 수 계산
            total_files = 0
            total_size = 0
            for root, dirs, files in os.walk(self.project_root):
                dirs[:] = [d for d in dirs if d not in exclude_patterns]
                for file in files:
                    if not any(pattern in file for pattern in exclude_patterns):
                        file_path = Path(root) / file
                        if file_path.exists():
                            total_files += 1
                            total_size += file_path.stat().st_size

            self.log_update('info', f"백업 대상: {total_files}개 파일, 총 {total_size / (1024*1024):.2f} MB")

            # 백업 ZIP 파일 생성
            backed_up_files = 0
            backed_up_size = 0

            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                for root, dirs, files in os.walk(self.project_root):
                    # 제외할 디렉토리 건너뛰기
                    dirs[:] = [d for d in dirs if d not in exclude_patterns]

                    for file in files:
                        if not any(pattern in file for pattern in exclude_patterns):
                            file_path = Path(root) / file
                            try:
                                if file_path.exists():
                                    arcname = file_path.relative_to(self.project_root)
                                    backup_zip.write(file_path, arcname)
                                    backed_up_files += 1
                                    backed_up_size += file_path.stat().st_size

                                    # 진행 상황 로그 (100개마다)
                                    if backed_up_files % 100 == 0:
                                        progress = (backed_up_files / total_files) * 100
                                        self.log_update('debug', f"백업 진행: {backed_up_files}/{total_files} ({progress:.1f}%)")

                            except Exception as file_error:
                                self.log_update('warning', f"파일 백업 실패: {file_path} - {file_error}")

            # 백업 완료 정보
            final_backup_size = os.path.getsize(backup_path)
            compression_ratio = (1 - final_backup_size / backed_up_size) * 100 if backed_up_size > 0 else 0

            self.log_update('info', f"백업 생성 완료: {backup_path}")
            self.log_update('info', f"백업된 파일: {backed_up_files}/{total_files}개")
            self.log_update('info', f"원본 크기: {backed_up_size / (1024*1024):.2f} MB")
            self.log_update('info', f"압축 크기: {final_backup_size / (1024*1024):.2f} MB")
            self.log_update('info', f"압축률: {compression_ratio:.1f}%")

            return True

        except Exception as e:
            self.log_update('error', f"백업 생성 실패: {str(e)}")
            import traceback
            self.log_update('error', f"백업 오류 트레이스: {traceback.format_exc()}")
            return False
    
    def download_update(self, update_info: Dict, parent_widget=None) -> Tuple[bool, Optional[str]]:
        """
        업데이트 파일 다운로드
        
        Args:
            update_info: 업데이트 정보
            parent_widget: 부모 위젯 (진행 대화상자용)
            
        Returns:
            Tuple[bool, Optional[str]]: (성공 여부, 다운로드된 파일 경로)
        """
        try:
            download_url = update_info.get('download_url')
            self.log_update('info', f"다운로드 URL: {download_url}")

            if not download_url:
                self.log_update('error', "다운로드 URL이 없습니다")
                return False, None

            # 다운로드 파일 경로
            update_filename = f"update_v{update_info.get('version', 'unknown')}.zip"
            download_path = self.temp_dir / update_filename
            self.log_update('info', f"다운로드 경로: {download_path}")
            
            # 진행 대화상자 생성
            progress_dialog = QProgressDialog(
                "업데이트 다운로드 중...",
                "취소",
                0, 100,
                parent_widget
            )
            progress_dialog.setWindowTitle("업데이트")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            
            # 다운로드 스레드 생성 및 시작
            self.log_update('info', "다운로드 스레드 생성 중...")
            download_thread = UpdateDownloadThread(download_url, str(download_path))

            # 시그널 연결
            download_thread.progress.connect(progress_dialog.setValue)
            download_thread.status.connect(progress_dialog.setLabelText)

            result = [False, None, False]  # [성공여부, 경로, 시그널_수신됨] 결과 저장용

            def on_download_finished(success: bool, message: str):
                self.log_update('info', f"다운로드 완료 시그널 수신: success={success}, message={message}")
                result[0] = success
                result[1] = str(download_path) if success else None
                result[2] = True  # 시그널이 수신되었음을 표시
                progress_dialog.close()

                if not success:
                    self.log_update('error', f"다운로드 실패: {message}")
                    QMessageBox.critical(
                        parent_widget,
                        "다운로드 실패",
                        f"업데이트 다운로드에 실패했습니다:\n{message}"
                    )

            download_thread.finished.connect(on_download_finished)
            self.log_update('info', "다운로드 스레드 시작...")
            download_thread.start()

            # 다운로드 완료까지 대기
            self.log_update('info', "다운로드 대기 중...")
            while download_thread.isRunning():
                QApplication.processEvents()
                time.sleep(0.01)  # 짧은 대기로 CPU 사용량 감소

                if progress_dialog.wasCanceled():
                    self.log_update('info', "사용자가 다운로드를 취소했습니다")
                    download_thread.quit()
                    download_thread.wait()
                    return False, None

            self.log_update('info', f"스레드 완료 후 즉시 상태: success={result[0]}, path={result[1]}, signal_received={result[2]}")

            # 스레드가 끝났지만 시그널 처리를 위해 추가 대기
            self.log_update('info', "스레드 종료됨. 시그널 처리 대기 중...")

            # 시그널 처리를 위해 충분한 시간 대기
            for i in range(30):  # 최대 3초 대기
                QApplication.processEvents()
                time.sleep(0.1)

                # 시그널이 수신되었는지 확인
                if result[2]:  # 시그널 수신 플래그
                    self.log_update('info', f"시그널 처리 완료 (반복 {i+1}): success={result[0]}, path={result[1]}")
                    break

                # 진행률 업데이트
                if i % 5 == 0:
                    self.log_update('debug', f"시그널 대기 중... ({i+1}/30): result={result}")
            else:
                self.log_update('warning', f"시그널 처리 타임아웃. 최종 상태: {result}")

                # 타임아웃이 발생해도 파일이 실제로 다운로드되었는지 확인
                if os.path.exists(download_path):
                    self.log_update('info', f"타임아웃이지만 파일은 존재함: {download_path}")
                    result[0] = True
                    result[1] = str(download_path)
                    result[2] = True

            # 실제 파일이 존재하는지 확인
            if result[0] and result[1] and os.path.exists(result[1]):
                self.log_update('info', f"다운로드 성공 확인: 파일 존재함 - {result[1]}")
                return True, result[1]
            elif result[0]:
                # 스레드는 성공했다고 하지만 파일이 없는 경우
                self.log_update('warning', f"스레드는 성공이라고 했지만 파일이 없음: {result[1]}")
                if os.path.exists(download_path):
                    self.log_update('info', f"원래 경로에 파일 존재: {download_path}")
                    return True, str(download_path)
                else:
                    self.log_update('error', "다운로드된 파일을 찾을 수 없음")
                    return False, None
            else:
                self.log_update('info', f"다운로드 결과: success={result[0]}, path={result[1]}")
                return result[0], result[1]
            
        except Exception as e:
            self.log_update('error', f"업데이트 다운로드 예외 발생: {str(e)}")
            import traceback
            self.log_update('error', f"스택 트레이스: {traceback.format_exc()}")
            return False, None
    
    def install_update(self, update_zip_path: str) -> bool:
        """
        업데이트 설치 (exe 파일의 경우 배치 스크립트 사용)

        Args:
            update_zip_path: 다운로드된 업데이트 ZIP 파일 경로

        Returns:
            bool: 설치 성공 여부
        """
        try:
            self.log_update('info', f"업데이트 설치 시작: {update_zip_path}")

            # ZIP 파일 압축 해제
            extract_path = self.temp_dir / 'update_files'
            extract_path.mkdir(exist_ok=True)

            self.log_update('info', f"ZIP 파일 압축 해제 중: {update_zip_path} -> {extract_path}")
            with zipfile.ZipFile(update_zip_path, 'r') as zip_file:
                file_list = zip_file.namelist()
                self.log_update('info', f"ZIP 파일 내용: {len(file_list)}개 파일")
                for i, filename in enumerate(file_list[:10]):  # 처음 10개만 로그
                    self.log_update('debug', f"ZIP 파일 {i+1}: {filename}")
                if len(file_list) > 10:
                    self.log_update('debug', f"... 및 {len(file_list) - 10}개 더")

                zip_file.extractall(extract_path)

            self.log_update('info', "압축 해제 완료. 파일 구조 분석 중...")

            # 압축 해제된 구조 확인
            source_root = extract_path
            extracted_items = list(extract_path.iterdir())

            self.log_update('info', f"추출된 아이템 수: {len(extracted_items)}")
            for item in extracted_items:
                self.log_update('debug', f"추출된 항목: {item.name} ({'디렉토리' if item.is_dir() else '파일'})")

            # 소스 루트 디렉토리 찾기 (여러 패턴 시도)
            possible_patterns = [
                'NaverBlogAutomation',
                'python_naver_blog',
                'naver',
                'blog'
            ]

            for item in extracted_items:
                if item.is_dir():
                    item_name_lower = item.name.lower()
                    for pattern in possible_patterns:
                        if pattern.lower() in item_name_lower:
                            source_root = item
                            self.log_update('info', f"소스 루트 디렉토리 발견: {source_root}")
                            break
                    if source_root != extract_path:
                        break

            # 소스 루트가 여전히 extract_path라면, 첫 번째 디렉토리를 사용
            if source_root == extract_path and extracted_items:
                for item in extracted_items:
                    if item.is_dir():
                        source_root = item
                        self.log_update('info', f"첫 번째 디렉토리를 소스 루트로 사용: {source_root}")
                        break

            self.log_update('info', f"최종 소스 루트: {source_root}")

            # 소스 루트 내용 확인
            if source_root.exists() and source_root.is_dir():
                source_files = list(source_root.iterdir())
                self.log_update('info', f"소스 루트 내 파일/폴더 수: {len(source_files)}")
                for i, item in enumerate(source_files[:10]):  # 처음 10개만 로그
                    self.log_update('debug', f"소스 파일 {i+1}: {item.name}")
                if len(source_files) > 10:
                    self.log_update('debug', f"... 및 {len(source_files) - 10}개 더")
            else:
                self.log_update('error', f"소스 루트가 유효하지 않음: {source_root}")
                return False

            # exe 파일로 실행 중인 경우 배치 스크립트를 사용한 지연 업데이트
            if getattr(sys, 'frozen', False):
                # 배치 스크립트만 생성하고, 실제 실행은 restart_application에서 처리
                self.batch_script_path = self._create_update_script(source_root)
                return self.batch_script_path is not None
            else:
                return self._install_script_update(source_root)

        except Exception as e:
            self.logger.error(f"업데이트 설치 실패: {str(e)}")
            return False

    def _initialize_preserve_targets(self):
        """업데이트 시 보존할 파일/디렉토리 집합 초기화"""
        defaults = {'config/settings.json', 'backups', 'logs', '.git'}
        combined = set()
        combined.update(defaults)
        combined.update({str(entry) for entry in self.user_preserve_paths if entry})

        self.preserve_files = set()
        self.preserve_dirs = set()

        for raw_entry in combined:
            raw_entry = str(raw_entry).strip().replace('\\', '\\')
            if not raw_entry:
                continue

            entry_path = Path(raw_entry)

            if entry_path.is_absolute():
                try:
                    entry_path = entry_path.relative_to(self.project_root)
                except ValueError:
                    self.log_update('warning', f'보존 경로 무시: {raw_entry}')
                    continue

            if str(entry_path).startswith('..'):
                self.log_update('warning', f'상위 경로로 향하는 보존 경로 무시: {raw_entry}')
                continue

            if entry_path.suffix:
                self.preserve_files.add(entry_path)
            else:
                self.preserve_dirs.add(entry_path)

        self.preserve_dirs.add(Path('backups'))

        self.log_update('info', f'보존 파일: {[str(p) for p in sorted(self.preserve_files)]}')
        self.log_update('info', f'보존 디렉토리: {[str(p) for p in sorted(self.preserve_dirs)]}')

    def _should_preserve_file(self, rel_path: Path) -> bool:
        """상대 경로 기준으로 파일 보존 여부 판단"""
        rel_path = rel_path if rel_path != Path('.') else Path('.')
        if rel_path in self.preserve_files:
            return True
        for preserve_dir in self.preserve_dirs:
            if rel_path.is_relative_to(preserve_dir):
                return True
        return False

    def _should_preserve_dir(self, rel_dir: Path) -> bool:
        """상대 경로 기준으로 디렉토리 보존 여부 판단"""
        if rel_dir in (Path('.'), Path('')):
            return False
        if rel_dir in self.preserve_dirs:
            return True
        for preserve_file in self.preserve_files:
            if preserve_file.is_relative_to(rel_dir):
                return True
        for preserve_dir in self.preserve_dirs:
            if preserve_dir.is_relative_to(rel_dir):
                return True
        return False

    def _clean_project_root(self):
        """보존 대상을 제외하고 프로젝트 루트를 정리"""
        self.log_update('info', '기존 파일 정리 시작 (보존 대상 제외)')
        for root, dirs, files in os.walk(self.project_root, topdown=False):
            current_dir = Path(root)
            rel_dir = current_dir.relative_to(self.project_root) if current_dir != self.project_root else Path('.')

            for file_name in files:
                rel_path = Path(file_name) if rel_dir == Path('.') else rel_dir / file_name
                if self._should_preserve_file(rel_path):
                    continue
                target_file = current_dir / file_name
                try:
                    target_file.unlink()
                    self.log_update('debug', f'기존 파일 삭제: {rel_path}')
                except Exception as cleanup_error:
                    self.log_update('warning', f'파일 삭제 실패 {rel_path}: {cleanup_error}')

            if rel_dir in (Path('.'), Path('')):
                continue
            if self._should_preserve_dir(rel_dir):
                continue

            try:
                current_dir.rmdir()
                self.log_update('debug', f'비어 있는 디렉토리 삭제: {rel_dir}')
            except OSError:
                pass

    def _create_update_script(self, source_root: Path) -> str:
        """exe 파일 업데이트용 스크립트 생성"""
        try:
            import platform

            self.log_update('info', "업데이트 배치 스크립트 생성 시작")

            current_exe_dir = Path(os.path.dirname(sys.executable))
            current_exe_path = Path(sys.executable)

            self.log_update('info', f"현재 실행 중인 exe: {current_exe_path}")
            self.log_update('info', f"exe 디렉토리: {current_exe_dir}")
            self.log_update('info', f"소스 루트: {source_root}")

            if current_exe_path.exists():
                exe_size = current_exe_path.stat().st_size
                exe_mtime = current_exe_path.stat().st_mtime
                self.log_update('info', f"현재 exe 크기: {exe_size} bytes, 수정시간: {exe_mtime}")

            windows_preserve_files = [str(path).replace('/', '\\') for path in sorted(self.preserve_files)]
            windows_preserve_dirs = [str(path).replace('/', '\\') for path in sorted(self.preserve_dirs)]

            robocopy_file_parts = ['update_installer.bat', 'update_installer.sh']
            for item in windows_preserve_files:
                robocopy_file_parts.extend([item, f'%TARGET_DIR%\\{item}'])
            robocopy_file_parts = list(dict.fromkeys(robocopy_file_parts))
            robocopy_exclude_files = ''
            if robocopy_file_parts:
                robocopy_exclude_files = '/XF ' + ' '.join(f'"{part}"' for part in robocopy_file_parts)

            robocopy_exclude_dirs = ''
            if windows_preserve_dirs:
                dir_parts = []
                for directory in windows_preserve_dirs:
                    dir_parts.extend([
                        f'%TARGET_DIR%\\{directory}',
                        f'%ACTUAL_SOURCE%\\{directory}',
                        directory
                    ])
                dir_parts = list(dict.fromkeys(dir_parts))
                if dir_parts:
                    robocopy_exclude_dirs = '/XD ' + ' '.join(f'"{part}"' for part in dir_parts)

            preserve_backup_block = ''
            if windows_preserve_files:
                preserve_backup_block = 'for %%F in (' + ' '.join(f'"{item}"' for item in windows_preserve_files) + ') do (\n'
                preserve_backup_block += '    if not "%%~F"=="" if exist "%TARGET_DIR%\\%%~F" (\n'
                preserve_backup_block += '        if not exist "%PRESERVE_BACKUP%\\%%~dpF" mkdir "%PRESERVE_BACKUP%\\%%~dpF" >nul 2>&1\n'
                preserve_backup_block += '        copy "%TARGET_DIR%\\%%~F" "%PRESERVE_BACKUP%\\%%~F" >nul 2>&1\n'
                preserve_backup_block += '    )\n'
                preserve_backup_block += ')\n'

            restore_backup_block = ''
            if windows_preserve_files:
                restore_backup_block = 'for %%F in (' + ' '.join(f'"{item}"' for item in windows_preserve_files) + ') do (\n'
                restore_backup_block += '    if exist "%PRESERVE_BACKUP%\\%%~F" (\n'
                restore_backup_block += '        if not exist "%TARGET_DIR%\\%%~dpF" mkdir "%TARGET_DIR%\\%%~dpF" >nul 2>&1\n'
                restore_backup_block += '        copy "%PRESERVE_BACKUP%\\%%~F" "%TARGET_DIR%\\%%~F" >nul 2>&1\n'
                restore_backup_block += '    )\n'
                restore_backup_block += ')\n'

            robocopy_exclude_dirs_line = f'set "ROBOCOPY_EXCLUDE_DIRS={robocopy_exclude_dirs}"' if robocopy_exclude_dirs else 'set "ROBOCOPY_EXCLUDE_DIRS="'
            robocopy_exclude_files_line = f'set "ROBOCOPY_EXCLUDE_FILES={robocopy_exclude_files}"' if robocopy_exclude_files else 'set "ROBOCOPY_EXCLUDE_FILES="'

            platform_name = platform.system().lower()
            self.log_update('info', f"플랫폼: {platform_name}")

            if platform_name == 'windows':
                batch_script = current_exe_dir / 'update_installer.bat'
                script_lines = [
                    '@echo off',
                    'setlocal enabledelayedexpansion',
                    'chcp 65001 >nul',
                    '',
                    f'set "TARGET_DIR={current_exe_dir}"',
                    f'set "ACTUAL_SOURCE={source_root}"',
                    f'set "TEMP_ROOT={self.temp_dir}"',
                    'set "PRESERVE_BACKUP=%TARGET_DIR%\\preserve_backup"',
                    '',
                    'echo ========================================',
                    'echo 네이버 블로그 자동화 프로그램 업데이트',
                    'echo ========================================',
                    'echo 대상 경로: %TARGET_DIR%',
                    'echo 소스 경로: %ACTUAL_SOURCE%',
                    'echo.',
                    'if not exist "%ACTUAL_SOURCE%" (',
                    '    echo 업데이트 소스 경로를 찾을 수 없습니다.',
                    '    goto error_exit',
                    ')',
                    '',
                    'if exist "%PRESERVE_BACKUP%" rmdir /s /q "%PRESERVE_BACKUP%"',
                    'mkdir "%PRESERVE_BACKUP%" >nul 2>&1',
                    '',
                ]
                if preserve_backup_block:
                    script_lines.append(preserve_backup_block.rstrip('\n'))
                    script_lines.append('')
                script_lines.extend([
                    'if exist "%TARGET_DIR%\\NaverBlogAutomation.exe" (',
                    '    copy "%TARGET_DIR%\\NaverBlogAutomation.exe" "%PRESERVE_BACKUP%\\NaverBlogAutomation.exe.backup" >nul 2>&1',
                    ')',
                    '',
                    'set "ROBOCOPY_OPTS=/MIR /R:2 /W:2 /NFL /NDL /NP /NJH /NJS"',
                    robocopy_exclude_dirs_line,
                    robocopy_exclude_files_line,
                    '',
                    'echo 새 파일 동기화 중... 잠시만 기다려주세요.',
                    'robocopy "%ACTUAL_SOURCE%" "%TARGET_DIR%" %ROBOCOPY_OPTS% %ROBOCOPY_EXCLUDE_DIRS% %ROBOCOPY_EXCLUDE_FILES%',
                    'set "ROBOCOPY_RESULT=%ERRORLEVEL%"',
                    '',
                    'if %ROBOCOPY_RESULT% GEQ 8 goto restore_backup',
                    'echo 업데이트 동기화 완료 (코드: %ROBOCOPY_RESULT%)',
                    '',
                    'if exist "%TEMP_ROOT%" rmdir /s /q "%TEMP_ROOT%" >nul 2>&1',
                    'if exist "%PRESERVE_BACKUP%" rmdir /s /q "%PRESERVE_BACKUP%" >nul 2>&1',
                    '',
                    'cd /d "%TARGET_DIR%"',
                    'start "" "%TARGET_DIR%\\NaverBlogAutomation.exe"',
                    'del "%~f0" >nul 2>&1',
                    'exit',
                    '',
                    ':restore_backup',
                    'echo 업데이트 중 오류가 발생했습니다. 백업을 복원합니다.',
                    'if exist "%PRESERVE_BACKUP%\\NaverBlogAutomation.exe.backup" (',
                    '    copy "%PRESERVE_BACKUP%\\NaverBlogAutomation.exe.backup" "%TARGET_DIR%\\NaverBlogAutomation.exe" >nul 2>&1',
                    ')',
                ])
                if restore_backup_block:
                    script_lines.append(restore_backup_block.rstrip('\n'))
                script_lines.extend([
                    'if exist "%PRESERVE_BACKUP%" rmdir /s /q "%PRESERVE_BACKUP%" >nul 2>&1',
                    'start "" "%TARGET_DIR%\\NaverBlogAutomation.exe"',
                    'pause',
                    'exit',
                    '',
                    ':error_exit',
                    'echo 업데이트 스크립트를 종료합니다.',
                    'pause',
                    'exit',
                ])
                script_content = '\n'.join(script_lines)
            else:
                batch_script = current_exe_dir / 'update_installer.sh'
                preserve_files_bash = ' '.join(f'"{str(path)}"' for path in sorted(self.preserve_files))
                preserve_dirs_bash = ' '.join(f'"{str(path)}"' for path in sorted(self.preserve_dirs))
                script_content = f'''#!/bin/bash
set -e
TARGET_DIR="{current_exe_dir}"
ACTUAL_SOURCE="{source_root}"
TEMP_ROOT="{self.temp_dir}"
PRESERVE_BACKUP="$TARGET_DIR/preserve_backup"

echo "========================================"
echo "네이버 블로그 자동화 프로그램 업데이트"
echo "========================================"
echo "대상 경로: $TARGET_DIR"
echo "소스 경로: $ACTUAL_SOURCE"
echo
if [ ! -d "$ACTUAL_SOURCE" ]; then
    echo "업데이트 소스 경로를 찾을 수 없습니다."
    exit 1
fi

rm -rf "$PRESERVE_BACKUP"
mkdir -p "$PRESERVE_BACKUP"

for file in {preserve_files_bash if preserve_files_bash else '""'}; do
    if [ -n "$file" ] && [ -f "$TARGET_DIR/$file" ]; then
        mkdir -p "$PRESERVE_BACKUP/$(dirname "$file")"
        cp "$TARGET_DIR/$file" "$PRESERVE_BACKUP/$file"
    fi
done

RSYNC_OPTS=(--archive --delete --human-readable)
RSYNC_OPTS+=(--exclude=update_installer.bat --exclude=update_installer.sh)
for file in {preserve_files_bash if preserve_files_bash else '""'}; do
    if [ -n "$file" ]; then
        RSYNC_OPTS+=(--exclude="$file")
    fi
done
for dir in {preserve_dirs_bash if preserve_dirs_bash else '""'}; do
    if [ -n "$dir" ]; then
        RSYNC_OPTS+=(--exclude="$dir")
    fi
done

if ! rsync "${{RSYNC_OPTS[@]}}" "$ACTUAL_SOURCE/" "$TARGET_DIR/"; then
    echo "rsync 실행 중 오류가 발생했습니다. 백업을 복원합니다."
    for file in {preserve_files_bash if preserve_files_bash else '""'}; do
        if [ -n "$file" ] && [ -f "$PRESERVE_BACKUP/$file" ]; then
            mkdir -p "$TARGET_DIR/$(dirname "$file")"
            cp "$PRESERVE_BACKUP/$file" "$TARGET_DIR/$file"
        fi
    done
    exit 1
fi

rm -rf "$PRESERVE_BACKUP"
rm -rf "$TEMP_ROOT"
cd "$TARGET_DIR"
./NaverBlogAutomation &
rm "$0"
'''

            self.log_update('info', f"배치 스크립트 작성 중: {batch_script}")
            with open(batch_script, 'w', encoding='utf-8') as f:
                f.write(script_content)

            if platform_name != 'windows':
                os.chmod(batch_script, 0o755)
                self.log_update('info', "실행 권한 부여 완료")

            self.log_update('info', f"배치 스크립트 생성 완료: {batch_script}")
            self.log_update('info', "배치 스크립트 내용:")
            for i, line in enumerate(script_content.split('\n'), 1):
                if line.strip():
                    self.log_update('debug', f"  {i:2d}: {line}")

            # 배치 스크립트 실행 전까지 임시 파일 정리를 지연
            self.defer_cleanup = True

            return str(batch_script)

        except Exception as e:
            self.log_update('error', f"배치 스크립트 생성 실패: {str(e)}")
            import traceback
            self.log_update('error', f"스택 트레이스: {traceback.format_exc()}")
            return None

    def _install_script_update(self, source_root: Path) -> bool:
        """스크립트 버전 업데이트 (설정 보존 + 전체 교체)"""
        try:
            self.log_update('info', f"스크립트 업데이트 시작: 소스={source_root}, 대상={self.project_root}")

            preserve_backup_root = self.temp_dir / 'preserved_items'
            preserved_files = []

            for rel_path in sorted(self.preserve_files):
                original_file = self.project_root / rel_path
                if original_file.exists():
                    backup_path = preserve_backup_root / rel_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original_file, backup_path)
                    preserved_files.append(rel_path)
                    self.log_update('debug', f"보존 파일 백업: {rel_path}")

            self._clean_project_root()

            exclude_patterns = {'__pycache__', '.DS_Store', '.idea', '.vscode'}

            copied_files = 0
            failed_files = 0

            for root, dirs, files in os.walk(source_root):
                current_dir = Path(root)
                rel_dir = current_dir.relative_to(source_root)
                target_dir = self.project_root / rel_dir if rel_dir != Path('.') else self.project_root

                filtered_dirs = []
                for dir_name in dirs:
                    rel_subdir = (rel_dir / dir_name) if rel_dir != Path('.') else Path(dir_name)
                    if self._should_preserve_dir(rel_subdir):
                        self.log_update('debug', f"보존 디렉토리 건너뜀: {rel_subdir}")
                        continue
                    filtered_dirs.append(dir_name)
                dirs[:] = filtered_dirs

                target_dir.mkdir(parents=True, exist_ok=True)

                for file_name in files:
                    if file_name.endswith('.pyc'):
                        continue
                    if any(pattern in file_name for pattern in exclude_patterns):
                        continue

                    rel_path = (rel_dir / file_name) if rel_dir != Path('.') else Path(file_name)

                    if self._should_preserve_file(rel_path):
                        self.log_update('debug', f"보존 파일 건너뜀: {rel_path}")
                        continue

                    src_file = current_dir / file_name
                    dest_file = self.project_root / rel_path

                    try:
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)
                        copied_files += 1
                        self.log_update('debug', f"파일 복사 완료: {rel_path}")
                    except Exception as file_error:
                        failed_files += 1
                        self.log_update('error', f"파일 복사 실패: {rel_path} - {file_error}")

            for rel_path in preserved_files:
                backup_path = preserve_backup_root / rel_path
                if backup_path.exists():
                    dest_path = self.project_root / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, dest_path)
                    self.log_update('debug', f"보존 파일 복원: {rel_path}")

            self.log_update('info', f"업데이트 설치 완료: {copied_files}개 파일 복사, {failed_files}개 파일 실패")

            if failed_files > 0:
                self.log_update('warning', f"{failed_files}개 파일 복사에 실패했지만 업데이트를 계속 진행합니다.")

            self.log_update('info', "업데이트 검증 중...")
            verification_files = ['main.py', 'utils/updater.py', 'gui/main_window.py']
            verified_files = 0

            for verify_file in verification_files:
                verify_path = self.project_root / verify_file
                if verify_path.exists():
                    file_size = verify_path.stat().st_size
                    modify_time = verify_path.stat().st_mtime
                    self.log_update('debug', f"검증 파일 {verify_file}: 크기={file_size}, 수정시간={modify_time}")

                    try:
                        with open(verify_path, 'r', encoding='utf-8') as f:
                            content_preview = f.read(100).replace('\n', '\\n')
                            self.log_update('debug', f"파일 내용 미리보기 {verify_file}: {content_preview}...")
                    except Exception as read_error:
                        self.log_update('warning', f"파일 읽기 실패 {verify_file}: {read_error}")

                    verified_files += 1
                else:
                    self.log_update('warning', f"검증 파일 누락: {verify_file}")

            self.log_update('info', f"업데이트 검증 완료: {verified_files}/{len(verification_files)}개 파일 확인")

            if not getattr(sys, 'frozen', False):
                self.log_update('warning', "=" * 60)
                self.log_update('warning', "Python 스크립트 모드 업데이트 완료!")
                self.log_update('warning', "")
                self.log_update('warning', "중요: 파일은 교체되었지만 현재 실행 중인")
                self.log_update('warning', "메모리의 코드는 변경되지 않았습니다.")
                self.log_update('warning', "")
                self.log_update('warning', "변경사항을 적용하려면:")
                self.log_update('warning', "1. 현재 프로그램을 완전히 종료")
                self.log_update('warning', "2. run_app.py를 다시 실행")
                self.log_update('warning', "")
                self.log_update('warning', "이는 Python의 모듈 로딩 방식 때문입니다.")
                self.log_update('warning', "=" * 60)

            return copied_files > 0

        except Exception as e:
            self.log_update('error', f"스크립트 업데이트 실패: {str(e)}")
            import traceback
            self.log_update('error', f"스택 트레이스: {traceback.format_exc()}")
            return False

    def restart_application(self):
        """애플리케이션 재시작 (exe의 경우 배치 스크립트 실행)"""
        try:
            import platform

            self.log_update('info', "애플리케이션 재시작 중...")

            if getattr(sys, 'frozen', False) and hasattr(self, 'batch_script_path') and self.batch_script_path:
                # exe 파일이고 배치 스크립트가 생성된 경우
                self.log_update('info', f"배치 스크립트 실행: {self.batch_script_path}")

                if platform.system().lower() == 'windows':
                    # Windows: cmd를 통해 배치 스크립트 실행
                    subprocess.Popen(
                        ['cmd', '/c', self.batch_script_path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    # macOS/Linux: bash를 통해 셸 스크립트 실행
                    subprocess.Popen(['bash', self.batch_script_path])

                self.log_update('info', "배치 스크립트 실행 완료. 프로그램 종료 중...")

            elif getattr(sys, 'frozen', False):
                # exe 파일이지만 배치 스크립트가 없는 경우 (일반 재시작)
                self.log_update('info', "일반 exe 재시작")
                subprocess.Popen([sys.executable] + sys.argv[1:])
            else:
                # Python 스크립트인 경우
                self.log_update('info', "Python 스크립트 재시작")
                subprocess.Popen([sys.executable, sys.argv[0]] + sys.argv[1:])

            # 현재 프로세스 강제 종료
            self.log_update('info', "현재 프로세스 종료")
            QApplication.quit()

            # 조금 더 강제적으로 종료
            import time
            time.sleep(0.5)
            sys.exit(0)

        except Exception as e:
            self.log_update('error', f"애플리케이션 재시작 실패: {str(e)}")
            import traceback
            self.log_update('error', f"스택 트레이스: {traceback.format_exc()}")
    
    def cleanup_temp_files(self):
        """임시 파일 정리"""
        try:
            if getattr(self, "defer_cleanup", False):
                self.log_update('info', "임시 파일 정리를 배치 스크립트로 지연합니다.")
                return

            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.logger.debug("임시 파일 정리 완료")
        except Exception as e:
            self.logger.error(f"임시 파일 정리 실패: {str(e)}")


    def run_auto_update(self, parent_widget=None) -> bool:
        """
        전체 자동 업데이트 프로세스 실행

        Args:
            parent_widget: 부모 위젯

        Returns:
            bool: 업데이트 실행 여부
        """
        try:
            self.log_update('info', "=" * 80)
            self.log_update('info', "자동 업데이트 프로세스 시작")
            self.log_update('info', f"시작 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_update('info', f"현재 버전: {self.current_version}")
            self.log_update('info', f"프로젝트 루트: {self.project_root}")
            self.log_update('info', f"실행 모드: {'EXE' if getattr(sys, 'frozen', False) else 'Python 스크립트'}")
            self.log_update('info', "=" * 80)

            # 1. 업데이트 확인
            self.log_update('info', "1단계: 업데이트 확인")
            self.log_update('info', f"GitHub 레포지토리: {self.github_repo}")

            needs_update, update_info = self.check_for_updates()

            if not needs_update:
                self.log_update('info', "이미 최신 버전입니다. 업데이트가 필요하지 않습니다.")
                return False

            new_version = update_info.get('version', 'Unknown')
            file_size = update_info.get('file_size', 0)
            file_name = update_info.get('file_name', 'Unknown')

            self.log_update('info', f"새 버전 발견: {self.current_version} → {new_version}")
            self.log_update('info', f"업데이트 파일: {file_name}")
            self.log_update('info', f"파일 크기: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")

            # 2. 사용자에게 업데이트 확인
            self.log_update('info', "2단계: 사용자 확인 대화상자 표시")
            dialog_start = time.time()

            if not self.show_update_dialog(update_info):
                self.log_update('info', f"사용자가 업데이트를 취소했습니다. (대화상자 표시 시간: {time.time() - dialog_start:.1f}초)")
                return False

            self.log_update('info', f"사용자가 업데이트를 승인했습니다. (대화상자 표시 시간: {time.time() - dialog_start:.1f}초)")

            # 3. 백업 생성
            self.log_update('info', "3단계: 기존 파일 백업 생성")
            backup_start = time.time()

            if not self.create_backup():
                backup_time = time.time() - backup_start
                self.log_update('warning', f"백업 생성 실패 (소요 시간: {backup_time:.1f}초)")

                reply = QMessageBox.question(
                    parent_widget,
                    "백업 실패",
                    "백업 생성에 실패했습니다. 그래도 업데이트를 진행하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    self.log_update('info', "사용자가 백업 실패로 인해 업데이트를 취소했습니다.")
                    return False
                self.log_update('warning', "백업 없이 업데이트 진행")
            else:
                backup_time = time.time() - backup_start
                self.log_update('info', f"백업 생성 완료 (소요 시간: {backup_time:.1f}초)")

            # 4. 업데이트 다운로드
            self.log_update('info', "4단계: 업데이트 다운로드")
            download_start = time.time()
            download_url = update_info.get('download_url', '')
            self.log_update('info', f"다운로드 URL: {download_url}")

            success, download_path = self.download_update(update_info, parent_widget)
            download_time = time.time() - download_start

            if not success or not download_path:
                self.log_update('error', f"업데이트 다운로드 실패 (소요 시간: {download_time:.1f}초)")
                QMessageBox.critical(
                    parent_widget,
                    "다운로드 실패",
                    "업데이트 다운로드에 실패했습니다."
                )
                return False

            # 다운로드된 파일 정보 확인
            if os.path.exists(download_path):
                actual_file_size = os.path.getsize(download_path)
                self.log_update('info', f"다운로드 완료: {download_path}")
                self.log_update('info', f"실제 파일 크기: {actual_file_size} bytes ({actual_file_size / (1024*1024):.2f} MB)")
                self.log_update('info', f"다운로드 속도: {actual_file_size / (1024*1024) / download_time:.2f} MB/s")
                self.log_update('info', f"다운로드 소요 시간: {download_time:.1f}초")
            else:
                self.log_update('error', f"다운로드된 파일을 찾을 수 없음: {download_path}")
                return False

            # 5. 업데이트 설치
            self.log_update('info', "5단계: 업데이트 설치")
            install_start = time.time()

            if not self.install_update(download_path):
                install_time = time.time() - install_start
                self.log_update('error', f"업데이트 설치 실패 (소요 시간: {install_time:.1f}초)")
                QMessageBox.critical(
                    parent_widget,
                    "설치 실패",
                    "업데이트 설치에 실패했습니다."
                )
                return False

            install_time = time.time() - install_start
            self.log_update('info', f"업데이트 설치 완료 (소요 시간: {install_time:.1f}초)")

            # 6. 성공 메시지 및 재시작 확인
            self.log_update('info', "6단계: 애플리케이션 재시작 확인")
            total_time = time.time() - self.start_time if hasattr(self, 'start_time') else 0

            # Python 스크립트와 EXE에 따라 다른 메시지
            if getattr(sys, 'frozen', False):
                # EXE 모드
                restart_message = f"업데이트가 완료되었습니다! ({total_time:.1f}초 소요)\n\n변경사항을 적용하려면 프로그램을 재시작해야 합니다.\n\n지금 재시작하시겠습니까?"
            else:
                # Python 스크립트 모드
                restart_message = f"업데이트가 완료되었습니다! ({total_time:.1f}초 소요)\n\n⚠️ Python 스크립트 모드 안내:\n파일은 업데이트되었지만 현재 메모리의 코드는 변경되지 않습니다.\n\n변경사항을 확인하려면:\n1. 이 프로그램을 완전히 종료\n2. run_app.py를 다시 실행\n\n지금 프로그램을 종료하시겠습니까?"

            reply = QMessageBox.question(
                parent_widget,
                "업데이트 완료",
                restart_message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                self.log_update('info', "사용자가 재시작을 선택했습니다.")
                self.log_update('info', "임시 파일 정리 중...")
                self.cleanup_temp_files()
                self.log_update('info', "애플리케이션 재시작 중...")
                self.restart_application()
            else:
                self.log_update('info', "사용자가 재시작을 연기했습니다.")

            final_time = time.time() - (self.start_time if hasattr(self, 'start_time') else 0)
            self.log_update('info', "=" * 80)
            self.log_update('info', f"업데이트 프로세스 완료! 총 소요 시간: {final_time:.1f}초")
            self.log_update('info', f"성공적으로 {self.current_version} → {new_version}로 업데이트됨")
            self.log_update('info', "=" * 80)
            return True

        except Exception as e:
            error_time = time.time() - (self.start_time if hasattr(self, 'start_time') else 0)
            self.log_update('error', "=" * 80)
            self.log_update('error', f"자동 업데이트 실패 (실행 시간: {error_time:.1f}초)")
            self.log_update('error', f"오류 메시지: {str(e)}")

            import traceback
            stack_trace = traceback.format_exc()
            self.log_update('error', "스택 트레이스:")
            for i, line in enumerate(stack_trace.split('\n'), 1):
                if line.strip():
                    self.log_update('error', f"  {i:3d}: {line}")
            self.log_update('error', "=" * 80)

            QMessageBox.critical(
                parent_widget,
                "업데이트 오류",
                f"업데이트 중 오류가 발생했습니다:\n{str(e)}"
            )
            return False

        finally:
            # 시작 시간 기록 (다음 호출을 위해)
            if not hasattr(self, 'start_time'):
                self.start_time = time.time()

            self.cleanup_temp_files()
            self.log_update('info', f"정리 작업 완료: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_update('info', "=" * 80)

# 호환성을 위한 별칭
AutoUpdater = GitHubReleaseUpdater