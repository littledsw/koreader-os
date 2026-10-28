from playwright.sync_api import sync_playwright
PORT = 9333
JS = """(label) => {
  const btns = Array.from(document.querySelectorAll('button,div[class*=Footer],div[class*=footer]'));
  const hit = btns.filter(b => (b.innerText||'').trim() === label);
  if (!hit.length) return 'none';
  hit[hit.length-1].click();
  return hit.length;
}"""
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    print("url0", page.url)
    print("js click:", page.evaluate(JS, "下一章"))
    page.wait_for_timeout(3000)
    print("url1", page.url)
    print("js click:", page.evaluate(JS, "上一章"))
    page.wait_for_timeout(3000)
    print("url2", page.url)
