from playwright.sync_api import sync_playwright
PORT = 9333
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = b.contexts[0]; page = ctx.pages[0]
    print("url0", page.url)
    page.keyboard.press("ArrowRight"); page.wait_for_timeout(2500)
    print("after Right", page.url)
    page.keyboard.press("ArrowRight"); page.wait_for_timeout(2500)
    print("after Right", page.url)
    page.keyboard.press("ArrowLeft"); page.wait_for_timeout(2500)
    print("after Left", page.url)
