#!/usr/bin/env python3
"""一次性抓包工具：登录微信读书，记录阅读器发出的所有 XHR。

设计成无头运行：二维码截图落盘，不依赖窗口焦点/可见性。

用法：
    python tools/discover.py                  # 无头，二维码写到 capture/qr.png
    WR_HEADLESS=0 python tools/discover.py    # 需要看窗口时

产物：
    capture/qr.png     登录二维码（用手机微信扫）
    capture/xhr.json   所有 /web/* 请求 + JSON 响应
    state.json         登录态，等同于账号凭据，勿外传
"""

import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path("capture")
STATE = Path("state.json")
LOGIN_COOKIE = "wr_skey"
MAX_WAIT_LOGIN = int(os.environ.get("WR_LOGIN_TIMEOUT", "600"))
CHANNEL = os.environ.get("WR_BROWSER_CHANNEL", "chrome")
HEADLESS = os.environ.get("WR_HEADLESS", "1") != "0"


def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def shot_qr(page, tag: str = "qr") -> Path:
    path = OUT_DIR / f"{tag}.png"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sel in ('img[src*="qrcode"]', 'img[src*="qrconnect"]', "canvas",
                '[class*="qrcode"]', '[class*="QRCode"]'):
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                box = loc.bounding_box()
                if box and box["width"] > 80:
                    page.screenshot(path=str(path), clip=box)
                    return path
        except Exception:  # noqa: BLE001
            continue
    page.screenshot(path=str(path))
    return path


def main() -> int:
    records, seen = [], {}

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=HEADLESS, channel=CHANNEL)
        except Exception as exc:  # noqa: BLE001
            print(f"channel={CHANNEL} 失败（{exc}），回退内置 Chromium")
            browser = p.chromium.launch(headless=HEADLESS)

        ctx = browser.new_context(
            storage_state=str(STATE) if STATE.exists() else None,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = ctx.new_page()

        def on_response(resp):
            url = resp.url
            if "/_nuxt/" in url or "cdn.weread.qq.com" in url or "oss.weread.qq.com" in url:
                return
            if "/web/" not in url:
                return
            req = resp.request
            item = {"url": url, "method": req.method, "status": resp.status,
                    "post_data": req.post_data}
            ctype = (resp.headers or {}).get("content-type", "")
            if "json" in ctype:
                try:
                    item["json"] = resp.json()
                except Exception as exc:  # noqa: BLE001
                    item["json_error"] = str(exc)
            records.append(item)
            seen[url.split("?")[0]] = item

        page.on("response", on_response)

        page.goto("https://weread.qq.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        if LOGIN_COOKIE not in {c["name"] for c in ctx.cookies()}:
            clicked = False
            for text in ("登录", "扫码登录", "立即登录"):
                try:
                    loc = page.get_by_text(text, exact=True)
                    if loc.count():
                        loc.first.click()
                        clicked = True
                        break
                except Exception:  # noqa: BLE001
                    pass
            print("clicked login:", clicked)
            page.wait_for_timeout(3000)
            print("QR_READY", shot_qr(page).resolve())

        deadline = time.time() + MAX_WAIT_LOGIN
        last_refresh = time.time()
        while time.time() < deadline:
            if LOGIN_COOKIE in {c["name"] for c in ctx.cookies()}:
                break
            if time.time() - last_refresh > 240:
                for text in ("刷新", "点击刷新"):
                    try:
                        loc = page.get_by_text(text, exact=True)
                        if loc.count():
                            loc.first.click()
                            break
                    except Exception:  # noqa: BLE001
                        pass
                page.wait_for_timeout(1500)
                print("QR_REFRESHED", shot_qr(page, "qr").resolve())
                last_refresh = time.time()
            time.sleep(1)
        else:
            print("LOGIN_TIMEOUT")
            browser.close()
            return 2

        print("LOGIN_OK")
        ctx.storage_state(path=str(STATE))

        page.goto("https://weread.qq.com/web/shelf", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUT_DIR / "shelf.png"))

        opened = False
        try:
            loc = page.locator('a[href*="/web/reader/"]')
            if loc.count() == 0:
                loc = page.locator('[class*="shelfBook"]')
            if loc.count():
                loc.first.click()
                opened = True
        except Exception as exc:  # noqa: BLE001
            print("open book failed:", exc)
        print("opened book:", opened, "url:", page.url)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(OUT_DIR / "reader.png"))

        for i in range(3):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(2500)
            print(f"page turn {i + 1}")
        page.screenshot(path=str(OUT_DIR / "reader2.png"))

        ctx.storage_state(path=str(STATE))
        dump({"records": records, "endpoints": sorted(seen)}, OUT_DIR / "xhr.json")
        dump(sorted(seen), OUT_DIR / "endpoints.json")

        browser.close()

    print(f"CAPTURED {len(records)} responses, {len(seen)} endpoints")
    for ep in sorted(seen):
        print("  ", ep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
