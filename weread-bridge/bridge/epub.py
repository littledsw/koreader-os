"""EPUB 3 生成器（纯标准库，零依赖）。

输入是通用结构，不绑定微信读书：
    build_epub("out.epub", meta={...}, chapters=[{"title":..., "html":...}])

设计要点：
- mimetype 必须是压缩包第一个条目且不压缩（规范要求）。
- 同时写 nav.xhtml（EPUB3）和 toc.ncx（EPUB2 兼容），老固件也能读目录。
- 内置 Kobo 友好的排版 CSS：中文首行缩进 2em、两端对齐、行高 1.7。
"""

from __future__ import annotations

import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

STYLE = """html { font-size: 100%; }
body {
  font-family: "LXGW WenKai", "Liberation Sans", "Noto Sans CJK SC", serif;
  line-height: 1.7;
  margin: 0 0.4em;
  text-align: justify;
  -webkit-hyphens: none;
  hyphens: none;
}
p { text-indent: 2em; margin: 0.32em 0; }
p.noindent { text-indent: 0; }
h1, h2, h3 { text-indent: 0; font-weight: 600; line-height: 1.4;
  margin: 1.4em 0 0.9em; page-break-after: avoid; break-after: avoid; }
h1 { font-size: 1.3em; }
img { max-width: 100%; height: auto; }
blockquote { margin: 1em 1.2em; font-size: 0.95em; }
hr { border: 0; border-top: 1px solid #000; margin: 1.4em 0; }
"""

XHTML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}" lang="{lang}">
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="../style.css"/>
</head>
<body>
{body}
</body>
</html>
"""

NAV = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}" lang="{lang}">
<head><meta charset="utf-8"/><title>目录</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>目录</h1>
    <ol>
{items}
    </ol>
  </nav>
</body>
</html>
"""

NCX = """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{uid}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
{points}
  </navMap>
</ncx>
"""


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text.strip())
    return (s or "section")[:48]


def _xhtml(title: str, body_html: str, lang: str) -> str:
    return XHTML.format(lang=lang, title=escape(title), body=body_html)


def _chapters_dir(n: int) -> str:
    return f"chapter_{n:04d}.xhtml"


def build_epub(
    out_path: str | Path,
    *,
    title: str,
    chapters: list[dict],
    author: str = "",
    language: str = "zh-CN",
    identifier: str | None = None,
    cover: Path | None = None,
    css_extra: str = "",
) -> Path:
    """chapters: [{"title": str, "html": str}]，html 是正文片段（不含 <body>）。"""
    if not chapters:
        raise ValueError("chapters 不能为空")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    uid = identifier or f"urn:uuid:{uuid.uuid4()}"
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    files: list[tuple[str, str | bytes]] = []      # (path, content)
    manifest: list[str] = []
    spine: list[str] = []

    files.append(("OEBPS/style.css", STYLE + "\n" + css_extra))
    manifest.append('<item id="css" href="style.css" media-type="text/css"/>')

    nav_items, ncx_points = [], []
    for i, ch in enumerate(chapters, 1):
        name = _chapters_dir(i)
        cid = f"chap{i:04d}"
        files.append((f"OEBPS/{name}", _xhtml(ch["title"], ch["html"], language)))
        manifest.append(
            f'<item id="{cid}" href="{name}" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="{cid}"/>')
        nav_items.append(f'      <li><a href="{name}">{escape(ch["title"])}</a></li>')
        ncx_points.append(
            f'    <navPoint id="np{i}" playOrder="{i}">'
            f'<navLabel><text>{escape(ch["title"])}</text></navLabel>'
            f'<content src="{name}"/></navPoint>'
        )

    if cover and Path(cover).exists():
        suffix = Path(cover).suffix.lower().lstrip(".")
        mtype = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                 "png": "image/png", "gif": "image/gif"}.get(suffix, "image/jpeg")
        cname = f"cover.{suffix}"
        files.append((f"OEBPS/{cname}", Path(cover).read_bytes()))
        manifest.append(f'<item id="cover-img" href="{cname}" media-type="{mtype}" properties="cover-image"/>')

    files.append(("OEBPS/nav.xhtml", NAV.format(lang=language, items="\n".join(nav_items))))
    manifest.append(
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    )
    files.append(
        ("OEBPS/toc.ncx", NCX.format(uid=uid, title=escape(title), points="\n".join(ncx_points)))
    )
    manifest.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{escape(uid)}</dc:identifier>
    <dc:title>{escape(title)}</dc:title>
    <dc:language>{language}</dc:language>
    <dc:creator>{escape(author)}</dc:creator>
    <meta property="dcterms:modified">{modified}</meta>
  </metadata>
  <manifest>
    {"".join(chr(10) + "    " + m for m in manifest)}
  </manifest>
  <spine toc="ncx">
    {"".join(chr(10) + "    " + s for s in spine)}
  </spine>
</package>
"""
    files.append(("OEBPS/content.opf", opf))
    files.append(("META-INF/container.xml", CONTAINER))

    with zipfile.ZipFile(out_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for path, content in files:
            if isinstance(content, bytes):
                zf.writestr(path, content, compress_type=zipfile.ZIP_DEFLATED)
            else:
                zf.writestr(path, content, compress_type=zipfile.ZIP_DEFLATED)
    return out_path
