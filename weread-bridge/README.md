# weread-bridge

把微信读书网页版包成 **OPDS / EPUB 内容源**，让 Kobo 上的 KOReader
像访问普通书库一样访问微信读书。

```
Kobo: KOReader ── OPDS ──┐
                         ▼
              NAS / 树莓派 / Mac（常开）
              weread-bridge
                ├─ /login          二维码登录，cookie 持久化
                ├─ /opds           书架 / 分类 / 搜索
                ├─ /book/{id}.epub 按需生成 + 缓存
                └─ /progress       阅读位置回写（可选）
```

## 为什么不是"在 Kobo 上装微信读书"

Kobo 没有浏览器，也跑不了 Android（内核 3.0.35、单核、512MB）。
所以"包一层"只能发生在设备之外，设备端只接收 EPUB。

## 当前状态

| 模块 | 状态 |
|---|---|
| `tools/discover.py` 抓包定接口 | ✅ 可运行 |
| `bridge/epub.py` EPUB 生成 | ✅ 已自检 |
| `bridge/opds.py` OPDS feed | ✅ 已自检 |
| `bridge/client.py` 接口客户端 | ⏳ 等抓包结果 |
| `bridge/app.py` FastAPI 服务 | ⏳ 等抓包结果 |

## 第一步：用真浏览器抓一次包

已知（未登录实测，2026-10-28）这几个端点存在，只差登录态：

```
/web/book/info?bookId=          → {"errCode":-2010,"errMsg":"用户不存在"}
/web/shelf/sync                 → 同上
/web/book/bookmarklist?bookId=  → 同上
/web/book/readinfo?bookId=      → 同上
```

还差**章节正文**的端点和返回结构。抓包脚本会替你找出来。

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install playwright
playwright install chromium

python tools/discover.py
```

脚本会：

1. 弹出 Chromium，显示微信读书首页
2. 你扫码登录（脚本轮询 `wr_skey` cookie，最多等 5 分钟）
3. 自动进书架、点开第一本书、翻 3 页
4. 把**所有** `/web/*` 请求及其 JSON 响应写到 `capture/xhr.json`

跑完把 `capture/xhr.json` 给我，就能确定：

- 正文接口路径、参数（bookId / chapterUid / 是否需要 token）
- 正文是纯 HTML、还是分片、还是加密
- 书架、目录、划线的真实字段名

## 自检

```bash
python3 tools/selftest.py
# EPUB ok: 8 entries, 3082 bytes
# OPDS ok: nav 846B, acq 1001B
# ALL OK
```

## 安全

- `state.json` 等于你的登录凭据（cookie），**不要提交到 git、不要外发**。
- 建议单独用一个微信小号，或至少接受主力号被风控的可能。
- 服务只监听内网，出门用 Tailscale，不要暴露公网。

## 已知风险

- 非官方接入，违反《微信读书用户协议》中关于自动化访问的条款，账号可能被限制。
- 接口非公开，改版即失效，需要维护。
- 划线、想法、阅读时长不会计入你的微信读书账号。
- 服务器离线时读不了；`v0.5` 导出的本地 EPUB 不受影响。
