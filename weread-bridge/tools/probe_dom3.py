import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")

JS = """() => {
  const el = document.querySelector('.readerChapterContent');
  if (!el) return null;
  return {html: el.innerHTML, text: el.innerText,
          paras: el.querySelectorAll('p').length,
          title: (document.querySelector('.readerChapterContent h1, .readerChapterContent h2')||{}).innerText || ''};
}"""

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.wait_for_timeout(1500)

    d1 = page.evaluate(JS)
    print("paras:", d1["paras"], "textlen:", len(d1["text"]))
    print("HEAD:", d1["text"][:200].replace("\n", " | "))
    OUT.joinpath("chapter1.html").write_text(d1["html"], encoding="utf-8")

    for i in range(2):
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(2500)
        d2 = page.evaluate(JS)
        same = d2["text"] == d1["text"]
        print(f"after turn {i+1}: textlen={len(d2['text'])} same_as_before={same} "
              f"tail={d2['text'][-60:].replace(chr(10),' ')!r}")
    page.screenshot(path=str(OUT / "dom3.png"))
