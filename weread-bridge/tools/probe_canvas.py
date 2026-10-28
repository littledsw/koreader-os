import os, json
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")
URL = "https://weread.qq.com/web/reader/843329f0728c8ee08434fb1"

HOOK = """
window.__draws = [];
window.__imgs = 0;
(() => {
  const P = CanvasRenderingContext2D.prototype;
  const ft = P.fillText;
  P.fillText = function(t, x, y, ...rest) {
    try { window.__draws.push({t: String(t), x: Math.round(x), y: Math.round(y), f: this.font}); } catch(e) {}
    return ft.call(this, t, x, y, ...rest);
  };
  const st = P.strokeText;
  P.strokeText = function(t, x, y, ...rest) {
    try { window.__draws.push({t: String(t), x: Math.round(x), y: Math.round(y), s:1}); } catch(e) {}
    return st.call(this, t, x, y, ...rest);
  };
  const di = P.drawImage;
  P.drawImage = function(...a) { window.__imgs++; return di.apply(this, a); };
})();
"""

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script(HOOK)
    page.goto(URL, wait_until="commit", timeout=60000)
    page.wait_for_timeout(10000)

    r = page.evaluate("""() => ({draws: (window.__draws||[]).length,
                                imgs: window.__imgs||0,
                                sample: (window.__draws||[]).slice(0,8)})""")
    print("fillText calls:", r["draws"], "| drawImage:", r["imgs"])
    print(json.dumps(r["sample"], ensure_ascii=False)[:600])

    c = page.evaluate("""() => {
      const cs = document.querySelectorAll('canvas');
      return {n: cs.length, sizes: Array.from(cs).slice(0,4).map(c => [c.width, c.height])};
    }""")
    print("canvases:", c)
    page.screenshot(path=str(OUT / "canvas.png"))
