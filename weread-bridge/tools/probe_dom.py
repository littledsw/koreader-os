import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture"); OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://weread.qq.com/web/reader/843329f0728c8ee08434fb1",
              wait_until="commit", timeout=60000)
    page.wait_for_timeout(9000)

    info = page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('div,section,article').forEach(el => {
        const t = el.innerText || '';
        if (t.length > 800) out.push({cls: el.className && el.className.toString().slice(0,60),
                                      tag: el.tagName, len: t.length,
                                      head: t.slice(0,80).replace(/\\n/g,' ')});
      });
      out.sort((a,b) => b.len - a.len);
      return out.slice(0, 12);
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=1)[:2500])

    body = page.evaluate("() => document.body.innerText")
    print("BODY LEN", len(body))
    print("BODY HEAD:", body[:300].replace("\n", " | "))
    (OUT / "dom_body.txt").write_text(body, encoding="utf-8")
    page.screenshot(path=str(OUT / "dom.png"))
