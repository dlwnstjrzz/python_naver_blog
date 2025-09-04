# 네이버 블로그 서로이웃 자동화 프로그램

Material Design을 적용한 네이버 블로그 서로이웃 자동화 프로그램입니다.

## 📋 프로젝트 상태

### ✅ 완료된 기능 (1-3단계)

- [x] **프로젝트 구조 및 환경 설정**

  - Python 가상환경, 필수 라이브러리 목록
  - 모듈화된 디렉터리 구조
  - 로깅 시스템 및 설정 관리자

- [x] **Material Design GUI 인터페이스**

  - 2단계 위저드 형식의 사용자 인터페이스
  - Material Design 색상 팔레트 및 타이포그래피
  - 카드 기반 레이아웃, 호버 효과
  - 반응형 텍스트 필드, 버튼, 라디오 옵션

- [x] **네이버 로그인 모듈**
  - CAPTCHA 우회를 위한 클립보드 기반 로그인
  - 봇 감지 방지 옵션들 (User-Agent, webdriver 속성 제거)
  - 로그인 상태 확인 및 재시도 로직

### 🔄 진행 예정 (4-12단계)

- [ ] 블로그 검색 및 수집 모듈
- [ ] 서로이웃 추가 모듈
- [ ] 게시글 상호작용 모듈
- [ ] 댓글 작성 모듈
- [ ] 설정 관리 시스템
- [ ] 봇 감지 방지 로직
- [ ] 예외 처리 및 오류 복구
- [ ] 실행 파일 패키징
- [ ] 테스트 및 디버깅

## 🛠️ 개발 가이드라인

## 📁 프로젝트 구조

```
python_naver_blog/
├── main.py                 # 메인 실행 파일
├── requirements.txt        # 필수 라이브러리
├── .env.example           # 환경변수 템플릿
├── README.md              # 프로젝트 가이드
├── config/
│   └── settings.json      # 설정 파일
├── logs/                  # 로그 파일들
├── utils/                 # 유틸리티 모듈
│   ├── __init__.py
│   ├── logger.py         # 로깅 시스템
│   └── config_manager.py # 설정 관리자
├── gui/                  # GUI 모듈
│   ├── __init__.py
│   └── main_window.py    # 메인 윈도우
└── automation/           # 자동화 모듈
    ├── __init__.py
    ├── naver_login.py    # 네이버 로그인
    ├── blog_searcher.py  # 블로그 검색 (예정)
    ├── neighbor_adder.py # 서로이웃 추가 (예정)
    └── utils.py          # 자동화 유틸리티
```

## 🚀 다음 단계 개발 가이드

### 4단계: 블로그 검색 및 수집 모듈

```python
# automation/blog_searcher.py 생성 예정
class BlogSearcher:
    def search_by_keyword(self, keyword, count):
        """키워드로 블로그 검색"""
        pass

    def get_neighbor_blogs(self, base_blog_url, count):
        """이웃 커넥트로 블로그 수집"""
        pass
```

### 5단계: 서로이웃 추가 모듈

```python
# automation/neighbor_adder.py 생성 예정
class NeighborAdder:
    def add_neighbor(self, blog_info):
        """서로이웃 추가"""
        pass
```

### GUI 확장 시 Material Design 원칙

1. **새로운 2단계 화면** 생성 시:

   - `create_step2_widgets()` 함수에 Material Card 적용
   - 섹션별로 구분선과 헤더 추가
   - 입력 필드는 `create_material_text_field()` 사용

2. **새로운 컴포넌트** 추가 시:
   - Material Color Palette 사용
   - Typography Scale 준수
   - 일관된 패딩/마진 적용

## 🔧 개발 환경 설정

```bash
# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 필수 라이브러리 설치
pip install -r requirements.txt

# GUI 실행
python main.py

# 기본 테스트
python test_basic.py
```

## 📝 코딩 규칙

1. **함수명**: snake_case 사용
2. **클래스명**: PascalCase 사용
3. **상수**: UPPER_CASE 사용
4. **Material Design 컴포넌트**: `create_material_*` 접두사 사용
5. **문서화**: 모든 함수에 docstring 추가
6. **로깅**: 주요 동작에 대해 로그 기록
7. **예외 처리**: try-except 블록으로 안전한 코드 작성

이 가이드라인을 따라 나머지 기능들을 일관된 스타일로 개발하면 전문적이고 사용자 친화적인 프로그램이 완성될 것입니다.
