from playwright.sync_api import sync_playwright
PORT = 9333
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    print("url0", page.url)
    loc = page.get_by_text("下一章", exact=True)
    print("count", loc.count())
    for i in range(loc.count()):
        try:
            el = loc.nth(i)
            print(i, el.evaluate("e => [e.tagName, e.className, e.offsetParent!==null, e.disabled]"))
        except Exception as e:
            print(i, "err", str(e)[:80])
    try:
        loc.last.click(timeout=5000)
        print("clicked ok")
    except Exception as e:
        print("click err:", str(e)[:300])
    page.wait_for_timeout(3000)
    print("url1", page.url)
