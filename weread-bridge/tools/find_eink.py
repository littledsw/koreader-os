import os, json
from playwright.sync_api import sync_playwright
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    page.goto("https://weread.qq.com/web/shelf", wait_until="commit", timeout=60000)
    page.wait_for_timeout(6000)
    links = page.evaluate("""() => {
      const out=[];
      document.querySelectorAll('a').forEach(a=>{
        const t=(a.innerText||'').trim();
        if (t && t.length<12) out.push({t, href:a.getAttribute('href')});
      });
      return out.slice(0,40);
    }""")
    print(json.dumps(links, ensure_ascii=False, indent=1)[:1500])
    # 直接看头部导航文本里的链接
    print(page.evaluate("""() => Array.from(document.querySelectorAll('a,span,div'))
        .filter(e => /墨水屏/.test(e.innerText||''))
        .slice(0,6).map(e => ({tag:e.tagName, cls:String(e.className).slice(0,40), href:e.getAttribute&&e.getAttribute('href'), t:(e.innerText||'').slice(0,20)}))"""))
