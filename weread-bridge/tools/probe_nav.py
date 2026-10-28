import os, re
from playwright.sync_api import sync_playwright
PORT = 9333
HOOK = r"""
window.__cap = [];
(() => {
  const d = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
  Object.defineProperty(Element.prototype, 'innerHTML', {
    configurable: true, enumerable: d.enumerable, get: d.get,
    set: function (v) {
      try { if (typeof v === 'string' && v.indexOf('data-wr-role="text"') >= 0)
        window.__cap.push({len: v.length, html: v}); } catch (e) {}
      return d.set.call(this, v);
    }
  });
})();
"""
def title(h):
    m = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", h or "", re.S)
    if not m: return "?"
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()[:40]

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    page.add_init_script(HOOK)
    page.goto("https://weread.qq.com/web/reader/843329f0728c8ee08434fb1", wait_until="commit", timeout=60000)
    page.wait_for_timeout(9000)
    print("url:", page.url)
    print("caps:", page.evaluate("() => window.__cap.length"), "| title:", title(page.evaluate("() => window.__cap.at(-1).html")))
    for i in range(3):
        loc = page.get_by_text("下一章", exact=True)
        print("next btn count:", loc.count())
        loc.last.click(timeout=5000)
        page.wait_for_timeout(2500)
        print(i, "->", page.url, "| caps:", page.evaluate("() => window.__cap.length"))
