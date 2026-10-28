import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path("capture"); out.mkdir(exist_ok=True)
logs, failed = [], []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="chrome")
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    pg = ctx.new_page()
    pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}"[:200]))
    pg.on("requestfailed", lambda r: failed.append(f"{r.url[:120]} :: {r.failure}"))
    try:
        resp = pg.goto("https://weread.qq.com/", wait_until="networkidle", timeout=45000)
        print("status:", resp.status if resp else None)
    except Exception as e:
        print("goto error:", type(e).__name__, str(e)[:300])
    pg.wait_for_timeout(3000)
    print("url:", pg.url)
    print("title:", pg.title())
    body = pg.inner_text("body")[:800] if pg.query_selector("body") else ""
    print("body:", body.replace("\n", " | ")[:600])
    pg.screenshot(path=str(out / "diag.png"), full_page=False)
    print("failed:", json.dumps(failed[:8], ensure_ascii=False))
    print("console:", json.dumps(logs[:8], ensure_ascii=False))
    ctx.close(); b.close()
print("shot:", out / "diag.png")
