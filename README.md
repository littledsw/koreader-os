# koreader-os

把一台 **Kobo Aura H2O（2014，6.8" / 1080×1430 / 16 灰阶）** 改造成自己的阅读器：
自建桌面 + KOReader 阅读引擎 + 微信读书桥接 + 雅思背单词。

> 现状：**设计稿与核心原型已完成，系统尚未上机。** 本仓库是 v0，用于把设计、方案、
> 以及微信读书抽取的可运行原型固定下来。

## 为什么不是"刷个 Android"

Kobo 跑的是 Linux，墨水屏靠 i.MX6 BSP 里的 `mxc_epdc_fb` 内核模块驱动，主线内核没有支持。
所以"换系统"的正确姿势是**保留原厂内核与驱动，只换上层**：

```
u-boot（原厂，不动）
 └ kernel（原厂，不动）
    └ 原厂 rootfs（只加一行 hook）
       └ 外置 SD 卡上的自建 rootfs → 自己的 init → Launcher
```

系统装在外置 microSD 上，**拔卡即回原厂**，不拆机、不碰内部存储分区。

微信读书是 Android APK，本机内核 3.0.35 + 512MB 内存跑不了，因此改走
**网页版桥接**：家庭服务器取正文 → 生成 EPUB → 设备按普通书阅读。

## 目录

```
docs/PLAN.md          完整施工方案：启动链、分区、刷新策略、风险与回退
hardware/probe.sh     M0 硬件探测脚本（只读，在 Kobo 上跑）
content/schema.md     三个词库包的字段规范
content/samples/      雅思词库 5 词样板（风格校准用）
demo/                 25 屏 UI 设计稿 + 渲染脚本 + 图库
weread-bridge/        微信读书 → EPUB / OPDS 桥接原型
tools/fetch_fonts.sh  取霞鹜文楷（demo 渲染用，不入库）
```

## 看设计稿

```bash
cd demo && python3 -m http.server 8765
# 浏览器打开 http://127.0.0.1:8765/gallery.html
```

25 屏覆盖：开机、书架、微信云端书架、导出、两类阅读、划线、笔记、目录、
单词卡、图鉴、单词本、搜索、离线与待同步状态。

`demo/flow2.html` 是唯一源文件，按 1080×1430 实际像素写；改完跑：

```bash
tools/fetch_fonts.sh                 # 首次需要
cd demo && python3 render_flow.py    # 需要 playwright + 系统 Chrome
```

## 微信读书桥接（原型）

```bash
cd weread-bridge
python3 -m venv .venv && . .venv/bin/activate
pip install playwright && playwright install chromium
python tools/login_flow.py            # 扫码登录，落 state.json
python tools/export_book3.py <reader_url> out.json
python tools/make_epub.py out.json book.epub "书名" "作者"
```

**已验证**：登录、书架、目录、划线、进度接口；章节正文可从 `innerHTML` 注入点截获；
能生成结构正确的 EPUB。

**未完成**：逐章遍历的稳健性（章末按钮会消失）、签名重放、批量导出。
`/web/book/read` 的进度回写字段已抓到（`b` 书 / `c` 章节 / `ci` 序号 / `co` 字符偏移），
签名 `s` 的算法待解；退路是让浏览器代发或只回写章节。

## 已知限制

- **语音输入不可能**：Aura H2O 没有麦克风、没有扬声器、没有蓝牙。
- **微信读书不是"装 App"**：是"把书搬过来读"。笔记与进度默认不回写账号；书城用不了。
- **非官方接入**：违反微信读书用户协议中关于自动化访问的条款，账号有被风控的风险。
- **彩色不可能**：16 级灰阶。图鉴照片按灰度处理。

## 安全

`weread-bridge/state.json` 等同于账号凭据，`capture/` 里是书籍正文与请求记录，
两者都已在 `.gitignore` 中，**不要提交、不要外发**。

## Roadmap

1. M0 硬件探测（需要设备）
2. M1 最小可启动 rootfs（SD 卡启动 → 显示 → 触摸 → 拔卡可回）
3. M2 Launcher + 简约主题
4. M3 KOReader 集成
5. M4 背单词 app（词根 / 造句批改 / 单词本 / 复习）
6. M5 内容包：雅思 3500、用英语讲中国、动物图鉴 300

## 素材授权

- 字体：霞鹜文楷（OFL 1.1），Arial 以 Liberation Sans 替代
- 动物照片：iNaturalist 开放数据，CC0 / CC BY，逐张署名见 `demo/assets/animals/CREDITS.json`
