import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.wait_for_timeout(2000)

    info = page.evaluate("""() => {
      const r = {};
      r.url = location.href;
      r.canvas = document.querySelectorAll('canvas').length;
      r.iframe = document.querySelectorAll('iframe').length;
      r.nodes = document.querySelectorAll('*').length;
      const big = [];
      document.querySelectorAll('div,section,article,main').forEach(el => {
        const t = el.textContent || '';
        if (t.length > 2000) big.push({cls: String(el.className).slice(0,50), len: t.length,
                                       head: t.slice(0,60).replace(/\\s+/g,' ')});
      });
      big.sort((a,b)=>b.len-a.len);
      r.big = big.slice(0,8);
      // 找可能的正文容器
      const cands = [];
      document.querySelectorAll('[class*="reader"],[class*="content"],[class*="chapter"]').forEach(el=>{
        const t = el.textContent || '';
        if (t.length > 300) cands.push({cls:String(el.className).slice(0,70), len:t.length});
      });
      cands.sort((a,b)=>b.len-a.len);
      r.cands = cands.slice(0,10);
      return r;
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=1)[:3000])

    html = page.content()
    OUT.joinpath("page.html").write_text(html, encoding="utf-8")
    print("html bytes", len(html))
    page.screenshot(path=str(OUT / "dom2.png"))
