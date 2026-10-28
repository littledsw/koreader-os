#!/bin/sh
# 下载霞鹜文楷 WebFont（约 30MB），供 demo 渲染使用
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)/demo/fonts"
mkdir -p "$DIR" && cd "$DIR"
URL="https://cdn.npmmirror.com/packages/lxgw-wenkai-webfont/1.7.0/lxgw-wenkai-webfont-1.7.0.tgz"
echo "downloading font package…"
curl -sSL -o pkg.tgz "$URL"
tar xzf pkg.tgz && rm -f pkg.tgz
echo "done: $DIR/package"
