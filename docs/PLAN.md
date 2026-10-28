# Kobo Aura H2O (2014) 自定义 OS — 施工方案 v0.1

目标：把 Aura H2O 一代改造成一台"自己的"阅读器 —— 开机是自己的极简桌面，
内置 KOReader 阅读引擎、雅思背单词、动物图鉴、AI 造句批改、
中文楷体 + 英文 Arial 系字体。

约束：**不拆机**、可回退、微信读书不在本机实现（见 §7）。

---

## 1. 硬件事实（待 M0 探测确认）

| 项 | 值 |
|---|---|
| SoC | Freescale i.MX6 SoloLite，Cortex-A9 单核 1GHz，512MB RAM |
| 屏 | 6.8" E Ink Carta，1080×1430，16 灰阶，265ppi |
| 存储 | 内部 4GB（实为 microSD）+ 外置 microSD 槽 |
| 无线 | 2.4G WiFi；**无蓝牙、无麦克风、无扬声器** |
| 其他 | 前光、电容触摸、IP67、无安全启动（u-boot 开放） |
| 内核 | Kobo BSP 3.0.35（连同 EPDC 驱动） |

## 2. L3 的正确装法：系统放外置 SD 卡

"换整个 rootfs" 不等于"刷机"。真正危险的只有两件事：改 u-boot、改内部存储分区。
两者都不做，于是：

```
u-boot(原厂,不动)
  └─ kernel(原厂,不动) ── 内置 EPDC/触摸/前光/电源驱动
       └─ 原厂 rootfs(不动) ── /etc/init.d/rcS 末尾加一行(5KB hook)
            └─ mount /dev/mmcblk1p2  (外置 SD 的系统分区)
                 └─ pivot_root → 我们的 init → Launcher
```

- 系统装在外置 microSD 的 ext4 分区，内部 4GB 完全不动。
- 回退：**拔掉 SD 卡**，原厂系统照常启动。没有拆机、没有刷 recovery。
- 原厂 rootfs 只多一行调用；hook 脚本本体放在 FAT 分区（`/mnt/onboard/.kobo/`），
  用户可见、可改、可删。
- 内核模块/固件从原厂 rootfs 只读挂到 `/stock`，保证版本永远匹配。

分区方案（外置 SD，≥16GB）：

| 分区 | 格式 | 大小 | 用途 |
|---|---|---|---|
| p1 | FAT32 | 剩余 | 书库，原厂固件也能读，插电脑直接拷书 |
| p2 | ext4 | 2–3GB | 我们的 rootfs |

## 3. 软件栈

- **构建**：Buildroot，target `armv7a` / Cortex-A9 / `-mfpu=vfpv3-d16`（不用 NEON，
  兼容性优先）/ hard-float，与 KOReader 官方 Kobo 包 ABI 一致。
- **init**：busybox init + 自写 rcS。
- **图形**：直接 `/dev/fb0` + `MXCFB_SEND_UPDATE` ioctl，不装 X/Wayland。
- **UI**：LVGL 9 + FreeType + libpng。
- **数据**：SQLite3。
- **网络**：wpa_supplicant + udhcpc + libcurl + ca-certificates。
- **阅读**：KOReader（Kobo 版，原样复用，作为子进程，退出回 Launcher）。
- **字体**：霞鹜文楷（子集：GB2312 + 词表）+ Liberation Sans + 少量符号。
- **休眠**：`/sys/power/state`，按键唤醒。

刷新策略（e-ink 关键）：

| 场景 | 波形 | 备注 |
|---|---|---|
| 翻页、界面切换 | GC16 | 全刷，干净 |
| 打字、滚动 | DU / A2 | 快，会残影 |
| 每 N 次局部刷 | GC16 强制 | 清残影，N 可配 |
| 关机/锁屏 | 全屏 GC16 | 顺带清屏 |

## 4. 里程碑

| 阶段 | 内容 | 验收 | 工期 |
|---|---|---|---|
| **M0** | 探测（SSH 采集硬件档案） | `hardware-profile.json` | 0.5 天 |
| **M1** | 最小可启动 rootfs | SD 启动 → 显示图片 → 触摸/按键/亮度/休眠可用，拔卡回原厂 | 2 周 |
| **M2** | Launcher + 简约主题 | 书架/继续阅读/设置，视觉规范落地 | 2 周 |
| **M3** | KOReader 集成 | 启动/退出/书库/进度/字典 | 1 周 |
| **M4** | 背单词 app | 卡片/词根/图鉴/单词本/造句/SM-2/FSRS/AI 批改 | 2–3 周 |
| **M5** | 内容包（并行） | 雅思 3500 / 中国专题 / 动物 300 | 与 M2–M4 并行 |

## 5. 视觉规范（简约风）

- 16 灰阶只用 0 / 30% / 100% 三档，不用渐变。
- 单栏、大留白，正文左右边距 ≥ 8%。
- 分隔用 1px 细线或纯留白，不用卡片阴影/圆角。
- 封面灰度化 + 1px 描边；无封面时用字标占位。
- 状态栏只留：时间、电量、进度。
- 中文字体文楷，英文 Liberation Sans；UI 字号 3 档（小 18 / 中 22 / 大 28 px）。

## 6. 内容管线（三个包）

1. **雅思核心 3500**：按话题分组，词根成族。
2. **用英语讲中国**：历史 / 名胜 / 文化 / 当代，每单元 20–30 词 + 250 词范文 + 中译。
3. **动物图鉴 300**：公有领域线描/版画，1-bit 或 16 灰阶高对比。

流程：schema 校验（JSON Schema）→ 自动核对（IPA 对 CMUdict、同反义对 WordNet、
去重）→ 抽检（词根故事必须人工过）→ 打包 SQLite。
字段定义见 `content/schema.md`，风格样板见 `content/samples/ielts_sample.json`。

## 7. 微信读书：本机不实现，但可以"桥接"

`com.tencent.weread.eink` 是 Android APK，需要 ART + Android 框架。
本机内核 3.0.35 无 binderfs，单核 + 512MB 无法承载 Android 运行时。
Anbox / Waydroid 两条路都堵死。

替代方案：**在家庭服务器上把网页版包成内容源**，Kobo 只当瘦客户端（详见 §11）。
设备端零改动，KOReader 自带 OPDS 浏览器就能吃。这条路绕开了 Android，
但代价是依赖一台常开设备，且属于非官方接入（见 §11 风险）。

## 8. AI 造句批改

全部走 **OpenAI 兼容接口**，provider 可配、可降级：

| 优先 | Provider | 模型 | 备注 |
|---|---|---|---|
| 1 | 智谱开放平台 | `glm-4-flash` | 免费、国内直连、中文解释好 |
| 2 | Google AI Studio | `gemini-2.0-flash` | 免费额度大，需外网 |
| 3 | Groq | `llama-3.1-8b-instant` | 免费、极快，英文语法够用 |
| 4 | OpenRouter | `*:free` | 兜底 |

免费额度政策变动频繁，所以客户端只认 `base_url / model / api_key` 三项配置，
换模型不改代码。请求返回严格 JSON：

```json
{
  "corrected": "…",
  "issues": [{"type": "grammar|word-choice|collocation|spelling",
              "original": "…", "suggestion": "…", "explain_zh": "…"}],
  "band_estimate": 5.5,
  "rewrite_band7": "…"
}
```

离线时入队，WiFi 恢复后补批；结果本地缓存，不重复花钱。

## 9. 风险与回退

| 风险 | 处置 |
|---|---|
| hook 写坏 | 拔 SD 卡 → 原厂启动 |
| 模块版本不匹配 | 从 `/stock` 只读挂载取 |
| 屏残影 | 波形策略表 + 定期全刷 |
| 续航变差 | 默认 suspend，禁止常亮 |
| 变砖 | 不写 u-boot、不碰内部存储分区，理论上不可达 |

## 10. 明确不做

- 不改 u-boot / 不改内核 / 不刷 recovery / 不拆机。
- 不实现 Android 兼容层。
- 不做中文输入法（造句用英文，ASCII 键盘）。
- 不做语音输入/朗读（无麦克风、无扬声器、无蓝牙）。

## 11. 微信读书桥接（新增）

### 11.1 为什么"包一层"必须发生在设备之外

Kobo 上没有可用浏览器（无 X/Wayland，内核对 Chromium 来说太老，512MB 也跑不动）。
所以设备端能拿到的只有两种东西：

1. **位图**：服务器跑真浏览器，截图回传 —— 远端浏览器模式。
2. **文本**：服务器把章节抽出来，生成 EPUB —— 内容桥模式。

### 11.2 接口现状（2026-10-28 实测，未登录）

| 端点 | 结果 | 含义 |
|---|---|---|
| `GET /web/book/info?bookId=` | 200 `{"errCode":-2010,"errMsg":"用户不存在"}` | 路由存在，需登录 |
| `GET /web/shelf/sync` | 同上 | 书架可拉 |
| `GET /web/book/bookmarklist?bookId=` | 同上 | 划线/书签可拉 |
| `GET /web/book/readinfo?bookId=` | 同上 | 阅读进度可读写 |
| `GET /web/book/chapterContent` | 404 | 章节正文路由待登录后从 XHR 里确认 |

`weread.qq.com` 是 Nuxt SPA，登录态靠 cookie。
**待验证**：章节正文的实际端点与返回格式（是否分片、是否混淆）。

### 11.3 推荐架构：OPDS / EPUB 桥

```
Kobo: KOReader ── OPDS ──┐
                         ▼
              家庭常开设备（Mac / NAS / 树莓派）
              weread-bridge (FastAPI + Playwright)
                ├─ /login   二维码登录，cookie 持久化
                ├─ /opds    书架、分类、搜索（原生目录）
                ├─ /book/{id}.epub  按需生成 + 缓存
                └─ /progress  位置回写（可选）
```

阅读动线：KOReader 里打开"微信读书"目录 → 选书 → 下载 EPUB → 用原生排版读
（楷体/Arial、划线、词典、生词本全部可用）。退出时回传位置。
**优点**：文字是原生的，不是位图；可离线（缓存后）；和背单词插件天然打通。
**缺点**：划线/想法留在本地，除非调接口回写；依赖服务器；接口会随版本变。

### 11.4 备选：远端浏览器（兜底）

服务器跑 Playwright，视口固定 1080×1430，关动画，渲染成 1-bit PNG 回传，
点击坐标回传。用于漫画、复杂版式、购买、登录等 EPUB 桥覆盖不到的场景。
代价：每翻一页一次往返，Wi-Fi 常开，续航明显下降。

### 11.5 分级推进

| 版本 | 内容 | 工期 |
|---|---|---|
| v0.5 | 导出脚本：把书架上的书抓成 EPUB 丢进 Kobo，离线读，不依赖服务器 | 3–5 天 |
| v1 | OPDS 桥：在线书架、按需生成、进度回写 | 2–3 周 |
| v2 | 远端浏览器兜底 | 1 周 |

### 11.6 风险

- **协议风险**：属于非官方接入，违反《微信读书用户协议》中关于自动化访问的条款，
  账号可能被风控/限制。仅个人自用，不传播、不商用。
- **接口风险**：非公开 API，QQ 侧改版即失效，需要长期维护。
- **体验风险**：划线、想法、阅读时长不计入微信读书账号；手机端进度不同步（除非回写）。
- **可用性风险**：服务器不在线时读不了微信读书的书（v0.5 导出的不受影响）。
