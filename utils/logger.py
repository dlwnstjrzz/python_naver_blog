import logging
import os
from datetime import datetime

def setup_logger():
    """로거 설정"""
    # logs 디렉터리 생성
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 파일명 (날짜별)
    log_filename = f"naver_blog_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # 로거 설정
    logger = logging.getLogger('naver_blog_automation')
    logger.setLevel(logging.INFO)
    
    # 핸들러가 이미 있으면 제거
    if logger.handlers:
        logger.handlers.clear()
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger