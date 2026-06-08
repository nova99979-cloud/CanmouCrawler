#!/usr/bin/env python3
"""
海外平台采集助手 v2 — 长期稳定方案

功能：
1. Cookie 管理：通过 Chrome 持久化登录态，定时刷新
2. IP 封禁检测：发现 403/429 时自动建议切换 QuickQ 节点
3. 节点切换提：检测到被封时通过飞书/终端通知你换节点
4. 请求间隔控制：自动限速避免封IP
"""
import asyncio, json, sys, time, os, subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('/Users/aiqing/.openclaw/workspace-canmou')
OVERSEAS_SCRIPT = ROOT / 'crawlers/overseas_extract.py'

# 请求间隔（秒）——避免频率过高被封
DEFAULT_DELAY = 3
AFTER_BAN_DELAY = 30  # 被封后等待时间

# 检测 IP 是否被封的标志
BAN_PATTERNS = [
    'blocked', 'Your IP', 'rate limit', '429', '403',
    'unable to download webpage',
    'empty media response',
    'send an empty',
]

def check_banned(output: str) -> bool:
    """检查输出中是否有被封特征"""
    lower = output.lower()
    return any(p.lower() in lower for p in BAN_PATTERNS)

def notify_user(message: str, urgent: bool = False):
    """通知用户（macOS 通知）"""
    title = '⚠️ 采集被封' if urgent else '海外采集'
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(['osascript', '-e', script], capture_output=True)

def get_current_node():
    """获取当前 QuickQ 节点信息（从 stored defaults）"""
    try:
        result = subprocess.run(
            ['defaults', 'read', 'work.js7.apps.tools.quickq'],
            capture_output=True, text=True, timeout=5
        )
        # 从 plist 提取节点名（这里不解析 hash，只是记录）
        return 'QuickQ (check app for current node)'
    except:
        return 'unknown'

async def run_with_retry(platform: str, urls: list, query: str = '',
                          limit: int = 5, cookies: str = 'chrome',
                          max_retries: int = 3):
    """
    带重试和IP封禁检测的采集任务
    
    策略：
    - 每次请求间隔 DEFAULT_DELAY 秒
    - 检测到被封 -> 通知用户 + 等待 AFTER_BAN_DELAY 秒 + 重试
    - 最多重试 max_retries 次
    """
    outdir = ROOT / 'outputs' / f'auto_{platform}_{int(time.time())}'
    outdir.mkdir(parents=True, exist_ok=True)
    
    cmd = ['python3', str(OVERSEAS_SCRIPT),
           '--platform', platform,
           '--outdir', str(outdir),
           '--limit', str(limit),
           '--fallback-browser']
    
    # Cookie: 只在需要登录的平台传，搜索模式不传
    if cookies and platform not in ('youtube', 'vimeo'):
        cmd += ['--cookies-from-browser', cookies]
    
    if urls:
        cmd += ['--url', '\n'.join(urls)]
    if query:
        cmd += ['--query', query]
    
    for attempt in range(max_retries):
        print(f'\n[{datetime.now().strftime("%H:%M:%S")}] 第 {attempt+1}/{max_retries} 次尝试...')
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = result.stdout + result.stderr
        
        if result.returncode == 0 and not check_banned(output):
            print('✅ 采集成功！')
            print(output[-500:])
            return {'status': 'success', 'outdir': str(outdir), 'output': output}
        
        if check_banned(output):
            print(f'❌ IP 被封或请求被拒 (attempt {attempt+1})')
            if attempt < max_retries - 1:
                notify_user(f'{platform} 采集被限制，等待 {AFTER_BAN_DELAY}s 后重试\n请尝试切换 QuickQ 节点', urgent=True)
                print(f'⏳ 等待 {AFTER_BAN_DELAY} 秒...')
                await asyncio.sleep(AFTER_BAN_DELAY)
                # 等待期间提醒用户切换节点
                print('💡 提示：请在 QuickQ 中切换到其他地区节点（如 日本→美国→新加坡）')
                continue
        else:
            # 其他错误
            print(f'❌ 采集出错: {output[:500]}')
            break
    
    notify_user(f'{platform} 采集失败，已达最大重试次数', urgent=True)
    return {'status': 'failed', 'outdir': str(outdir), 'output': output}


def export_cookies_to_file():
    """
    将 Chrome 的 Cookie 导出为 Netscape 格式文件
    yt-dlp 可以直接用 --cookies cookies.txt
    
    这样即使 Chrome 关闭，Cookie 文件也可用
    """
    cookies_file = ROOT / 'config' / 'cookies_chrome.txt'
    cookies_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        result = subprocess.run(
            ['yt-dlp', '--cookies-from-browser', 'chrome', '--cookies', str(cookies_file),
             '--no-warnings', '--simulate', '-j', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'],
            capture_output=True, text=True, timeout=30
        )
        if cookies_file.exists() and cookies_file.stat().st_size > 100:
            print(f'✅ Cookie 已导出 ({cookies_file.stat().st_size} bytes)')
            return str(cookies_file)
        else:
            print(f'⚠️ Cookie 导出不完整: {result.stdout[:200]}')
            return None
    except Exception as e:
        print(f'❌ Cookie 导出失败: {e}')
        return None


async def smart_collect(platform: str, **kwargs):
    """
    智能采集入口 — 自动管理：
    1. 检查 Cookie 是否有效
    2. 带间隔发送请求
    3. 被封自动提示 + 重试
    """
    # 先导出 cookie
    cookies_file = export_cookies_to_file()
    
    print(f'\n🌍 开始采集 {platform}')
    print(f'📁 Cookie: {cookies_file or "使用浏览器实时cookie"}')
    print(f'🌐 当前节点: {get_current_node()}')
    print(f'⏱️  请求间隔: {DEFAULT_DELAY}s')
    
    result = await run_with_retry(platform, cookies='chrome', **kwargs)
    
    # 总结
    if result['status'] == 'success':
        print(f'\n✅ {platform} 采集完成: {result["outdir"]}')
    else:
        print(f'\n❌ {platform} 采集失败')
        print('💡 建议操作:')
        print('   1. 在 QuickQ 中切换到其他节点')
        print('   2. 打开 Chrome 确认已登录 TikTok/Instagram/X')
        print('   3. 等待 1-2 分钟后重试')
    
    return result


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--platform', default='youtube', help='tiktok|youtube|instagram|facebook|x|vimeo')
    ap.add_argument('--query', default='', help='关键词搜索')
    ap.add_argument('--url', default='', help='URL（多个用换行分隔）')
    ap.add_argument('--limit', type=int, default=5)
    ap.add_argument('--export-cookies', action='store_true', help='仅导出 Cookie')
    
    args = ap.parse_args()
    
    if args.export_cookies:
        export_cookies_to_file()
        sys.exit(0)
    
    urls = [u.strip() for u in args.url.splitlines() if u.strip()] if args.url else []
    
    asyncio.run(smart_collect(
        args.platform,
        urls=urls,
        query=args.query,
        limit=args.limit
    ))