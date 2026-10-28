#!/usr/bin/env python3
"""零依赖自检：生成一个 EPUB 和两个 OPDS feed，校验结构。"""
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bridge.epub import build_epub          # noqa: E402
from bridge.opds import acquisition_feed, navigation_feed  # noqa: E402

tmp = Path(tempfile.mkdtemp())
epub = tmp / "t.epub"

build_epub(
    epub,
    title="自检样书",
    author="bridge",
    chapters=[
        {"title": "第一章 开端", "html": "<h1>第一章</h1><p>第一段。</p><p>第二段。</p>"},
        {"title": "第二章 转折", "html": "<h1>第二章</h1><p>又一段。</p>"},
    ],
)

with zipfile.ZipFile(epub) as z:
    names = z.namelist()
    assert names[0] == "mimetype", names[:3]
    assert z.read("mimetype") == b"application/epub+zip"
    opf = z.read("OEBPS/content.opf").decode()
    assert opf.count("<itemref") == 2, opf
    assert "dcterms:modified" in opf
    assert "OEBPS/nav.xhtml" in names and "OEBPS/toc.ncx" in names
    nav = z.read("OEBPS/nav.xhtml").decode()
    assert "第一章" in nav
    print(f"EPUB ok: {len(names)} entries, {epub.stat().st_size} bytes")

nav_feed = navigation_feed(
    title="微信读书", feed_id="urn:weread:root", self_href="/opds",
    start_href="/opds", entries=[{"title": "书架", "href": "/opds/shelf"}],
)
acq = acquisition_feed(
    title="书架", feed_id="urn:weread:shelf", self_href="/opds/shelf",
    start_href="/opds",
    books=[{"id": "urn:weread:1", "title": "某本书", "author": "某人",
            "epub_href": "/book/1.epub", "cover_href": "/cover/1.jpg"}],
)
assert nav_feed.startswith("<?xml") and "kind=navigation" in nav_feed
assert "application/epub+zip" in acq
print(f"OPDS ok: nav {len(nav_feed)}B, acq {len(acq)}B")
print("ALL OK")
