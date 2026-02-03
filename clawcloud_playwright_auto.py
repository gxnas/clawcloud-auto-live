#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ClawCloud 自动保活
"""

import os
import time
import re
import json
import pyotp
import platform
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ================= 基础配置 =================

CLAW_CLOUD_URL = os.environ.get(
    "CLAW_CLOUD_URL", "https://eu-central-1.run.claw.cloud"
)

SCRIPT_DIR = "/ql/data/scripts/clawcloud"
STATE_FILE = f"{SCRIPT_DIR}/clawcloud_state.json"

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

MAX_TIMEOUT_FAIL = 2
SKIP_HOURS = 24

# ================= 日志 =================

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ================= Telegram =================

def tg_send_result(photo_path, text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        if photo_path and os.path.exists(photo_path):
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
            with open(photo_path, "rb") as f:
                requests.post(
                    url,
                    data={"chat_id": TG_CHAT_ID, "caption": text[:1024]},
                    files={"photo": f},
                    timeout=20
                )
        else:
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            requests.post(
                url,
                data={"chat_id": TG_CHAT_ID, "text": text[:4096]},
                timeout=20
            )
    except Exception as e:
        log(f"[TG] 推送失败（忽略）：{e}")

def tg_send_summary(success, skipped, failed, cost):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    text = (
        "📊 ClawCloud 自动保活完成\n\n"
        f"✅ 成功：{success}\n"
        f"⏰ 超时跳过：{skipped}\n"
        f"❌ 异常失败：{failed}\n\n"
        f"⏱ 总耗时：{cost} 秒"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": text},
            timeout=20
        )
    except:
        pass

# ================= 状态缓存 =================

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

STATE = load_state()

def should_skip(username):
    info = STATE.get(username)
    return info and time.time() < info.get("skip_until", 0)

def record_timeout(username):
    info = STATE.get(username, {})
    count = info.get("timeout_count", 0) + 1
    if count >= MAX_TIMEOUT_FAIL:
        info["skip_until"] = time.time() + SKIP_HOURS * 3600
        info["timeout_count"] = 0
        STATE[username] = info
        save_state(STATE)
        return True
    info["timeout_count"] = count
    STATE[username] = info
    save_state(STATE)
    return False

def record_success(username):
    if username in STATE:
        STATE.pop(username)
        save_state(STATE)

# ================= 截图 =================

def safe_screenshot(page, idx, status):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{SCRIPT_DIR}/clawcloud_{status}_acc{idx}_{ts}.png"
    try:
        page.screenshot(path=path, full_page=True, timeout=5000)
        return path
    except Exception as e:
        log(f"⚠️ 截图失败（忽略）：{e}")
        return None

# ================= 账号读取 =================

def load_accounts():
    env = os.environ.get("CLAW_ACCOUNTS", "")
    accounts = []
    for acc in env.split("&"):
        parts = acc.split("----")
        if len(parts) >= 2:
            accounts.append({
                "username": parts[0],
                "password": parts[1],
                "totp": parts[2] if len(parts) > 2 else ""
            })
    return accounts

ACCOUNTS = load_accounts()

# ================= 单账号执行 =================

def handle_account(playwright, acc, idx, retry=False):
    if should_skip(acc["username"]):
        log("⏭️ 已熔断，跳过 24h")
        return "skipped"

    log(f"🚀 账号 {idx} | 架构: {platform.machine()}" + (" | 重试" if retry else ""))

    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    page = browser.new_page()

    try:
        page.goto(CLAW_CLOUD_URL, timeout=60000)
        page.wait_for_timeout(5000)

        if "signin" not in page.url:
            shot = safe_screenshot(page, idx, "success")
            tg_send_result(shot, f"✅ ClawCloud 保活成功\n账号 {idx}")
            record_success(acc["username"])
            browser.close()
            return "success"

        page.get_by_role("button", name="GitHub").click(timeout=30000)
        page.wait_for_timeout(3000)

        if "github.com/login" in page.url:
            page.fill("#login_field", acc["username"])
            page.fill("#password", acc["password"])
            page.click("input[type=submit]")
            page.wait_for_timeout(5000)

            if "two-factor" in page.content().lower() and acc["totp"]:
                code = pyotp.TOTP(acc["totp"]).now()
                page.fill("#otp", code)
                page.keyboard.press("Enter")
                page.wait_for_timeout(5000)

        if "oauth/authorize" in page.url:
            try:
                page.get_by_role("button", name=re.compile("Authorize", re.I)).click(timeout=15000)
            except:
                pass

        page.goto(CLAW_CLOUD_URL + "/apps")
        page.wait_for_timeout(5000)

        shot = safe_screenshot(page, idx, "success")
        tg_send_result(shot, f"✅ ClawCloud 保活成功\n账号 {idx}")
        record_success(acc["username"])
        browser.close()
        return "success"

    except PWTimeout:
        shot = safe_screenshot(page, idx, "timeout")
        tg_send_result(shot, f"⏰ ClawCloud 页面超时\n账号 {idx}")
        browser.close()

        if record_timeout(acc["username"]):
            return "skipped"
        if not retry:
            return handle_account(playwright, acc, idx, retry=True)
        return "failed"

    except Exception as e:
        shot = safe_screenshot(page, idx, "error")
        tg_send_result(shot, f"❌ ClawCloud 异常\n账号 {idx}\n{e}")
        browser.close()
        return "failed"

# ================= 主入口 =================

if __name__ == "__main__":

    print("=" * 60)
    print("💻 ClawCloud Playwright Auto Live")
    print("=" * 60)

    start = time.time()
    success = skipped = failed = 0

    with sync_playwright() as p:
        for i, acc in enumerate(ACCOUNTS, 1):
            r = handle_account(p, acc, i)
            if r == "success":
                success += 1
            elif r == "skipped":
                skipped += 1
            else:
                failed += 1
            time.sleep(10)

    cost = int(time.time() - start)
    tg_send_summary(success, skipped, failed, cost)

    print("\n✅ 所有账号执行完成")
