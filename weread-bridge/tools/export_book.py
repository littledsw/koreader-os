#!/usr/bin/env python3
"""把微信读书某本书的章节正文导出成 JSON（供 EPUB 生成器使用）。

原理：正文被渲染进 canvas，但解密后的 HTML 会先通过 innerHTML 注入。
在注入瞬间截获完整章节 HTML，绕过 canvas 与加密。

用法：
    python tools/export_book.py <reader_url> <out.json> [start] [end]

注意：需要登录态（复用 .chrome-profile 里的 Chrome）。
"""

import json
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PORT = int(os.environ.get("WR_CDP_PORT", "9333"))

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
          window.__cap.push({t: Date.now(), html: v});
        }
      } catch (e) {}
      return d.set.call(this, v);
    }
  });
})();
"""


def clean_html(raw: str) -> str:
    """把逐字 span 还原成干净段落。"""
    s = raw
    # 去掉逐字 span（保留内容）
    s = re.sub(r"<span[^>]*data-wr-role=\"text\"[^>]*>", "", s)
    s = re.sub(r"</span>", "", s)
    # 其余 span 整个去掉
    s = re.sub(r"<span[^>]*>", "", s)
    s = s.replace("</span>", "")
    # 去注释
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    # 属性只留 class（用于标题级别）
    s = re.sub(r"\s(?:data-wr[\w-]*|style|id|data-v-[\w-]+)=\"[^\"]*\"", "", s)
    # 合并空段落
    s = re.sub(r"<p[^>]*>\s*</p>", "", s)
    # 合并多余空白但保留标签
    s = re.sub(r"[ \t\r\n]+", " ", s)
    return s.strip()


def chapter_title(raw: str, fallback: str) -> str:
    m = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw, flags=re.S)
    if m:
        t = re.sub(r"<[^>]+>", "", m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            return t
    return fallback


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    url = sys.argv[1]
    out_path = Path(sys.argv[2])
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    end = int(sys.argv[4]) if len(sys.argv) > 4 else None

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.add_init_script(HOOK)
        page.goto(url, wait_until="commit", timeout=60000)
        page.wait_for_timeout(8000)

        items = page.evaluate(
            "() => Array.from(document.querySelectorAll('.readerCatalog_list_item'))"
            ".map(e => (e.innerText||'').trim())"
        )
        print("catalog items:", len(items))
        total = len(items)
        end = total if end is None else min(end, total)

        chapters = []
        for i in range(start, end):
            before = page.evaluate("() => (window.__cap||[]).length")
            ok = page.evaluate(
                "(i) => { const a = document.querySelectorAll('.readerCatalog_list_item');"
                " if (!a[i]) return false; a[i].querySelector('div').click(); return true; }", i
            )
            if not ok:
                print(i, "click failed")
                continue
            got = None
            for _ in range(24):
                page.wait_for_timeout(500)
                now = page.evaluate("() => (window.__cap||[]).length")
                if now > before:
                    got = page.evaluate("() => window.__cap[window.__cap.length-1].html")
                    break
            href = page.evaluate("() => location.href")
            title = chapter_title(got or "", items[i])
            chapters.append({"idx": i, "toc_title": items[i], "title": title,
                             "href": href, "raw_len": len(got or ""),
                             "html": clean_html(got or "")})
            print(f"[{i+1}/{end}] {title[:30]} raw={len(got or '')} clean={len(chapters[-1]['html'])}")

        book = {"source": url, "chapters": chapters}
        out_path.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
        print("saved", out_path, "chapters", len(chapters),
              "total chars", sum(len(c["html"]) for c in chapters))
    return 0


if __name__ == "__main__":
    sys.exit(main())
