import os
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))
OUT = Path("capture")

GET = """() => {
  const el = document.querySelector('.readerChapterContent');
  const t = (document.querySelector('.readerTopBar_title, .readerChapterTitle, h1')||{}).innerText || '';
  return {text: el ? el.innerText : '', title: t};
}"""

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    a = page.evaluate(GET)
    print("start len", len(a["text"]), "title", a["title"][:40])

    for i in range(3):
        page.keyboard.press("ArrowRight"); page.wait_for_timeout(1800)
        c = page.evaluate(GET)
        print(f"  turn{i+1}: len={len(c['text'])} changed={c['text']!=a['text']} title={c['title'][:30]}")

    # 找下一章控件
    btns = page.evaluate("""() => {
      const out=[];
      document.querySelectorAll('button,div,span,a').forEach(el=>{
        const t=(el.innerText||'').trim();
        if(t && t.length<8 && /下一章|上一章|下一节/.test(t)) out.push({tag:el.tagName, cls:String(el.className).slice(0,40), t});
      });
      return out.slice(0,6);
    }""")
    print("nav btns:", btns)

    before = page.evaluate(GET)
    clicked = False
    try:
        loc = page.get_by_text("下一章", exact=True)
        if loc.count():
            loc.first.click(); clicked = True
    except Exception as e:
        print("click err", e)
    page.wait_for_timeout(3500)
    after = page.evaluate(GET)
    print("clicked", clicked, "| title", before["title"][:24], "->", after["title"][:24],
          "| len", len(before["text"]), "->", len(after["text"]))
    page.screenshot(path=str(OUT / "dom5.png"))
