"""OPDS 1.2 生成（纯字符串模板）。

KOReader 自带 OPDS 浏览器，所以 Kobo 端零改动：
    OPDS 目录 → 下载 EPUB → 原生排版阅读。
"""

from __future__ import annotations

from datetime import datetime, timezone
from xml.sax.saxutils import escape, quoteattr

NAV_TYPE = "application/atom+xml;profile=opds-catalog;kind=navigation"
ACQ_TYPE = "application/atom+xml;profile=opds-catalog;kind=acquisition"

HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opds="http://opds-spec.org/2010/catalog"
      xmlns:dc="http://purl.org/dc/terms/"
      xmlns:thr="http://purl.org/syndication/thread/1.0">
  <id>{feed_id}</id>
  <title>{title}</title>
  <updated>{updated}</updated>
  <link rel="self" href={self_href} type="{self_type}"/>
  <link rel="start" href={start_href} type="{nav_type}"/>
  <author><name>{author}</name></author>
"""

FOOT = "</feed>\n"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def navigation_feed(
    *,
    title: str,
    feed_id: str,
    self_href: str,
    start_href: str,
    entries: list[dict],
    author: str = "weread-bridge",
) -> str:
    """entries: [{"title":..., "href":..., "description":...}]"""
    out = [HEAD.format(
        feed_id=escape(feed_id), title=escape(title), updated=_now(),
        self_href=quoteattr(self_href), self_type=NAV_TYPE,
        start_href=quoteattr(start_href), nav_type=NAV_TYPE, author=escape(author),
    )]
    for i, e in enumerate(entries):
        out.append(f"""  <entry>
    <title>{escape(e['title'])}</title>
    <id>{escape(feed_id)}#{i}</id>
    <updated>{_now()}</updated>
    <content type="text">{escape(e.get('description', ''))}</content>
    <link rel="subsection" href={quoteattr(e['href'])} type="{NAV_TYPE}"/>
  </entry>
""")
    out.append(FOOT)
    return "".join(out)


def acquisition_feed(
    *,
    title: str,
    feed_id: str,
    self_href: str,
    start_href: str,
    books: list[dict],
    author: str = "weread-bridge",
) -> str:
    """books: [{"id","title","author","updated","cover_href","epub_href","summary","language"}]"""
    out = [HEAD.format(
        feed_id=escape(feed_id), title=escape(title), updated=_now(),
        self_href=quoteattr(self_href), self_type=ACQ_TYPE,
        start_href=quoteattr(start_href), nav_type=NAV_TYPE, author=escape(author),
    )]
    for b in books:
        cover = ""
        if b.get("cover_href"):
            cover = (f'    <link rel="http://opds-spec.org/image" '
                     f'href={quoteattr(b["cover_href"])} type="image/jpeg"/>\n')
        out.append(f"""  <entry>
    <title>{escape(b['title'])}</title>
    <id>{escape(b['id'])}</id>
    <updated>{b.get('updated') or _now()}</updated>
    <author><name>{escape(b.get('author', ''))}</name></author>
    <dc:language>{escape(b.get('language', 'zh-CN'))}</dc:language>
    <content type="text">{escape(b.get('summary', ''))}</content>
{cover}    <link rel="http://opds-spec.org/acquisition" href={quoteattr(b['epub_href'])}
          type="application/epub+zip"/>
  </entry>
""")
    out.append(FOOT)
    return "".join(out)
