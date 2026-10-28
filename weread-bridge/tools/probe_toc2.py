import os, json
from playwright.sync_api import sync_playwright
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    out = page.evaluate("""() => {
      const items = document.querySelectorAll('.readerCatalog li, .readerCatalog [class*="catalogItem"]');
      const first = items[2];
      return {
        count: items.length,
        html: first ? first.outerHTML.slice(0, 700) : null,
        attrs: first ? Array.from(first.attributes).map(a => [a.name, a.value]) : null,
        url: location.href
      };
    }""")
    print(json.dumps(out, ensure_ascii=False, indent=1)[:1500])
