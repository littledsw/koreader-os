import os
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    page.wait_for_timeout(2000)

    print("main url:", page.url)
    for i, f in enumerate(page.frames):
        try:
            info = f.evaluate("""() => {
              const el = document.querySelector('.readerChapterContent');
              const all = document.body ? document.body.innerText : '';
              return {url: location.href, nodes: document.querySelectorAll('*').length,
                      bodyLen: all.length, contentLen: el ? el.innerText.length : -1,
                      head: all.slice(0,80).replace(/\\n/g,' | ')};
            }""")
            print(f"frame[{i}]", info)
        except Exception as e:
            print(f"frame[{i}] err", str(e)[:80])

    info = page.evaluate("""() => {
      const r = {roleText: 0, roleSample: ''};
      const els = document.querySelectorAll('[data-wr-role="text"]');
      r.roleText = els.length;
      let best = null;
      els.forEach(e => { if (!best || e.innerText.length > best.innerText.length) best = e; });
      if (best) { r.bestCls = String(best.className).slice(0,60); r.bestLen = best.innerText.length;
                  r.roleSample = best.innerText.slice(0,120); }
      const cc = document.querySelectorAll('[class*="ChapterContent"]');
      r.ccCount = cc.length;
      r.ccLens = Array.from(cc).slice(0,5).map(e => ({cls: String(e.className).slice(0,50), len: e.innerText.length}));
      return r;
    }""")
    print(info)
