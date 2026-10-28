#!/usr/bin/env python3
"""登录 + 抓包一体化（CDP 挂到真实 Chrome 上）。

登录判定：调用 /web/shelf/sync，errCode == 0 才算真登录。
访客态也会下发 wr_skey，所以不能看 cookie。

用法：
    WR_ATTACH=1 python tools/login_flow.py     # 复用已开的调试 Chrome
    python tools/login_flow.py                 # 自己拉起 Chrome
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
PROFILE = Path(os.environ.get("WR_PROFILE", ".chrome-profile")).resolve()
OUT = Path("capture")
STATE = Path("state.json")
MAX_WAIT = int(os.environ.get("WR_LOGIN_TIMEOUT", "900"))


def shot(page, name):
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(OUT / f"{name}.png"))
    except Exception:  # noqa: BLE001
        pass


def shelf_ok(page):
    try:
        res = page.evaluate(
            "async () => { const r = await fetch('/web/shelf/sync',"
            " {credentials:'include'}); return await r.json(); }"
        )
        # 成功响应不带 errCode 字段；访客/未登录才带非 0 的 errCode
        ok = res.get("errCode", 0) == 0 and ("bookCount" in res or "books" in res)
        return ok, res
    except Exception as exc:  # noqa: BLE001
        return False, {"error": str(exc)[:120]}


def open_login(page):
    for text in ("登录", "扫码登录", "立即登录"):
        try:
            loc = page.get_by_text(text, exact=True)
            if loc.count():
                loc.first.click()
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def refresh_qr(page):
    for text in ("点击刷新", "刷新", "重新获取"):
        try:
            loc = page.get_by_text(text, exact=True)
            if loc.count():
                loc.first.click()
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def main() -> int:
    proc = None
    if os.environ.get("WR_ATTACH") != "1":
        PROFILE.mkdir(parents=True, exist_ok=True)
        Path(".crash").mkdir(exist_ok=True)
        proc = subprocess.Popen(
            [CHROME, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
             "--no-first-run", "--no-default-browser-check",
             "--no-sandbox", "--disable-gpu", "--disable-crash-reporter",
             f"--crash-dumps-dir={Path('.crash').resolve()}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(5)

    records, seen = [], {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            def on_response(resp):
                url = resp.url
                if "/web/" not in url or "/_nuxt/" in url:
                    return
                if any(h in url for h in ("cdn.weread.qq.com", "oss.weread.qq.com")):
                    return
                item = {"url": url, "method": resp.request.method, "status": resp.status,
                        "post_data": resp.request.post_data}
                if "json" in (resp.headers or {}).get("content-type", ""):
                    try:
                        item["json"] = resp.json()
                    except Exception as exc:  # noqa: BLE001
                        item["json_error"] = str(exc)
                records.append(item)
                seen[url.split("?")[0]] = item

            page.on("response", on_response)

            if "weread.qq.com" not in page.url:
                page.goto("https://weread.qq.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)

            ok, res = shelf_ok(page)
            print("logged_in:", ok, "| shelf:", json.dumps(res, ensure_ascii=False)[:120])

            if not ok:
                print("open_login:", open_login(page))
                page.wait_for_timeout(3000)
                shot(page, "qr")
                print("QR_SAVED", (OUT / "qr.png").resolve())

            deadline = time.time() + MAX_WAIT
            last = 0
            refreshed = 0
            while time.time() < deadline:
                ok, res = shelf_ok(page)
                if ok:
                    break
                if time.time() - last > 8:
                    last = time.time()
                    shot(page, "live")
                    try:
                        txt = page.inner_text("body")[:150].replace("\n", " ")
                    except Exception:  # noqa: BLE001
                        txt = ""
                    stamp = time.strftime("%H:%M:%S")
                    print(f"[{stamp}] WAIT {int(deadline - time.time())}s | {txt[:100]}")
                    if any(k in txt for k in ("过期", "失效", "刷新")):
                        if refresh_qr(page):
                            refreshed += 1
                            page.wait_for_timeout(2000)
                            shot(page, "qr")
                            print("QR_REFRESHED", refreshed, (OUT / "qr.png").resolve())
                time.sleep(3)
            else:
                print("LOGIN_TIMEOUT")
                return 2

            print("LOGIN_OK")
            ctx.storage_state(path=str(STATE))

            page.goto("https://weread.qq.com/web/shelf", wait_until="commit", timeout=60000)
            page.wait_for_timeout(6000)
            shot(page, "shelf")

            loc = page.locator('a[href*="/web/reader/"]')
            print("shelf links:", loc.count(), "url:", page.url)
            if loc.count() == 0:
                loc = page.locator('[class*="shelfBook"]')
            if loc.count():
                loc.first.click()
                page.wait_for_timeout(7000)
                print("reader url:", page.url)
                shot(page, "reader")
                for i in range(3):
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(2500)
                    print("turn", i + 1)
                shot(page, "reader2")
            else:
                print("no book found")

            ctx.storage_state(path=str(STATE))
            (OUT / "xhr.json").write_text(
                json.dumps({"records": records, "endpoints": sorted(seen)},
                           ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"CAPTURED {len(records)} responses / {len(seen)} endpoints")
            for ep in sorted(seen):
                print("  ", ep)
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
