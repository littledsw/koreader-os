#!/usr/bin/env python3
"""把 export_book3.py 的输出转成 EPUB。"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bridge.epub import build_epub

src, out = Path(sys.argv[1]), Path(sys.argv[2])
title = sys.argv[3] if len(sys.argv) > 3 else "未命名"
author = sys.argv[4] if len(sys.argv) > 4 else ""

book = json.loads(src.read_text())
chs = [c for c in book["chapters"] if len(c.get("html", "")) > 200]
print("chapters:", len(chs), "chars:", sum(len(c["html"]) for c in chs))
build_epub(out, title=title, author=author,
           chapters=[{"title": c["title"], "html": c["html"]} for c in chs])
print("built", out, out.stat().st_size, "bytes")
