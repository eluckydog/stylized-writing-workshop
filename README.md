# 风格化写作工坊 · Stylized Writing Workshop

> 全自动 AI 写作系统 · 给定主题，自动调研、自动写作、自动校验、自动修改到达标
> Autonomous writing pipeline: research → write → QC → revise → done
> 対応言語：中文 · [English](./README.en.md) · [日本語](./README.ja.md)

[//]: # (This README is in Chinese. English version: README.en.md | 日本語版: README.ja.md)

---

## 一句话概括

```
给定一个主题 → 自动联网搜索 → 自动生成提纲 → 按风格写文章
→ 5个引擎逐层检测AI味 → 不达标自动修改 → 直到质量合格
```

---

## 安装

```bash
pip install chromadb sentence-transformers
# 联网搜索可选（推荐）:
pip install duckduckgo-search
```

向量库已含在仓库中（Git LFS），克隆后即可使用，无需额外构建。

---

## 核心用法

### 全自动写作（推荐）

```python
from engines.research_orchestrator import ResearchOrchestrator

robot = ResearchOrchestrator()

# 给定主题，全自动完成：调研 → 写作 → 校验 → 修改
article = robot.write(
    topic="中国芯片产业现状与未来",
    style="maqianzu",        # 支持 maqianzu / jiubian / lukewen / natgeo
    max_iterations=3,         # 不达标最多重写3轮
)

print(article["title"])
print(article["content"])
print(f"最终质量评分: {article['quality_score']}/100")
```

输出示例：
```
[1/5] 联网调研... 搜索了5组关键词，提取8条数据点
[2/5] 生成提纲... [问题提出] [数据呈现] [原因分析] [方案建议]
[3/5] 生成初稿... 完成 (1240字)
[4/5] 质量校验...
  第1轮: 62.5/100 (needs_revision) → 数据稀疏、AI套话
  第2轮: 78.0/100 (minor_issues) → 金句略多
  第3轮: 85.0/100 (good) ✅
[5/5] 完成
最终质量评分: 85.0/100
```

### 对已有文章做质检

```python
from engines.edge_detector_essay import full_report
from engines.citation_guard import CitationGuard
from engines.logic_guard import LogicGuard

text = open("my_article.md", encoding="utf-8").read()

# 检测AI味
report = full_report(text)
print(f"状态: {report['status']} / 评分: {report['overall_score']}/100")

# 检查引用
cite = CitationGuard().scan(text)
print(f"引用可信度: {cite['citation_score']}/100")

# 检查逻辑
logic = LogicGuard().scan(text)
print(f"逻辑评分: {logic['overall_score']}/100")
```

---

## 快速调用速查

```python
# === 自动写作（一条命令）===
from engines.research_orchestrator import auto_write
result = auto_write("芯片产业", style="maqianzu")

# === 搜索参考素材 ===
from engines.vector_search import search_all, search_writer, search_literary
search_all("房价")                   # 跨库搜索
search_writer("maqianzu", "芯片")    # 马前卒语料
search_literary("坚持", "idioms")    # 成语

# === 生成提纲 ===
from engines.argument_controller import create_outline
outline = create_outline("maqianzu", "房价")

# === 风格校验 ===
from engines.style_profile_engine import validate_against_profile
validate_against_profile(text, "maqianzu")

# === AI味检测 ===
from engines.edge_detector_essay import full_report
full_report(text, lang="en")  # 英文
full_report(text, lang="ja")  # 日文
full_report(text)             # 自动检测
```

---

## 引擎一览

| 引擎 | 作用 |
|------|------|
| **research_orchestrator** | 全自动写作管线：调研→写作→校验→迭代 |
| **vector_search** | 跨库向量搜索（马前卒语料 + **卢克文语料** + 成语 + 诗词） |
| **edge_detector_essay** | 7维AI味检测：句长节奏/数据密度/金句/AI套话/重复用词/论证结构/修辞 |
| **literary_spark** | **点睛笔引擎** — 自动检测平淡区，在转折/收尾处推荐成语或诗词 |
| **style_profile_engine** | 风格合规校验（4位写手的规则配置） |
| **argument_controller** | 论证三段论强制与提纲生成 |
| **citation_guard** | 引用来源标注检查与可信度评分 |
| **logic_guard** | 逻辑一致性：因果链/矛盾检测/时间线/幻觉 |

所有引擎均使用**确定性规则**（正则/统计/基尼系数），不依赖LLM做二次判断。

---

## 向量库

| 库 | 大小 | 内容 |
|----|------|------|
| `vector_db/maqianzu/` | 198MB | 睡前消息832期 + 高见40篇 + 参考信息446篇 + 黑话60篇 = 1376条语义切片 |
| `vector_db/lukewen/` | **30MB** | **卢克文444篇文章 = 12,164条语义切片** |
| `vector_db/literary_ref/` | 550MB | 成语 30,310 条 + 诗词名句 10,000 条 |

向量库通过 Git LFS 管理，克隆后可直接使用。

---

## 语言支持

引擎自动检测输入文本的语言，支持中/英/日三语：

```python
full_report("This cannot be overstated."))        # → 自动识別 en
full_report("この問題は重要な意義を持つ。")       # → 自動検出 ja
full_report("这个问题值得深思。")                   # → 自动识别 zh
```

---

## 写手风格

| 写手 | 论证结构 | 向量数据 | 说明 |
|------|---------|---------|------|
| **马前卒** | 问题→数据→分析→方案 | ✅ 1376条 | 工程师视角，数据驱动 |
| **卢克文** | 地缘→冲突→推演→前景 | ✅ **12,164条** | 宏大叙事，地缘政治 |
| **九边** | 背景→现象→深度→开放 | ⚠️ 待补充 | 长线社会观察 |
| **国家地理** | 发现→原理→数据→意义 | ✅ 成语+诗词 | 科学叙事 |

九边目前仅有风格规则配置和 Agent 定义，缺少本地向量库（尚未找到合适的公开语料）。引擎的规则校验功能仍然可用。

---

## 参数调优

各引擎的检测阈值在源码顶部定义为常量，直接修改即可：

```python
# edge_detector_essay.py
OBSESSIVE_THRESHOLD = 0.08   # 同一词占比>8%标记为重复

# citation_guard.py
SOURCE_RATIO_WEIGHT = 60      # 来源占比权重
DATA_VOLUME_WEIGHT = 40       # 数据量权重

# style_profile_engine.py — 马前卒的配置块
"min_data_points": 3           # 最少数据点数
"preferred_min": 5             # 推荐数据点数
```

---

## 架构

```
stylized-writing-workshop/
├── engines/
│   ├── research_orchestrator.py    全自动写作管线
│   ├── vector_search.py            统一向量搜索
│   ├── edge_detector_essay.py      AI味检测
│   ├── literary_spark.py           点睛笔引擎
│   ├── style_profile_engine.py     风格校验
│   ├── argument_controller.py      论证结构
│   ├── citation_guard.py           引用检查
│   ├── logic_guard.py              逻辑一致性
│   └── lang_config.py              三语模式配置
├── agents/                         写手 Agent 配置
├── vector_db/                      向量库 (LFS)
└── skills/styles/                  风格参考
```

---

## Tags

`ai-writing` `style-transfer` `writing-quality` `chinese-nlp` `aigc-detection` `chromadb` `nlp` `writing-tools` `content-detection` `essay-analysis`

## License

MIT

## Credits

- 衍梦文枢 v2 — 检测哲学："好作品走极端，AI安全就是平庸"
- btnews — 马前卒睡前消息语料 (github.com/mdark-org/btnews)
- THUOCL — 清华大学开放中文词库
