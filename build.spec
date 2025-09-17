# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['/Users/noah/personal/python_naver_blog'],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('data', 'data'),
        ('image', 'image'),
        ('image/logo.png', '.'),  # 루트 디렉토리에 복사
        ('image/logo.ico', '.'),  # 루트 디렉토리에 복사
    ],
    hiddenimports=[
        'selenium',
        'selenium.webdriver.common.service',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.firefox.service',
        'selenium.webdriver.edge.service',
        'selenium.webdriver.safari.service',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'webdriver_manager.firefox', 
        'webdriver_manager.microsoft',
        'google.generativeai',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'bs4',
        'lxml',
        'requests',
        'pyperclip',
        'dotenv',
        'PIL',
        'automation',
        'automation.blog_automation',
        'automation.buddy_manager',
        'automation.neighbor_connect',
        'automation.post_interaction',
        'automation.buddy_cancel_manager',
        'utils',
        'utils.config_manager',
        'utils.logger',
        'utils.extracted_ids_manager',
        'utils.ai_comment_generator',
        'gui',
        'gui.main_window',
        'gui.extracted_ids_window',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NaverBlogAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 애플리케이션이므로 콘솔 창 숨김
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='image/logo.ico',  # ICO 파일을 아이콘으로 사용
)