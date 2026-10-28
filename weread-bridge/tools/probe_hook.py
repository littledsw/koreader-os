import os, json
from pathlib import Path
from playwright.sync_api import sync_playwright
PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")
URL = "https://weread.qq.com/web/reader/843329f0728c8ee08434fb1"

HOOK = r"""
window.__cap = {html: [], wasm: 0, parse: []};
(() => {
  const d = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
  if (d && d.set) {
    Object.defineProperty(Element.prototype, 'innerHTML', {
      configurable: true, enumerable: d.enumerable, get: d.get,
      set: function(v) {
        try { if (typeof v === 'string' && v.length > 1500) window.__cap.html.push(v.slice(0, 3000)); } catch(e){}
        return d.set.call(this, v);
      }
    });
  }
  const ps = DOMParser.prototype.parseFromString;
  DOMParser.prototype.parseFromString = function(s, t) {
    try { if (typeof s === 'string' && s.length > 1500) window.__cap.parse.push(s.slice(0, 3000)); } catch(e){}
    return ps.call(this, s, t);
  };
  const wa = WebAssembly.instantiate;
  WebAssembly.instantiate = function(...a) { window.__cap.wasm++; return wa.apply(this, a); };
})();
"""

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0]
    page.add_init_script(HOOK)
    page.goto(URL, wait_until="commit", timeout=60000)
    page.wait_for_timeout(9000)
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(5000)

    r = page.evaluate("""() => ({
      html: (window.__cap.html||[]).length,
      parse: (window.__cap.parse||[]).length,
      wasm: window.__cap.wasm||0,
      sampleHtml: (window.__cap.html||[]).slice(0,2),
      sampleParse: (window.__cap.parse||[]).slice(0,1)
    })""")
    print("captured html:", r["html"], "parse:", r["parse"], "wasm:", r["wasm"])
    for s in r["sampleHtml"]:
        print("HTML>>", s[:300].replace("\n", " "))
    for s in r["sampleParse"]:
        print("PARSE>>", s[:300].replace("\n", " "))
    page.screenshot(path=str(OUT / "hook.png"))
