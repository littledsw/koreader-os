import os, json
from pathlib import Path
from playwright.sync_api import sync_playwright
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0]
    page.goto("https://ink.qq.com", wait_until="commit", timeout=60000)
    page.wait_for_timeout(8000)
    print("url:", page.url, "| title:", page.title())
    info = page.evaluate("""() => ({
      nodes: document.querySelectorAll('*').length,
      canvases: document.querySelectorAll('canvas').length,
      textLen: document.body.innerText.length,
      head: document.body.innerText.slice(0,300).replace(/\\n/g,' | '),
      cookies: document.cookie.slice(0,200)
    })""")
    print(json.dumps(info, ensure_ascii=False, indent=1)[:1200])
    page.screenshot(path=str(OUT / "ink.png"))
