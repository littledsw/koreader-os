#!/usr/bin/env python3
"""用本机真实 Chrome（CDP 挂载）登录并抓包。

为什么：headless 里扫码会被判"登录失败"。这里启动一个普通 Chrome 进程，
用 --remote-debugging-port 暴露，Playwright 只做 CDP 连接，
浏览器没有 automation 指纹，扫码等同于正常网页登录。

用法：
    python tools/run_cdp.py

产物：capture/qr.png、capture/xhr.json、state.json
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
MAX_WAIT = int(os.environ.get("WR_LOGIN_TIMEOUT", "600"))


def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def shot(page, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / f"{name}.png"))


def main() -> int:
    if not Path(CHROME).exists():
        print("找不到 Chrome:", CHROME)
        return 1
    PROFILE.mkdir(parents=True, exist_ok=True)

    proc = None
    if os.environ.get("WR_ATTACH") == "1":
        print("attach 模式：复用已在 127.0.0.1:%d 上的 Chrome" % PORT)
    else:
        (PROFILE / "..").resolve()
        Path(".crash").mkdir(exist_ok=True)
        proc = subprocess.Popen(
            [CHROME, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
             "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
             "--no-sandbox", "--disable-gpu", "--disable-crash-reporter",
             f"--crash-dumps-dir={Path('.crash').resolve()}",
             "about:blank"],
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
            page.goto("https://weread.qq.com/", wait_until="domcontentloaded")
            page.wait_for_timeout(2500)

            if "wr_skey" not in {c["name"] for c in ctx.cookies("https://weread.qq.com")}:
                for text in ("登录", "扫码登录", "立即登录"):
                    try:
                        loc = page.get_by_text(text, exact=True)
                        if loc.count():
                            loc.first.click()
                            break
                    except Exception:  # noqa: BLE001
                        pass
                page.wait_for_timeout(3000)
                shot(page, "qr")
                print("QR_SAVED", (OUT / "qr.png").resolve())

            deadline = time.time() + MAX_WAIT
            last_beat = 0
            while time.time() < deadline:
                cookies = {c["name"] for c in ctx.cookies("https://weread.qq.com")}
                if "wr_skey" in cookies:
                    break
                if time.time() - last_beat > 10:
                    last_beat = time.time()
                    txt = ""
                    try:
                        txt = page.inner_text("body")[:200].replace("\n", " ")
                    except Exception:  # noqa: BLE001
                        pass
                    print("WAIT", int(deadline - time.time()), "|", txt[:120])
                    shot(page, "live")
                time.sleep(2)
            else:
                print("LOGIN_TIMEOUT")
                shot(page, "timeout")
                return 2

            print("LOGIN_OK")
            ctx.storage_state(path=str(STATE))

            page.goto("https://weread.qq.com/web/shelf", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            shot(page, "shelf")

            loc = page.locator('a[href*="/web/reader/"]')
            if loc.count() == 0:
                loc = page.locator('[class*="shelfBook"]')
            print("shelf entries:", loc.count(), "url:", page.url)
            if loc.count():
                loc.first.click()
                page.wait_for_timeout(6000)
                print("reader url:", page.url)
                shot(page, "reader")
                for i in range(3):
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(2500)
                    print("turn", i + 1)
                shot(page, "reader2")
            else:
                print("no book found on shelf")

            ctx.storage_state(path=str(STATE))
            dump({"records": records, "endpoints": sorted(seen)}, OUT / "xhr.json")
            dump(sorted(seen), OUT / "endpoints.json")
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass

    print(f"CAPTURED {len(records)} responses / {len(seen)} endpoints")
    for ep in sorted(seen):
        print("  ", ep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
