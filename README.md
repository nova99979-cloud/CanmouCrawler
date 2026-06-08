# 参谋多平台采集台

本地运行的多平台数据采集工具，支持抖音、TikTok、YouTube、Instagram、X/Twitter 等。

## 文件说明

| 文件 | 说明 |
|------|------|
| `app_server.py` | Web 服务主程序（http://127.0.0.1:8765） |
| `start.sh` | macOS 启动脚本 |
| `overseas_extract.py` | 海外平台采集引擎（OEmbed → yt-dlp → 浏览器渲染） |
| `overseas_assistant.py` | 海外智能采集助手（Cookie + 反封检测 + 重试） |
| `build/build_win.py` | Windows 安装包构建脚本 |
| `.github/workflows/build.yml` | GitHub Actions 自动构建配置 |

## 运行

### macOS
```bash
bash start.sh
```
或双击桌面 `参谋多平台采集台.app`

### Windows（需要自行构建）
```bash
python build/build_win.py
```
输出 `dist/参谋多平台采集台.exe`，双击运行。

或通过 GitHub Actions 自动构建：推送代码到 GitHub main 分支即可。

## 环境要求
- Python 3.11+
- Chrome 浏览器（用于 Cookie 读取）
- macOS: yt-dlp, Patchright
- Windows: yt-dlp 需额外安装

## 桌面 App
- macOS: `测试app/参谋多平台采集台.app`（Automator 打包）
- Windows: 运行 build_win.py 生成 .exe
