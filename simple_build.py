#!/usr/bin/env python3
"""PyInstaller helper script without Firebase packaging."""

import os
import subprocess
import sys


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
    return True


if __name__ == "__main__":
    success = build_executable()
    if not success:
        sys.exit(1)
