import re, subprocess, sys, time, socket
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)
PORT = 8899

def open_(p):
    s = socket.socket(); s.settimeout(0.3)
    try: s.connect(("127.0.0.1", p)); return True
    except OSError: return False
    finally: s.close()

srv = None
if not open_(PORT):
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=str(ROOT),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if open_(PORT): break
        time.sleep(0.2)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1080, "height": 1430}, device_scale_factor=2)
        PAGE = sys.argv[1] if len(sys.argv) > 1 else "flow.html"
        pg.goto(f"http://127.0.0.1:{PORT}/{PAGE}", wait_until="networkidle")
        pg.evaluate("() => document.fonts.ready")
        pg.wait_for_timeout(2500)
        ids = pg.eval_on_selector_all(".screen", "els => els.map(e => e.id)")
        for i in ids:
            f = OUT / f"{i}.png"
            pg.locator(f"#{i}").screenshot(path=str(f))
            print(i, f.stat().st_size)
        b.close()
finally:
    if srv: srv.terminate()
