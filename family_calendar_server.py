#!/usr/bin/env python3
"""
家庭共享日历 - CalDAV 服务器启动脚本
======================================
使用 Radicale 提供 CalDAV 协议支持，家人可以直接在手机自带日历 App 中
添加、编辑、删除日程，所有设备自动同步。

启动方式: python3 family_calendar_server.py

手机配置说明:
  - 打开 http://你的IP:8082 查看配置指南
  - CalDAV 服务器地址: http://你的IP:8081
  - 账号: family  /  密码: family2026
"""

import http.server
import os
import socket
import subprocess
import sys
import threading
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CALDAV_PORT = int(os.environ.get("PORT", 8081))
SETUP_PORT = 8082
DATA_DIR = os.path.join(SCRIPT_DIR, "caldav_data")
USERS_FILE = os.path.join(SCRIPT_DIR, "radicale_users.htpasswd")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "radicale_config.cfg")


def generate_config():
    """动态生成 radicale 配置文件，路径基于脚本所在目录"""
    config = f"""[server]
hosts = 0.0.0.0:{CALDAV_PORT}

[auth]
type = htpasswd
htpasswd_filename = {USERS_FILE}
htpasswd_encryption = plain

[storage]
type = multifilesystem
filesystem_folder = {DATA_DIR}

[rights]
type = authenticated
"""
    with open(CONFIG_FILE, "w") as f:
        f.write(config)


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


SETUP_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>家庭日历 - 手机配置指南</title>
<style>
:root { --accent: #4A90D9; --bg: #f5f5f7; --card: #fff; --text: #1a1a2e; --text2: #666; }
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family: -apple-system, 'Noto Sans SC', 'PingFang SC', sans-serif;
    background: var(--bg); color: var(--text);
    min-height: 100vh; padding: 30px 20px;
}
.container { max-width: 520px; margin: 0 auto; }
h1 { font-size: 1.5rem; font-weight: 800; text-align: center; margin-bottom: 4px; }
.subtitle { color: var(--text2); font-size: 0.85rem; text-align: center; margin-bottom: 24px; }
.card {
    background: var(--card); border-radius: 16px; padding: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 16px;
}
.card h2 { font-size: 1rem; color: var(--accent); margin-bottom: 14px; }
.step {
    display: flex; gap: 12px; align-items: flex-start; margin: 10px 0;
    padding: 12px; background: #f8f9fa; border-radius: 10px;
}
.step-num {
    width: 28px; height: 28px; border-radius: 50%;
    background: var(--accent); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.8rem; flex-shrink: 0;
}
.step-text { font-size: 0.85rem; color: var(--text2); line-height: 1.5; flex: 1; }
.step-text strong { color: var(--text); }
.info-box {
    background: #f0f7ff; border: 1px solid #d0e3f5; border-radius: 10px;
    padding: 14px; margin: 12px 0; font-size: 0.82rem; line-height: 1.6;
}
.info-box code {
    background: #e8f0f8; padding: 2px 6px; border-radius: 4px;
    font-size: 0.85rem; font-family: monospace;
}
.note { font-size: 0.7rem; color: var(--text2); opacity: 0.5; text-align: center; margin-top: 20px; }
</style>
</head>
<body>
<div class="container">
    <h1>📅 家庭共享日历</h1>
    <p class="subtitle">用手机自带日历 App 管理 · 全家自动同步</p>

    <div class="card">
        <h2>🔑 账号信息</h2>
        <div class="info-box">
            服务器地址：<code id="server-url">http://SERVER:8081</code><br>
            用户名：<code>family</code><br>
            密码：<code>family2026</code>
        </div>
    </div>

    <div class="card">
        <h2>📱 iPhone 配置</h2>
        <div class="step">
            <span class="step-num">1</span>
            <span class="step-text">打开 <strong>设置</strong> → <strong>日历</strong> → <strong>账户</strong></span>
        </div>
        <div class="step">
            <span class="step-num">2</span>
            <span class="step-text">点击 <strong>添加账户</strong> → 选择 <strong>其他</strong></span>
        </div>
        <div class="step">
            <span class="step-num">3</span>
            <span class="step-text">选择 <strong>添加 CalDAV 账户</strong></span>
        </div>
        <div class="step">
            <span class="step-num">4</span>
            <span class="step-text">填入上方<strong>服务器地址、用户名、密码</strong>，点击"下一步"</span>
        </div>
        <div class="step">
            <span class="step-num">5</span>
            <span class="step-text">打开<strong>日历 App</strong>，即可看到共享日历，可以直接添加/编辑日程</span>
        </div>
    </div>

    <div class="card">
        <h2>🤖 小米手机配置</h2>
        <div class="step">
            <span class="step-num">1</span>
            <span class="step-text">打开 <strong>设置</strong> → <strong>账号与同步</strong></span>
        </div>
        <div class="step">
            <span class="step-num">2</span>
            <span class="step-text">点击 <strong>添加账号</strong> → 选择 <strong>CalDAV</strong> 或 <strong>公司/Exchange</strong></span>
        </div>
        <div class="step">
            <span class="step-num">3</span>
            <span class="step-text">填入上方的<strong>服务器地址、用户名、密码</strong></span>
        </div>
        <div class="step">
            <span class="step-num">4</span>
            <span class="step-text">保存后，打开<strong>日历 App</strong> 即可使用</span>
        </div>
    </div>

    <div class="card">
        <h2>🤖 华为手机配置</h2>
        <div class="step">
            <span class="step-num">1</span>
            <span class="step-text">打开 <strong>设置</strong> → <strong>用户和账户</strong></span>
        </div>
        <div class="step">
            <span class="step-num">2</span>
            <span class="step-text">点击 <strong>添加账户</strong> → 选择 <strong>CalDAV</strong> 或 <strong>日历</strong></span>
        </div>
        <div class="step">
            <span class="step-num">3</span>
            <span class="step-text">填入上方的<strong>服务器地址、用户名、密码</strong></span>
        </div>
        <div class="step">
            <span class="step-num">4</span>
            <span class="step-text">保存后，打开<strong>日历 App</strong> 即可使用</span>
        </div>
    </div>

    <p class="note">⚡ 所有家人用同一个账号登录，任何人在手机日历中添加/修改/删除日程，其他人都会自动同步</p>
</div>

<script>
document.querySelectorAll('#server-url').forEach(el => {
    el.textContent = 'http://' + window.location.hostname + ':8081';
});
</script>
</body>
</html>"""


def start_radicale():
    """启动 Radicale CalDAV 服务器"""
    print(f"[CalDAV] 启动 Radicale 服务器...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "radicale", "--config", CONFIG_FILE],
        cwd=SCRIPT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def start_setup_server():
    """启动配置指南页面服务器"""
    class SetupHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            html = SETUP_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("0.0.0.0", SETUP_PORT), SetupHandler)
    print(f"[Setup] 配置页面: http://{get_local_ip()}:{SETUP_PORT}")
    server.serve_forever()


def ensure_dirs():
    """确保数据目录和配置文件存在"""
    os.makedirs(DATA_DIR, exist_ok=True)
    generate_config()


def main():
    ensure_dirs()

    local_ip = get_local_ip()

    print(f"""
╔══════════════════════════════════════════════════════╗
║          📅  家庭共享日历 - CalDAV 服务器           ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  CalDAV 地址: http://{local_ip}:{CALDAV_PORT}       ║
║  配置指南:    http://{local_ip}:{SETUP_PORT}         ║
║                                                      ║
║  🔑 账号: family                                     ║
║  🔑 密码: family2026                                 ║
║                                                      ║
║  📱 手机配置：                                       ║
║     iPhone: 设置 → 日历 → 账户 → 添加 CalDAV        ║
║     小米:   设置 → 账号与同步 → 添加 CalDAV         ║
║     华为:   设置 → 用户和账户 → 添加 CalDAV         ║
║                                                      ║
║  按 Ctrl+C 停止服务器                                ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """)

    # 启动 CalDAV 服务器
    radicale_proc = start_radicale()

    # 启动配置指南页面
    try:
        start_setup_server()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        radicale_proc.terminate()
        radicale_proc.wait()


if __name__ == "__main__":
    main()