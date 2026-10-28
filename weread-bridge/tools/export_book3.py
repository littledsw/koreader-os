#!/usr/bin/env python3
"""导出微信读书书籍正文（URL 驱动版，最稳）。

观察：每次翻章，reader URL 会变成 ...k<chapterKey>，同时解密后的 HTML
通过 innerHTML 重新注入。以 URL 变化作为「翻章完成」的判据，再取最新注入。

用法：
    python tools/export_book3.py <reader_url> <out.json>
"""

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PORT = 9333
HOOK = r"""
window.__cap = [];
(() => {
  const d = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
  if (!d || !d.set) return;
  Object.defineProperty(Element.prototype, 'innerHTML', {
    configurable: true, enumerable: d.enumerable, get: d.get,
    set: function (v) {
      try {
        if (typeof v === 'string' && v.length > 600 && v.indexOf('data-wr-role="text"') >= 0) {
          window.__cap.push({t: Date.now(), len: v.length, html: v});
        }
      } catch (e) {}
      return d.set.call(this, v);
    }
  });
})();
"""


def clean_html(raw: str) -> str:
    s = raw
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<span[^>]*data-wr-role=\"text\"[^>]*>", "", s)
    s = re.sub(r"</span>", "", s)
    s = re.sub(r"</?span[^>]*>", "", s)
    s = re.sub(r"\s(?:data-wr[\w-]*|data-v-[\w-]+|style|id)=\"[^\"]*\"", "", s)
    s = re.sub(r"<p[^>]*>\s*</p>", "", s)
    s = re.sub(r"[ \t\r\n]+", " ", s)
    return s.strip()


def title_of(html: str, fallback: str = "") -> str:
    m = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", html or "", flags=re.S)
    if m:
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
        if t:
            return t
    return fallback


def caps(page) -> int:
    return page.evaluate("() => (window.__cap || []).length")


def last_html(page) -> str:
    return page.evaluate("() => { const a = window.__cap||[]; return a.length ? a[a.length-1].html : ''; }")


def advance(page, label: str, prev_url: str) -> bool:
    """点翻章按钮，直到 URL 真的变化。失败会重试并尝试唤出底部控件。"""
    for _ in range(5):
        try:
            loc = page.get_by_text(label, exact=True)
            if loc.count() == 0:
                page.mouse.move(640, 520)
                page.wait_for_timeout(400)
                continue
            loc.last.click(timeout=5000)
        except Exception as exc:  # noqa: BLE001
            print("   click err:", str(exc).split("\n")[0][:90])
            page.mouse.move(640, 520)
            page.wait_for_timeout(500)
            continue
        for _ in range(20):
            page.wait_for_timeout(300)
            if page.url != prev_url:
                return True
    return False


def key_of(url: str) -> str:
    m = re.search(r"/web/reader/([^/]+)$", url)
    return m.group(1) if m else url


def walk(page, label: str, direction: str, store: dict):
    """向一个方向逐章走，直到 URL 不再变化。"""
    for _ in range(300):
        url = page.url
        before = caps(page)
        if not advance(page, label, url):
            print("  stop:", label, "no url change")
            return
        for _ in range(24):
            page.wait_for_timeout(350)
            if caps(page) > before:
                break
        html = last_html(page)
        k = key_of(page.url)
        title = title_of(html, k[:12])
        if k not in store:
            store[k] = {"title": title, "html": clean_html(html), "url": page.url}
            print(f"  {direction} +{len(store)} {title[:34]} ({len(store[k]['html'])} chars)")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    url, out_path = sys.argv[1], Path(sys.argv[2])

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.add_init_script(HOOK)
        page.goto(url, wait_until="commit", timeout=60000)
        page.wait_for_timeout(9000)

        store = {}
        k = key_of(page.url)
        html = last_html(page)
        store[k] = {"title": title_of(html, "起始章"), "html": clean_html(html), "url": page.url}
        print("start:", store[k]["title"], len(store[k]["html"]))

        print("forward…")
        walk(page, "下一章", "fwd", store)
        print("backward…")
        walk(page, "上一章", "back", store)

        chapters = [v for v in store.values() if v["html"].strip()]
        book = {"source": url, "chapters": chapters}
        out_path.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
        print("saved", out_path, "| chapters", len(chapters),
              "| chars", sum(len(c["html"]) for c in chapters))
    return 0


if __name__ == "__main__":
    sys.exit(main())
