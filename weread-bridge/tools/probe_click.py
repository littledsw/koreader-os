import os, json
from playwright.sync_api import sync_playwright
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
URL = "https://weread.qq.com/web/reader/843329f0728c8ee08434fb1"
HOOK = r"""
window.__nav = [];
(() => {
  const p = history.pushState;
  history.pushState = function(s,t,u){ window.__nav.push(String(u)); return p.apply(this, arguments); };
  const r = history.replaceState;
  history.replaceState = function(s,t,u){ window.__nav.push('R:'+String(u)); return r.apply(this, arguments); };
})();
"""
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    page.add_init_script(HOOK)
    page.goto(URL, wait_until="commit", timeout=60000)
    page.wait_for_timeout(8000)
    print("start url:", page.url)
    for idx in (5, 6):
        r = page.evaluate("""(i) => {
          const li = document.querySelectorAll('.readerCatalog_list_item')[i];
          if (!li) return 'no-item';
          li.click();
          return 'clicked';
        }""", idx)
        page.wait_for_timeout(4000)
        print(idx, r, "| url:", page.url, "| nav:", page.evaluate("() => (window.__nav||[]).slice(-2)"))
