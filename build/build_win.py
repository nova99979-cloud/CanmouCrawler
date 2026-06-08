#!/usr/bin/env python3
"""
Windows 安装包构建脚本

使用方法（在 Windows 上）：
  1. 安装 Python 3.11+
  2. pip install pyinstaller
  3. python build_win.py

输出：dist/参谋多平台采集台.exe
"""
import os, sys, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST = ROOT / 'dist'
BUILD = ROOT / 'build'

def build():
    print("🔧 开始构建 Windows 安装包...")
    
    # 安装依赖
    print("\n📦 安装 PyInstaller...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    
    # 清理旧构建
    if DIST.exists():
        shutil.rmtree(DIST)
    
    # PyInstaller 打包
    print("\n📦 打包 app_server.py + 所有依赖...")
    cmd = [
        'pyinstaller',
        '--onefile',           # 单 exe 文件
        '--name', '参谋多平台采集台',
        '--add-data', f'overseas_extract.py{os.pathsep}.',
        '--add-data', f'overseas_assistant.py{os.pathsep}.',
        '--hidden-import', 'patchright.async_api',
        '--hidden-import', 'patchright.sync_api',
        '--hidden-import', 'asyncio',
        '--hidden-import', 'json',
        '--hidden-import', 'http.server',
        '--hidden-import', 'urllib.parse',
        '--console',           # 显示控制台窗口，方便看日志
        'app_server.py'
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    
    # 复制 exe 到 dist
    print("\n✅ 构建完成！")
    exe = DIST / '参谋多平台采集台.exe'
    if exe.exists():
        print(f"  输出: {exe}")
        print(f"  大小: {exe.stat().st_size / 1024 / 1024:.1f} MB")
    
    # 生成使用说明
    readme = DIST / '使用说明.txt'
    readme.write_text(
        '参谋多平台采集台 - Windows 版\n'
        '==========================\n\n'
        '双击 "参谋多平台采集台.exe" 启动\n'
        '服务启动后会自动打开浏览器: http://127.0.0.1:8765\n\n'
        '注意：\n'
        '- 首次运行可能需要防火墙允许\n'
        '- 需要 yt-dlp 和 Chrome 配合使用\n'
        '- 关闭控制台窗口即可停止服务\n',
        encoding='utf-8'
    )
    
    print(f"\n📁 输出目录: {DIST}")
    for f in DIST.iterdir():
        print(f"  {f.name} ({f.stat().st_size / 1024:.1f} KB)")

if __name__ == '__main__':
    build()
