#!/usr/bin/env python3
"""
네이버 블로그 자동화 프로그램 빌드 스크립트
PyInstaller를 사용하여 exe 파일 생성
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def clean_build_folders():
    """이전 빌드 파일들 정리"""
    print(" 이전 빌드 파일들 정리 중...")
    
    folders_to_clean = ['build', 'dist', '__pycache__']
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"   {folder} 폴더 삭제 완료")
    
    # Python 캐시 파일들도 정리
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs[:]:
            if dir_name == '__pycache__':
                shutil.rmtree(os.path.join(root, dir_name))
                dirs.remove(dir_name)

def ensure_directories():
    """필요한 디렉토리들이 존재하는지 확인"""
    print(" 필요한 디렉토리들 확인 중...")
    
    required_dirs = ['config', 'data', 'logs']
    
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"   {dir_name} 디렉토리 생성 완료")
        else:
            print(f"   {dir_name} 디렉토리 존재 확인")

def build_executable():
    """PyInstaller를 사용하여 실행 파일 생성"""
    print(" PyInstaller로 실행 파일 빌드 중...")
    
    try:
        # spec 파일을 사용하여 빌드
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', 'build.spec']
        
        print(f"실행 명령어: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print(" 빌드 성공!")
        print("빌드 출력:")
        print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f" 빌드 실패: {e}")
        print("에러 출력:")
        print(e.stderr)
        return False

def copy_additional_files():
    """추가 필요 파일들을 dist 폴더로 복사"""
    print(" 추가 파일들 복사 중...")
    
    if not os.path.exists('dist/NaverBlogAutomation'):
        print(" dist 폴더가 존재하지 않습니다.")
        return False
    
    # README 파일 생성
    readme_content = """# 네이버 블로그 자동화 프로그램

## 사용법
1. 자동화폭격기블로그자동화.exe 실행
2. 네이버 아이디/비밀번호 입력
3. 검색 키워드 또는 이웃커넥트 블로그 URL 설정
4. 상세 설정 (공감/댓글 옵션 등) 조정
5. 자동화 시작

## 주의사항
- 네이버 정책을 준수하여 사용해주세요
- 과도한 사용은 계정 제재를 받을 수 있습니다
- 프로그램 사용으로 인한 모든 책임은 사용자에게 있습니다

## 문제 발생시
- logs 폴더의 로그 파일을 확인해주세요
- config 폴더의 설정 파일을 삭제하고 재설정해보세요
"""
    
    with open('dist/README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("   README.txt 생성 완료")
    
    return True

def main():
    """메인 빌드 프로세스"""
    print(" 네이버 블로그 자동화 프로그램 빌드 시작")
    print("=" * 50)
    
    # 1. 이전 빌드 파일들 정리
    clean_build_folders()
    
    # 2. 필요한 디렉토리들 확인
    ensure_directories()
    
    # 3. 실행 파일 빌드
    if not build_executable():
        print(" 빌드 실패")
        sys.exit(1)
    
    # 4. 추가 파일들 복사
    if not copy_additional_files():
        print(" 추가 파일 복사 실패")
        sys.exit(1)
    
    print("=" * 50)
    print(" 빌드 완료!")
    print(" dist 폴더에서 자동화폭격기블로그자동화.exe를 확인하세요")
    print(" 배포를 위해 dist 폴더 전체를 압축하여 배포할 수 있습니다")

if __name__ == "__main__":
    main()