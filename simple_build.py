#!/usr/bin/env python3
"""PyInstaller helper script without Firebase packaging."""

import os
import subprocess
import sys
from pathlib import Path


def build_executable() -> bool:
    """Run PyInstaller with the minimal options needed for this project."""
    print("Building executable with PyInstaller...")

    cmd = [
        "pyinstaller",
        "--onedir",
        "--windowed",
        "--name=NaverBlogAutomation",
        "--add-data=config:config",
        "--add-data=data:data",
        "--add-data=image:image",
        "--hidden-import=selenium",
        "--hidden-import=webdriver_manager",
        "--hidden-import=PyQt5",
        "--hidden-import=google.generativeai",
        "--hidden-import=automation",
        "--hidden-import=utils",
        "--hidden-import=gui",
        "--clean",
        "main.py",
    ]

    print("Command:", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Build failed: {exc}")
        return False

    dist_path = os.path.join("dist", "NaverBlogAutomation")
    print(f"Build succeeded. Check '{dist_path}' for the output.")

    # Rename Windows executable to Korean name
    windows_exe = Path(dist_path) / "NaverBlogAutomation.exe"
    korean_exe = Path(dist_path) / "자동화폭격기블로그자동화.exe"
    if windows_exe.exists():
        windows_exe.rename(korean_exe)
        print(f"Renamed executable to {korean_exe.name}")

    return True


if __name__ == "__main__":
    success = build_executable()
    if not success:
        sys.exit(1)
