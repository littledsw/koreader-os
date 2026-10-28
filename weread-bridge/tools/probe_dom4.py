import json, os, time
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")
URL = "https://weread.qq.com/web/reader/843329f0728c8ee08434fb1"

def state(page):
    return page.evaluate("""() => {
      const el = document.querySelector('.readerChapterContent');
      return {has: !!el, len: el ? (el.innerText||'').length : 0,
              body: document.body.innerText.slice(0,120).replace(/\\n/g,' | ')};
    }""")

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(URL, wait_until="commit", timeout=60000)
    for i in range(10):
        page.wait_for_timeout(1500)
        s = state(page)
        print(i, s["has"], s["len"], "|", s["body"][:90])
        if s["len"] > 100:
            break
        if i == 3:
            for t in ("开始阅读", "继续阅读", "立即阅读"):
                try:
                    loc = page.get_by_text(t, exact=True)
                    if loc.count():
                        print("click", t); loc.first.click(); break
                except Exception: pass
    page.screenshot(path=str(OUT / "dom4.png"))
    s = state(page)
    if s["len"] > 100:
        html = page.evaluate("() => document.querySelector('.readerChapterContent').innerHTML")
        txt = page.evaluate("() => document.querySelector('.readerChapterContent').innerText")
        OUT.joinpath("chapter1.html").write_text(html, encoding="utf-8")
        print("SAVED chapter1.html", len(html), "text", len(txt))
        print("HEAD:", txt[:160].replace("\n"," | "))
