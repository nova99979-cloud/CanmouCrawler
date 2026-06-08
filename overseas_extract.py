#!/usr/bin/env python3
"""Overseas platform extractor with fallback: yt-dlp → browser rendering → OEmbed APIs.

Supports TikTok, YouTube, Instagram, Facebook, X/Twitter, Reddit, Vimeo, etc.
"""
import argparse, csv, json, subprocess, sys, time, asyncio, re
from pathlib import Path

ROOT = Path('/Users/aiqing/.openclaw/workspace-canmou')
YTDLP = 'yt-dlp'

# Try to import browser renderer
BROWSER_AVAILABLE = False
try:
    from patchright.async_api import async_playwright
    BROWSER_AVAILABLE = True
except ImportError:
    pass

SEARCH_PREFIX = {
    'youtube': 'ytsearch',
    'ytb': 'ytsearch',
    'tiktok': 'tiktoksearch',
    'tk': 'tiktoksearch',
}

OEMBED_PROVIDERS = {
    'youtube': 'https://www.youtube.com/oembed?url={url}&format=json',
}

async def browser_extract(url, timeout=25, cookies_from_browser=''):
    """Use Patchright headless to render page and extract meta."""
    if not BROWSER_AVAILABLE:
        return None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            # If cookies from browser requested, try to import them
            if cookies_from_browser:
                try:
                    await ctx.browser_context.cookies  # ensure context is ready
                    # Patchright doesn't directly support chrome cookie import,
                    # but we can set cookies manually from yt-dlp export
                except:
                    pass
            page = await ctx.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout*1000)
            await asyncio.sleep(3)
            title = await page.title()
            meta = await page.evaluate("""
                () => {
                    const metas = document.querySelectorAll('meta[property], meta[name]');
                    return Array.from(metas).map(m => ({
                        prop: m.getAttribute('property') || m.getAttribute('name'),
                        content: m.getAttribute('content')
                    })).filter(m => m.content);
                }
            """)
            body_text = await page.evaluate("() => document.body?.innerText?.substring(0, 3000) || ''")
            final_url = page.url
            await ctx.close()
            await browser.close()
            return {'title': title, 'meta': meta, 'body_text': body_text[:500], 'final_url': final_url}
    except Exception as e:
        return {'error': str(e)}


def run_ytdlp(target, args, use_cookies=True):
    """Run yt-dlp and return parsed JSON lines."""
    cmd = [YTDLP, target, '--ignore-errors', '--no-warnings',
           '--socket-timeout', str(args.socket_timeout),
           '--retries', str(args.retries),
           '--playlist-end', str(args.limit)]
    if use_cookies:
        if args.cookies_from_browser:
            cmd += ['--cookies-from-browser', args.cookies_from_browser]
        if args.cookies:
            cmd += ['--cookies', args.cookies]
    cmd += ['--simulate', '-j']
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=args.ytdlp_timeout)
    if out.returncode:
        return {'error': out.stdout.strip() or out.stderr.strip()}
    rows = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith('{'):
            try: rows.append(json.loads(line))
            except: pass
    return rows


def try_oembed(url):
    """Simple oembed API fetch for supported providers."""
    import httpx
    for provider, pattern in OEMBED_PROVIDERS.items():
        if provider in url.lower() or provider in url:
            oembed_url = pattern.format(url=url)
            try:
                r = httpx.get(oembed_url, follow_redirects=True, timeout=15,
                              headers={'Accept': 'application/json'})
                if r.status_code == 200 and r.text.strip().startswith('{'):
                    return json.loads(r.text)
            except:
                pass
    return None


async def extract_with_browser(url, args):
    """Try yt-dlp first, then oembed, then browser rendering."""
    # Step 1: try oembed API (fastest)
    oembed = try_oembed(url)
    if oembed:
        return {'method': 'oembed', 'data': oembed}

    # Step 2: try yt-dlp
    yt = run_ytdlp(url, args)
    if isinstance(yt, list):
        if len(yt) > 0:
            return {'method': 'yt-dlp', 'count': len(yt), 'data': yt}
        else:
            # yt-dlp ran but returned nothing (search found 0 results, etc.)
            # This is not a failure of yt-dlp itself, skip browser fallback
            return {'method': 'yt-dlp-empty', 'data': []}


    # Step 3: browser rendering (skip for search queries)
    if args.fallback_browser and not url.startswith('ytsearch') and not url.startswith('tiktoksearch'):
        browser = await browser_extract(url, cookies_from_browser=args.cookies_from_browser)
        if browser and 'error' not in browser:
            return {'method': 'browser', 'data': browser}

    # All failed
    return {'method': 'failed', 'yt_error': yt if isinstance(yt, dict) else None}


def build_targets(args):
    targets = []
    if args.url:
        targets += [x.strip() for x in args.url.splitlines() if x.strip()]
    if args.url_file:
        targets += [x.strip() for x in Path(args.url_file).read_text(encoding='utf-8').splitlines()
                    if x.strip() and not x.strip().startswith('#')]
    if args.query:
        prefix = SEARCH_PREFIX.get(args.platform.lower())
        if not prefix:
            raise SystemExit(f'Query search currently supported for youtube/tiktok, got platform={args.platform}')
        targets.append(f'{prefix}{args.limit}:{args.query}')
    return targets


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--platform', default='url', help='url|tiktok|tk|youtube|ytb|facebook|fb|instagram|ig|x|twitter|reddit|vimeo')
    ap.add_argument('--url', default='')
    ap.add_argument('--url-file', default='')
    ap.add_argument('--query', default='')
    ap.add_argument('--limit', type=int, default=10)
    ap.add_argument('--outdir', default='outputs/overseas_ytdlp')
    ap.add_argument('--download', action='store_true')
    ap.add_argument('--cookies-from-browser', default='')
    ap.add_argument('--cookies', default='')
    ap.add_argument('--dateafter', default='')
    ap.add_argument('--datebefore', default='')
    ap.add_argument('--match-filter', default='')
    ap.add_argument('--socket-timeout', type=int, default=20)
    ap.add_argument('--retries', type=int, default=2)
    ap.add_argument('--ytdlp-timeout', type=int, default=60, help='yt-dlp single target timeout (seconds)')
    ap.add_argument('--fallback-browser', action='store_true', help='Fall back to browser rendering when yt-dlp fails')
    args = ap.parse_args()

    if args.fallback_browser and not BROWSER_AVAILABLE:
        print('⚠️  --fallback-browser requested but patchright not installed, skipping browser fallback', file=sys.stderr)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    targets = build_targets(args)
    if not targets:
        raise SystemExit('No targets: provide --url, --url-file, or --query')

    jsonl = outdir / 'metadata.jsonl'
    csv_path = outdir / 'metadata.csv'
    rows = []
    per_target = []

    for target in targets:
        result = await extract_with_browser(target, args)
        print(f"[{target[:60]}] method={result['method']}", flush=True)
        per_target.append({'target': target, 'result': result})
        if result['method'] in ('oembed',):
            # Normalize oembed to yt-dlp-like format
            d = result['data']
            row = {
                'extractor_key': 'oembed',
                'id': target,
                'title': d.get('title', ''),
                'uploader': d.get('author_name', ''),
                'channel': d.get('author_name', ''),
                'upload_date': '',
                'duration': 0,
                'view_count': 0,
                'like_count': 0,
                'comment_count': 0,
                'webpage_url': d.get('author_url', target),
            }
            rows.append(row)
        elif result['method'] == 'yt-dlp':
            for r in result['data']:
                rows.append(r)
        elif result['method'] == 'browser':
            # Save browser extract as JSON
            browser_json = outdir / f"browser_{len(per_target)}.json"
            browser_json.write_text(json.dumps(result['data'], ensure_ascii=False, indent=2), encoding='utf-8')
            # Create a pseudo-row
            title = result['data'].get('title', '')
            rows.append({
                'extractor_key': 'browser',
                'id': target,
                'title': title or '',
                'uploader': '',
                'channel': '',
                'upload_date': '',
                'duration': 0,
                'view_count': 0,
                'like_count': 0,
                'comment_count': 0,
                'webpage_url': result['data'].get('final_url', target),
            })

    # Write outputs
    with jsonl.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    cols = ['extractor_key', 'id', 'title', 'uploader', 'channel', 'upload_date',
            'duration', 'view_count', 'like_count', 'comment_count', 'webpage_url']
    with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in cols})

    summary = {
        'platform': args.platform,
        'targets': targets,
        'download': args.download,
        'count': len(rows),
        'methods': {r['result']['method']: sum(1 for p in per_target if p['result']['method'] == r['result']['method']) for r in per_target},
        'created_at': int(time.time()),
        'jsonl': str(jsonl),
        'csv': str(csv_path),
        'outdir': str(outdir),
    }
    (outdir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(main())