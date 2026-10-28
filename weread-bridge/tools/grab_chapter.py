import base64, json, os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("capture"); OUT.mkdir(exist_ok=True)
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    got = []

    def on_resp(r):
        if "/web/book/chapter/" not in r.url:
            return
        try:
            body = r.body()
        except Exception as e:
            print("body err", e); return
        hdrs = r.headers
        got.append({"url": r.url, "req": r.request.post_data, "headers": hdrs,
                    "len": len(body), "b64": base64.b64encode(body).decode()})
        print("CHAPTER", len(body), "bytes | ctype:", hdrs.get("content-type"))
        print("  head:", body[:120])

    page.on("response", on_resp)
    page.goto("https://weread.qq.com/web/reader/843329f0728c8ee08434fb1",
              wait_until="commit", timeout=60000)
    page.wait_for_timeout(8000)
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(5000)

    (OUT / "chapter_raw.json").write_text(json.dumps(got, ensure_ascii=False), encoding="utf-8")
    print("saved", OUT / "chapter_raw.json", "count", len(got))
