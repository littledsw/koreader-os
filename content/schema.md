# 内容包字段定义

所有内容包最终打包成 SQLite（`content.db`），源数据为 JSON 数组
（大批量生成时可用 JSONL，每行一个对象），一个文件一个包，便于分批生成与校验。

## 通用约定

- 全 UTF-8，无 BOM。
- `id`：稳定主键，格式 `包名:slug`，如 `ielts:ambiguous`、`animal:pangolin`。
- IPA 用 `/.../`，英美差异记在 `ipa_us` 可选字段。
- 中文释义用全角标点；英文例句用半角标点。
- 例句必须自造或来自 CC 授权语料，禁止直接抄商业词典。

## 1. 雅思词条 `ielts`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | ✓ | `ielts:<word>` |
| word | string | ✓ | 词条 |
| ipa | string | ✓ | 国际音标 |
| pos | string[] | ✓ | 词性，如 `["adj."]` |
| def_zh | string | ✓ | 中文释义，多个义项用 `；` |
| def_en | string | ✓ | 英文释义（学习词典风格，一句） |
| roots | object[] | ✓ | 词根拆分，见下 |
| root_story | string | ✓ | 词根小故事，100–200 字中文，讲"字面义如何变成今天的意思" |
| family | object[] | ✓ | 同根词扩展 `{word, gloss_zh}`，3–8 个 |
| synonyms | string[] | ✓ | 2–4 个 |
| antonyms | string[] | ✓ | 0–3 个 |
| examples | object[] | ✓ | 2–3 条 `{en, zh}` |
| collocations | string[] | ○ | 常见搭配 |
| ielts_topics | string[] | ✓ | 教育/环境/科技/健康/社会/法律/商业/文化 |
| level | string | ○ | `core` / `extended` |

`roots` 元素：

```json
{"form": "ambi-", "gloss_zh": "两边", "note": "拉丁前缀，同 ambivalent"}
```

## 2. 中国专题 `china`

以单元为单位，一个单元一行：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | `china:<slug>` |
| unit | string | 单元名，如 `history:sil-road` |
| title_zh / title_en | string | 标题 |
| words | object[] | 主题词 `{word, ipa, def_zh, example_en}` |
| patterns | string[] | 句型/表达 |
| essay_en | string | 250 词左右范文 |
| essay_zh | string | 中文对照 |
| recitable | string[] | 可背诵段落 |

## 3. 动物图鉴 `animal`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | `animal:<slug>` |
| name_en / name_zh | string | 名称 |
| scientific | string | 学名（斜体显示） |
| ipa | string | 音标 |
| taxon | string | 纲/目，如 `Mammalia · Carnivora` |
| traits | string[] | 3 条英文特征，每条 ≤ 12 词 |
| fact_zh | string | 一条冷知识，中文，≤ 60 字 |
| idioms | object[] | `{en, zh}`，如 `as busy as a bee` |
| conservation | string | IUCN 等级：LC/NT/VU/EN/CR |
| image | object | `{file, license, author, source_url}` |

图片规范：

- 仅用公有领域 / CC0 素材（Biodiversity Heritage Library、Wikimedia Commons 老插图）。
- 处理：去背景 → 灰度 → 对比度拉伸 → 1-bit 抖动或 16 灰阶，输出 PNG，长边 640px。
- 文件命名 `animal/<slug>.png`，同目录保留 `CREDITS.md` 记录来源与作者。
