#!/usr/bin/env python3
import json, os, subprocess, sys, time, uuid, html, shlex
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = Path('/Users/aiqing/.openclaw/workspace-canmou')
PY_CRAWLERS = ROOT / '.venv-crawlers311/bin/python'
PY_MEDIA = ROOT / '.venv-mediacrawler311/bin/python'
MEDIA_DIR = ROOT / 'crawlers/MediaCrawler'
OVERSEAS_SCRIPT = ROOT / 'crawlers/overseas_extract.py'
RUNS = ROOT / 'outputs/app_runs'
RUNS.mkdir(parents=True, exist_ok=True)
TASKS = {}

PLATFORMS = {
    'dy': '抖音', 'xhs': '小红书', 'ks': '快手', 'bili': 'B站', 'wb': '微博', 'tieba': '贴吧', 'zhihu': '知乎'
}

OVERSEAS_BULK = [
    {'platform':'tiktok',  'name':'TikTok',    'url':'https://www.tiktok.com/@tiktok/video/7108035792512945450'},
    {'platform':'youtube', 'name':'YouTube',   'url':'https://www.youtube.com/watch?v=dQw4w9WgXcQ'},
    {'platform':'instagram','name':'Instagram','url':'https://www.instagram.com/p/CwVOP3eIK1x/'},
    {'platform':'facebook','name':'Facebook',  'url':'https://www.facebook.com/watch/?v=10156115910856598'},
    {'platform':'x',       'name':'X/Twitter', 'url':'https://x.com/NASA/status/1793628904698773838'},
]

def now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def safe_name(s):
    return ''.join(c if c.isalnum() or c in '-_.' else '_' for c in s)[:80]

def start_task(kind, cmd, cwd, outdir):
    tid = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{kind}_{uuid.uuid4().hex[:6]}"
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    log = outdir / 'task.log'
    f = log.open('w', encoding='utf-8')
    f.write(f"[{now()}] START {kind}\nCMD: {' '.join(map(str,cmd))}\nCWD: {cwd}\n\n")
    f.flush()
    p = subprocess.Popen(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT, text=True)
    TASKS[tid] = {'id':tid, 'kind':kind, 'cmd':map(str,cmd), 'cwd':str(cwd), 'outdir':str(outdir), 'log':str(log), 'pid':p.pid, 'process':p, 'start':now()}
    return tid

def task_view():
    rows=[]
    for tid,t in list(TASKS.items())[::-1]:
        p=t['process']; rc=p.poll()
        if rc is None: status='<span class="tag tag-running">🔄 运行中</span>'
        elif rc==0: status=f'<span class="tag tag-ok">✅ 完成</span>'
        else: status=f'<span class="tag tag-err">❌ 失败({rc})</span>'
        rows.append(f'<tr><td>{html.escape(tid)}</td><td>{html.escape(t["kind"])}</td><td>{status}</td><td>{t["pid"]}</td><td><a href="/task?id={html.escape(tid)}">日志</a></td><td><a href="/task_result?id={html.escape(tid)}">&#128202; 结果</a></td><td><a href="/files?dir={html.escape(t["outdir"])}">文件</a></td></tr>')
    return '\n'.join(rows) or '<tr><td colspan=6>暂无任务</td></tr>'

INDEX = r'''<!doctype html><html><head><meta charset="utf-8"><title>参谋多平台采集台</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1100px;margin:28px auto;padding:0 18px;background:#fafafa;color:#222} h1{font-size:28px;margin-bottom:2px} .subtitle{color:#888;font-size:14px;margin-top:0;margin-bottom:20px} h2{margin-top:22px;font-size:20px}.card{background:white;border:1px solid #e5e5e5;border-radius:12px;padding:18px;margin:14px 0;box-shadow:0 1px 2px #0001}label{display:block;margin:10px 0 4px;font-weight:600}input,select,textarea{width:100%;box-sizing:border-box;padding:9px;border:1px solid #ccc;border-radius:8px;font-size:14px}button{background:#111;color:white;border:0;border-radius:8px;padding:10px 16px;font-size:14px;cursor:pointer;margin-top:12px}.btn-sm{background:#333;padding:6px 12px;font-size:13px;margin:0 4px}.btn-yellow{background:#d4a017;color:#fff;border:0;border-radius:8px;padding:10px 16px;font-size:14px;cursor:pointer;margin-top:12px}.hint{color:#666;font-size:13px;line-height:1.5}table{width:100%;border-collapse:collapse;background:white}td,th{border-bottom:1px solid #eee;padding:8px;text-align:left;font-size:13px}td:first-child,th:first-child{padding-left:6px}code{background:#f1f1f1;padding:2px 5px;border-radius:4px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:800px){.grid{grid-template-columns:1fr}}.tab{display:inline-block;padding:8px 18px;margin:0 2px;cursor:pointer;border-radius:8px 8px 0 0;background:#ddd;font-size:14px;font-weight:600}.tab.active{background:white;border:1px solid #e5e5e5;border-bottom:1px solid white}.tab-content{background:white;border:1px solid #e5e5e5;border-radius:0 8px 8px 8px;padding:18px;margin-top:-1px}.tag{display:inline-block;padding:1px 8px;border-radius:12px;font-size:11px;font-weight:600}.tag-ok{background:#d4edda;color:#155724}.tag-running{background:#ffeeba;color:#856404}.tag-done{background:#cce5ff;color:#004085}.tag-err{background:#f8d7da;color:#721c24}
</style>
</head><body><h1>参谋多平台采集台</h1><p class="subtitle">本地运行 · 不上传数据 · 请仅采集你有权限查看的公开内容</p>

<div class="card" style="margin-top:0"><h2 style="margin-top:0">一键批量验证：海外平台可达性测试</h2>
<form method="post" action="/run_bulk_overseas">
<p class="hint">用每个平台的代表性公开链接跑一遍，验证元数据可采集性。限 metadata-only。</p>
<button class="btn-yellow" onclick="return confirm('将依次测试 TikTok / YouTube / Instagram / Facebook / X，约1-2分钟')">🚀 开始批量验证</button>
</form></div>

<div class="tabs">
<span class="tab active" onclick="showTab(this,'tab-douyin')">🎵 抖音</span>
<span class="tab" onclick="showTab(this,'tab-media')">📱 国内多平台</span>
<span class="tab" onclick="showTab(this,'tab-overseas')">🌍 海外平台</span>
</div>

<div id="tab-douyin" class="tab-content">
<div class="grid">
<div class="card" style="border:0;padding:0;margin:0"><h3>单视频/精选链接</h3><form method="post" action="/run_douyin_public"><label>URL</label><input name="url" value="https://www.douyin.com/jingxuan?modal_id=7639590279997132072"><label>等待渲染(ms)</label><input name="wait_ms" value="8000"><button>公开页抓取</button></form><p class="hint">不登录，仅提取页面公开可见内容。</p></div>
<div class="card" style="border:0;padding:0;margin:0"><h3>作者主页公开资料</h3><form method="post" action="/run_douyin_author"><label>作者主页 URL / sec_uid</label><input name="url" value="https://www.douyin.com/user/MS4wLjABAAAA3E5Bodw8QYFKQtESpZLZvzQQ9gTW9HGiZ6Zyrx-kWfoDQlvK7vDsQ0iyw1S4_uZ6"><button>抓作者资料</button></form></div>
</div>
</div>

<div id="tab-media" class="tab-content" style="display:none">
<div class="card" style="border:0;padding:0;margin:0"><h3>MediaCrawler 搜索/详情/作者</h3><form method="post" action="/run_media"><label>平台</label><select name="platform"><option value="dy">抖音</option><option value="xhs">小红书</option><option value="ks">快手</option><option value="bili">B站</option><option value="wb">微博</option><option value="tieba">贴吧</option><option value="zhihu">知乎</option></select><label>模式</label><select name="mode"><option value="search">关键词搜索</option><option value="detail">指定内容详情</option><option value="creator">作者主页</option></select><label>关键词（search 模式）</label><input name="keywords" placeholder="多个关键词用英文逗号分隔"><label>指定内容 URL/ID（detail 模式，多个用英文逗号分隔）</label><textarea name="specified_id" rows="1"></textarea><label>作者 URL/ID（creator 模式，多个用英文逗号分隔）</label><textarea name="creator_id" rows="1"></textarea><label>最大内容数</label><input name="max_notes" value="20"><label>单条评论数上限</label><input name="max_comments" value="20"><label>登录方式</label><select name="lt"><option value="qrcode">二维码/已保存登录态</option><option value="cookie">Cookie</option></select><label>Cookie（可选）</label><textarea name="cookies" rows="1"></textarea><label><input type="checkbox" name="get_comment" value="true" checked style="width:auto"> 抓评论</label><button>启动 MediaCrawler</button></form><p class="hint">首次登录会弹浏览器扫码；结果在 MediaCrawler data 目录及本 App run 目录中。</p></div>
</div>

<div id="tab-overseas" class="tab-content" style="display:none">
<div class="card" style="border:1px solid #d4a017;padding:18px;margin:0 0 14px 0;border-radius:12px;background:#fffbe6"><h3 style="margin-top:0">🛡️ 智能采集模式（自动 Cookie + 反封 + 重试）</h3><form method="post" action="/run_overseas_smart"><label>平台</label><select name="platform"><option value="youtube">YouTube</option><option value="tiktok">TikTok</option><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="x">X/Twitter</option><option value="vimeo">Vimeo</option></select><label>关键词搜索</label><input name="query" placeholder="mrbeast bunker"><label>URL（多个用换行分隔）</label><textarea name="url" rows="2" placeholder="https://www.youtube.com/watch?v=..."></textarea><label>数量上限</label><input name="limit" value="5"><button style="background:#d4a017">🚀 智能采集</button></form><p class="hint">自动导出 Chrome Cookie → 检测IP被封 → 建议换节点 → 自动重试。</p></div>
<div class="card" style="border:0;padding:0;margin:0"><h3>海外平台：URL / 搜索（手动模式）</h3><form method="post" action="/run_overseas"><label>平台</label><select name="platform"><option value="tiktok">TikTok</option><option value="youtube">YouTube</option><option value="facebook">Facebook</option><option value="instagram">Instagram</option><option value="x">X / Twitter</option><option value="reddit">Reddit</option><option value="vimeo">Vimeo</option><option value="url">通用 URL</option></select><label>URL（可多行；支持公开视频/主页/频道/播放列表等）</label><textarea name="url" rows="3" placeholder="https://www.tiktok.com/@handle/video/...
https://www.youtube.com/watch?v=..."></textarea><label>关键词搜索（目前优先支持 YouTube / TikTok）</label><input name="query" placeholder="mrbeast bunker"><label>数量上限</label><input name="limit" value="10"><label>Cookie 来源（可选，chrome/safari/firefox）</label><input name="cookies_from_browser" placeholder="chrome"><label>过滤条件（可选，yt-dlp match-filter）</label><input name="match_filter" placeholder="view_count >= 100000"><label><input type="checkbox" name="download" value="true" style="width:auto"> 下载媒体（默认只抓元数据）</label><button>启动抓取</button></form><p class="hint">底层 yt-dlp，默认 metadata-only；Facebook/Instagram/X 若需登录可用浏览器 Cookie。</p></div>
</div>

<div class="card"><h2>报告与任务</h2>
<p><a href="/files?dir=__RUNS__">查看 App 运行目录</a></p>
<table><thead><tr><th>ID</th><th>类型</th><th>状态</th><th>PID</th><th>日志</th><th>&#128202; 结果</th><th>文件</th></tr></thead><tbody>__TASKS__</tbody></table></div>
<script>
function showTab(el,id){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));el.classList.add('active');document.querySelectorAll('.tab-content').forEach(t=>t.style.display='none');document.getElementById(id).style.display='block'}
setTimeout(()=>{ if(location.pathname=='/') location.reload() }, 5000)
</script></body></html>'''

class H(BaseHTTPRequestHandler):
    def send(self, body, code=200, ctype='text/html; charset=utf-8'):
        self.send_response(code); self.send_header('Content-Type', ctype); self.end_headers(); self.wfile.write(body.encode('utf-8'))
    def params(self):
        n=int(self.headers.get('Content-Length','0') or 0); return parse_qs(self.rfile.read(n).decode('utf-8'))
    def redirect(self, path='/'):
        self.send_response(303); self.send_header('Location', path); self.end_headers()
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=='/':
            page = INDEX.replace('__TASKS__', task_view()).replace('__RUNS__', str(RUNS))
            return self.send(page)
        if u.path=='/task':
            tid=parse_qs(u.query).get('id',[''])[0]; t=TASKS.get(tid)
            if not t: return self.send('not found',404)
            log=Path(t['log']).read_text(encoding='utf-8', errors='replace')[-50000:]
            return self.send(f"<meta charset=utf-8><h1>{html.escape(tid)}</h1><p><a href='/'>返回</a> | <a href='/files?dir={html.escape(t['outdir'])}'>文件</a></p><pre>{html.escape(log)}</pre>")
        if u.path=='/files':
            d=Path(parse_qs(u.query).get('dir',[str(RUNS)])[0])
            if not d.exists(): return self.send('dir not found',404)
            rows=[]
            for p in sorted(d.iterdir(), key=lambda x:x.name):
                rel=str(p)
                if p.is_dir(): rows.append(f"<li>📁 <a href='/files?dir={html.escape(rel)}'>{html.escape(p.name)}</a></li>")
                else: rows.append(f"<li>📄 <a href='/raw?file={html.escape(rel)}'>{html.escape(p.name)}</a> ({p.stat().st_size} bytes)</li>")
            return self.send(f"<meta charset=utf-8><h1>文件：{html.escape(str(d))}</h1><p><a href='/'>返回</a></p><ul>{''.join(rows)}</ul>")
        if u.path=='/raw':
            f=Path(parse_qs(u.query).get('file',[''])[0])
            if not f.exists() or f.is_dir(): return self.send('file not found',404)
            data=f.read_text(encoding='utf-8', errors='replace')
            return self.send(f"<meta charset=utf-8><p><a href='javascript:history.back()'>返回</a></p><pre>{html.escape(data)}</pre>")
        if u.path=='/task_result':
            tid=parse_qs(u.query).get('id',[''])[0]; t=TASKS.get(tid)
            if not t: return self.send('not found',404)
            out=Path(t['outdir'])
            csv_file = out / 'metadata.csv'
            summary_file = out / 'summary.json'
            summary_data = {}
            if summary_file.exists():
                try: summary_data=json.loads(summary_file.read_text())
                except: pass
            rows_html = []
            csv_preview = ''
            if csv_file.exists():
                lines = csv_file.read_text(encoding='utf-8').splitlines()
                if len(lines) > 1:
                    header = lines[0].split(',')
                    rows_html.append('<table><thead><tr>' + ''.join(f'<th>{html.escape(h)}</th>' for h in header[:8]) + '</tr></thead><tbody>')
                    for line in lines[1:11]:
                        cells = line.split(',')
                        rows_html.append('<tr>' + ''.join(f'<td>{html.escape(c[:80])}</td>' for c in cells[:8]) + '</tr>')
                    rows_html.append('</tbody></table>')
                    csv_preview = ''.join(rows_html)
            browser_preview = ''
            for bjson in sorted(out.glob('browser_*.json')):
                try:
                    bd = json.loads(bjson.read_text())
                    browser_preview += f'<div class="card"><h3>浏览器渲染结果</h3><p><b>标题:</b> {html.escape(str(bd.get("title","")))}</p><p><b>最终URL:</b> {html.escape(str(bd.get("final_url","")))}</p><pre>{html.escape(str(bd.get("body_text",""))[:800])}</pre></div>'
                except: pass
            method_info = '<br>'.join(f'{k}: {v}' for k,v in summary_data.get('methods',{}).items())
            return self.send(f'''<meta charset="utf-8"><h1>采集结果: {html.escape(t["kind"])}</h1>
<p><a href="/">返回</a> | <a href="/task?id={html.escape(tid)}">完整日志</a> | <a href="/files?dir={html.escape(t["outdir"])}">全部文件</a></p>
<div class="card"><h3>概要</h3><p>方法: {method_info}</p><p>条数: {summary_data.get("count",0)}</p></div>
{browser_preview}
<div class="card"><h3>数据预览</h3>{csv_preview}</div>
''')
        return self.send('not found',404)
    def do_POST(self):
        p=self.params()
        if self.path=='/run_douyin_public':
            url=p.get('url',[''])[0]; wait=p.get('wait_ms',['8000'])[0]
            out=RUNS/f"douyin_public_{uuid.uuid4().hex[:8]}"
            tid=start_task('douyin_public',[str(PY_CRAWLERS), str(ROOT/'crawlers/douyin_public_extract.py'), url, '--outdir', str(out), '--wait-ms', wait], ROOT, out)
            return self.redirect(f'/task?id={tid}')
        if self.path=='/run_douyin_author':
            url=p.get('url',[''])[0]
            out=RUNS/f"douyin_author_{uuid.uuid4().hex[:8]}"
            tid=start_task('douyin_author',[str(PY_CRAWLERS), str(ROOT/'crawlers/douyin_author_profile_extract.py'), url, '--outdir', str(out)], ROOT, out)
            return self.redirect(f'/task?id={tid}')
        if self.path=='/run_overseas':
            platform=p.get('platform',['url'])[0]
            out=RUNS/f"overseas_{platform}_{uuid.uuid4().hex[:8]}"
            cmd=['python3', str(OVERSEAS_SCRIPT), '--platform', platform, '--outdir', str(out), '--limit', p.get('limit',['10'])[0]]
            if p.get('url',[''])[0]: cmd += ['--url', p.get('url',[''])[0]]
            if p.get('query',[''])[0]: cmd += ['--query', p.get('query',[''])[0]]
            if p.get('cookies_from_browser',[''])[0]: cmd += ['--cookies-from-browser', p.get('cookies_from_browser',[''])[0]]
            if p.get('match_filter',[''])[0]: cmd += ['--match-filter', p.get('match_filter',[''])[0]]
            if p.get('download'): cmd += ['--download']
            if p.get('fallback_browser'): cmd += ['--fallback-browser']
            tid=start_task('overseas_'+platform,cmd,ROOT,out)
            return self.redirect(f'/task?id={tid}')
        if self.path=='/run_overseas_smart':
            platform=p.get('platform',['youtube'])[0]
            out=RUNS/f'smart_{platform}_{uuid.uuid4().hex[:8]}'
            cmd=['python3', str(ROOT/'crawlers/overseas_assistant.py'),
                 '--platform', platform,
                 '--limit', p.get('limit',['5'])[0]]
            if p.get('url',[''])[0]: cmd += ['--url', p.get('url',[''])[0]]
            if p.get('query',[''])[0]: cmd += ['--query', p.get('query',[''])[0]]
            tid=start_task('smart_'+platform,cmd,ROOT,out)
            return self.redirect(f'/task?id={tid}')
        if self.path=='/run_bulk_overseas':
            bulk_out = RUNS / f"bulk_overseas_{uuid.uuid4().hex[:8]}"
            bulk_out.mkdir(parents=True, exist_ok=True)
            report_rows = []
            for item in OVERSEAS_BULK:
                plat = item['platform']
                url = item['url']
                name = item['name']
                out = RUNS / f"bulk_test_{plat}_{uuid.uuid4().hex[:6]}"
                cmd = ['python3', str(OVERSEAS_SCRIPT), '--platform', plat, '--url', url, '--outdir', str(out), '--limit', '1']
                tid = start_task(f'bulk_{plat}', cmd, ROOT, out)
                report_rows.append({'platform':plat, 'name':name, 'url':url, 'tid':tid, 'outdir':str(out)})
            summary = {
                'started_at': now(),
                'platforms': [[r['name'], r['url'], r['tid'], r['outdir']] for r in report_rows]
            }
            (bulk_out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
            # Build a batch overview page
            links = ''.join(f"<li><a href='/task?id={html.escape(r['tid'])}'>{html.escape(r['name'])}</a> — {html.escape(r['url'])}</li>" for r in report_rows)
            return self.send(f"<meta charset=utf-8><h1>批量海外验证已启动</h1><p><a href='/'>返回首页</a></p><p>每个平台独立运行，可分别查看进度：</p><ul>{links}</ul>")
        if self.path=='/run_media':
            platform=p.get('platform',['dy'])[0]; mode=p.get('mode',['search'])[0]
            out=RUNS/f"media_{platform}_{mode}_{uuid.uuid4().hex[:8]}"
            cmd=[str(PY_MEDIA),'main.py','--platform',platform,'--lt',p.get('lt',['qrcode'])[0],'--type',mode,'--save_data_option','jsonl','--headless','false','--crawler_max_notes_count',p.get('max_notes',['20'])[0],'--max_comments_count_singlenotes',p.get('max_comments',['20'])[0], '--save_data_path', str(out)]
            if p.get('keywords',[''])[0]: cmd += ['--keywords', p.get('keywords',[''])[0]]
            if p.get('specified_id',[''])[0]: cmd += ['--specified_id', p.get('specified_id',[''])[0]]
            if p.get('creator_id',[''])[0]: cmd += ['--creator_id', p.get('creator_id',[''])[0]]
            if p.get('cookies',[''])[0]: cmd += ['--cookies', p.get('cookies',[''])[0]]
            cmd += ['--get_comment', 'true' if p.get('get_comment') else 'false', '--get_sub_comment', 'false']
            tid=start_task('media_'+platform+'_'+mode,cmd,MEDIA_DIR,out)
            return self.redirect(f'/task?id={tid}')
        return self.send('not found',404)

def main():
    port=int(os.environ.get('CANMOU_CRAWLER_PORT','8765'))
    httpd=ThreadingHTTPServer(('127.0.0.1',port),H)
    print(f'Canmou Crawler App running: http://127.0.0.1:{port}', flush=True)
    httpd.serve_forever()

if __name__=='__main__': main()