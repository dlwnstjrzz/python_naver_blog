#!/usr/bin/env python3
"""
네이버 블로그 자동화 도구 버전 정보
"""

__version__ = "1.0.6"
__version_info__ = (1, 0, 6)

# 버전 비교 함수
def compare_versions(version1: str, version2: str) -> int:
    """
    두 버전을 비교합니다.
    
    Args:
        version1: 첫 번째 버전 (예: "1.0.0")
        version2: 두 번째 버전 (예: "1.1.0")
    
    Returns:
        -1: version1 < version2
         0: version1 == version2
         1: version1 > version2
    """
    def parse_version(version: str):
        return tuple(map(int, version.split('.')))
    
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0

def get_version():
    """현재 버전을 반환합니다."""
    return __version__

def get_version_info():
    """현재 버전 정보를 튜플로 반환합니다."""
    return __version_info__