import os, json
from pathlib import Path
from playwright.sync_api import sync_playwright
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    page.wait_for_timeout(1000)
    # 打开目录
    for sel in ('.readerControls_item', '[class*="catalog"]', 'button[class*="Catalog"]'):
        try:
            loc = page.locator(sel)
            if loc.count(): print("catalog trigger:", sel, loc.count())
        except Exception: pass
    info = page.evaluate("""() => {
      const cat = document.querySelector('.readerCatalog, [class*="readerCatalog"]');
      if (!cat) return {found:false};
      const items = cat.querySelectorAll('li, .readerCatalog_list_item, [class*="catalogItem"]');
      return {found:true, cls:String(cat.className).slice(0,60), items: items.length,
              sample: Array.from(items).slice(0,5).map(e => (e.innerText||'').slice(0,40))};
    }""")
    print(json.dumps(info, ensure_ascii=False)[:800])
    # 找所有可点的目录入口
    print(page.evaluate("""() => Array.from(document.querySelectorAll('button,div'))
       .filter(e => /目录/.test((e.innerText||'').trim()) && (e.innerText||'').trim().length < 6)
       .slice(0,5).map(e => ({tag:e.tagName, cls:String(e.className).slice(0,50)}))"""))
