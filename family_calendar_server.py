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
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CALDAV_PORT = int(os.environ.get("PORT", 8081))
SETUP_PORT = 8082
DATA_DIR = os.path.join(SCRIPT_DIR, "caldav_data")
USERS_FILE = os.path.join(SCRIPT_DIR, "radicale_users.htpasswd")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "radicale_config.cfg")
USERNAME = "family"
PASSWORD = "family2026"


def generate_password_hash(password):
    """使用 bcrypt 生成密码哈希（兼容 Radicale）"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        pass
    try:
        import hashlib
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return "$pbkdf2-sha256$100000${}${}".format(
            salt.hex(), dk.hex()
        )
    except Exception:
        pass
    return password


def generate_config():
    """动态生成 radicale 配置文件，路径基于脚本所在目录"""
    config = f"""[server]
hosts = 0.0.0.0:{CALDAV_PORT}

[auth]
type = htpasswd
htpasswd_filename = {USERS_FILE}
htpasswd_encryption = bcrypt

[storage]
type = multifilesystem
filesystem_folder = {DATA_DIR}

[rights]
type = authenticated

[logging]
level = warning
"""
    with open(CONFIG_FILE, "w") as f:
        f.write(config)


def ensure_users():
    """确保用户文件存在且密码正确（使用 bcrypt 加密）"""
    if os.path.exists(USERS_FILE):
        return

    # 尝试用 bcrypt 库生成
    try:
        import bcrypt
        pw_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
        with open(USERS_FILE, "w") as f:
            f.write(f"{USERNAME}:{pw_hash}\n")
        print(f"[Auth] 用户 {USERNAME} 已创建 (bcrypt)")
        return
    except ImportError:
        print("[Auth] bcrypt 未安装，请运行: pip install bcrypt")
        sys.exit(1)


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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # 等一小会儿，检查是否立即崩溃
    time.sleep(1)
    if proc.poll() is not None:
        _, stderr = proc.communicate()
        print(f"[CalDAV] Radicale 启动失败:\n{stderr.decode()}")
        sys.exit(1)
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
    ensure_users()


def create_default_calendar():
    """创建默认日历集合（iPhone 需要至少一个日历才能验证成功）"""
    import urllib.request
    import urllib.error
    import base64

    auth = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    calendar_url = f"http://127.0.0.1:{CALDAV_PORT}/family/"

    # 重试最多 15 次，等 Radicale 启动
    for i in range(15):
        try:
            req = urllib.request.Request(
                calendar_url, method="MKCOL",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/xml; charset=utf-8",
                },
            )
            urllib.request.urlopen(req, timeout=5)
            print(f"[CalDAV] 默认日历已创建: /family/")
            return
        except urllib.error.HTTPError as e:
            if e.code in (405, 201):
                print(f"[CalDAV] 日历已存在: /family/")
                return
            print(f"[CalDAV] 创建日历: HTTP {e.code}")
            return
        except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
            msg = str(e)
            if "Connection refused" in msg or "timed out" in msg.lower() or "getaddrinfo" in msg:
                if i == 0:
                    print(f"[CalDAV] 等待 Radicale 启动...")
                time.sleep(1)
                continue
            print(f"[CalDAV] 创建日历失败: {e}")
            return
        except Exception as e:
            print(f"[CalDAV] 创建日历异常: {e}")
            return
    print(f"[CalDAV] 无法连接 Radicale，跳过创建日历")


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

    # 创建默认日历（内部会重试等待 Radicale 启动）
    create_default_calendar()

    # 启动配置指南页面
    try:
        start_setup_server()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        radicale_proc.terminate()
        radicale_proc.wait()


if __name__ == "__main__":
    main()