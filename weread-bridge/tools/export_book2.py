#!/usr/bin/env python3
"""导出微信读书书籍正文（顺序遍历版）。

用「上一章 / 下一章」按钮翻章：每次翻章，解密后的 HTML 都会通过 innerHTML
重新注入，我们在这个瞬间截获完整章节。绕开 canvas 渲染和正文加密。

用法：
    python tools/export_book2.py <reader_url> <out.json> [max_chapters]
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
        if (typeof v === 'string' && v.length > 800 && v.indexOf('data-wr-role="text"') >= 0) {
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
    # 逐字 span 去掉标签保留文字
    s = re.sub(r"<span[^>]*data-wr-role=\"text\"[^>]*>", "", s)
    s = re.sub(r"</span>", "", s)
    s = re.sub(r"</?span[^>]*>", "", s)
    # 只留少量属性
    s = re.sub(r"\s(?:data-wr[\w-]*|data-v-[\w-]+|style|id)=\"[^\"]*\"", "", s)
    s = re.sub(r"<p[^>]*>\s*</p>", "", s)
    s = re.sub(r"[ \t\r\n]+", " ", s)
    return s.strip()


def title_of(html: str, fallback: str) -> str:
    m = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", html, flags=re.S)
    if m:
        t = re.sub(r"<[^>]+>", "", m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            return t
    return fallback


def cap_count(page) -> int:
    return page.evaluate("() => (window.__cap || []).length")


def last_cap(page) -> str:
    return page.evaluate("() => { const a = window.__cap || []; return a.length ? a[a.length-1].html : ''; }")


def click_next(page, label: str) -> bool:
    try:
        loc = page.get_by_text(label, exact=True)
        if loc.count():
            loc.last.click(timeout=5000)
            return True
    except Exception as exc:  # noqa: BLE001
        print("click fail:", label, str(exc)[:80])
    return False


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    url, out_path = sys.argv[1], Path(sys.argv[2])
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 999

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.add_init_script(HOOK)
        page.goto(url, wait_until="commit", timeout=60000)
        page.wait_for_timeout(9000)
        print("loaded, caps:", cap_count(page))

        # 回退到第一章
        for _ in range(80):
            before = cap_count(page)
            if not click_next(page, "上一章"):
                break
            page.wait_for_timeout(1200)
            if cap_count(page) == before:
                break
        page.wait_for_timeout(1500)
        print("rewound, caps:", cap_count(page))

        chapters, seen_titles = [], set()
        for step in range(limit):
            html = last_cap(page)
            if not html:
                print("no capture at step", step)
                break
            clean = clean_html(html)
            title = title_of(html, f"第{step+1}节")
            if title in seen_titles:
                break
            seen_titles.add(title)
            chapters.append({"title": title, "html": clean})
            print(f"[{len(chapters)}] {title[:34]} ({len(clean)} chars)")

            before = cap_count(page)
            if not click_next(page, "下一章"):
                break
            ok = False
            for _ in range(16):
                page.wait_for_timeout(400)
                if cap_count(page) > before:
                    ok = True
                    break
            if not ok:
                print("no new capture after 下一章, stop")
                break

        book = {"source": url, "chapters": chapters}
        out_path.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
        print("saved", out_path, "chapters", len(chapters),
              "chars", sum(len(c["html"]) for c in chapters))
    return 0


if __name__ == "__main__":
    sys.exit(main())
