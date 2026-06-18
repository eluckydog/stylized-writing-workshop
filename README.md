# 风格化写作工坊 · Stylized Writing Workshop

> **Python deterministic engines + ChromaDB vector retrieval = engineering-grade AI writing quality control**
> 中文 | [English](./README.en.md)

这不是一个"写文章"的工具，而是一套 **"让AI写出来的东西不像AI写的"** 的质量控制系统。核心思路：**"好作品走极端，AI安全就是平庸"**。

> WorkBuddy Agent · qclaw Skill · 中英日三语 · 7维检测

---

## 技术特色 · Features

### 五层确定性引擎 · Five Deterministic Engines

放弃 prompt 约束风格，改用 Python 确定性规则引擎：

| Engine | What | How |
|--------|------|-----|
| **research_orchestrator** | Autonomous writing pipeline | web research → outline → write → 5-engine QC → iterate |
| **vector_search** | Unified vector search | cross-DB query across maqianzu + idioms + poems |
| **edge_detector_essay** | Detect "AI taste" (7 dims) | sentence variance / Gini coefficient / data density / AI-safe words / repetition / golden sentences / rhetoric clustering |
| **style_profile_engine** | Style compliance | argument structure matching / forbidden list / data thresholds |
| **argument_controller** | Force 3-stage logic | problem→analysis→solution paragraph validation + outline generation |
| **citation_guard** | Citation quality | source prefix matching / vague statement detection / credibility scoring |
| **logic_guard** | Logic & hallucination | causal chain completeness / fact claim tagging / contradiction detection / timeline check |

All detections are **deterministic** (regex, statistics, Gini coefficient). No LLM-as-judge needed.

### 双向量库 · Dual Vector Databases

- **maqianzu corpus** (198MB): 1,376 semantic chunks from btnews (832 episodes + 40 opinions + 446 references + 60 slang)
- **Literary reference** (550MB): 30,310 Chinese idioms + 10,000 classical poem sentences (THUOCL)

### 多语言支持 · Trilingual (ZH/EN/JA)

```python
from engines.edge_detector_essay import full_report

# Auto-detect language (zh / en / ja)
report = full_report("This cannot be overstated.")     # → English AI-safe ✓
report = full_report("この問題は重要な意義を持つ。")   # → Japanese AI-safe ✓
report = full_report("这个问题值得深思。", lang="zh")  # → specify explicitly
```

---

## 实战教程 · Tutorial

### 场景：你写了一篇公众号文章，担心被小红书/公众号判为AI生成

现在很多平台对AI生成内容的风控越来越严。我们的工坊不只是一个质检工具，它是一套能帮你**写出一篇"看起来就是人写的"文章**的完整系统。

---

### 第一步：用马前卒风格写一篇初稿

```python
# 在你的 AI 对话工具或 WorkBuddy Agent 中调用马前卒写手
# 提示词模板：

你是一个马前卒风格的写手，请写一篇关于\"中国芯片产业现状\"的分析文章。
要求：
1. 按"问题提出→数据呈现→原因分析→方案建议"的结构组织
2. 至少引用3个具体数据点
3. 以设问句开头
4. 结尾给出可操作的解决方案
```

### 第二步：检测AI味

```python
from engines.edge_detector_essay import full_report

text = open("draft.md", encoding="utf-8").read()
report = full_report(text)

print(f"总分: {report['overall_score']}/100")
print(f"状态: {report['status']}")
# good / minor_issues / needs_revision / ai_taste

for issue in report["issues"]:
    print(f"  [{issue['severity']}] {issue['dimension']}: {issue['detail']}")
```

**输出示例：**
```
总分: 62.5/100
状态: needs_revision
  [CRITICAL] 数据密度: 全文无数据支撑，政论文章大忌
  [WARNING] AI套话: 安全词密度2.5/千字，含['空洞表态']等类别
```

### 第三步：针对性修改

根据检测报告中的问题逐条修改。几个高频问题及对策：

| 检测问题 | 典型AI写法 | 改成这样 |
|---------|-----------|---------|
| AI套话过多 | "这个问题值得深思" | "这个问题的账其实很简单：收入涨不动，支出却刚性" |
| 数据空洞 | "近年来快速增长" | "2023年进口芯片3500亿美元，同比降15.6%" |
| 金句堆砌 | "既要…又要…更要…不仅…而且…" | 保留1-2处，其余改为平实陈述 |
| 句长无节奏 | 每句25-30字均匀分布 | 在第3段插入1句极短句(<10字)打乱节奏 |
| 用词重复 | "核心""关键""突破"高频出现 | 替换同义词："要害""枢纽""关卡""进展" |

### 第四步：校验风格合规

```python
from engines.style_profile_engine import validate_against_profile

# 检查是否符合马前卒风格
result = validate_against_profile(text, "maqianzu")
print(f"风格校验: {'通过' if result['pass'] else '未通过'}")
for issue in result["issues"]:
    print(f"  {issue}")
```

### 第五步：检查引用质量

```python
from engines.citation_guard import CitationGuard
guard = CitationGuard()
result = guard.scan(text)
print(f"引用可信度: {result['citation_score']}/100")
print(f"有来源声明: {result['sourced_claims']}, 无来源: {result['unsourced_claims']}")

# 如果有无来源的数据，搜索结果给它补上出处
from engines.vector_search import search_all
evidence = search_all("2023年芯片进口3500亿美元", top_k=1)
print(f"搜索到参考: {evidence[0]['document'][:60] if evidence else '未找到'}")
```

### 第六步：检查逻辑一致性

```python
from engines.logic_guard import LogicGuard
guard = LogicGuard()
result = guard.scan(text)
print(f"逻辑评分: {result['overall_score']}/100 ({result['status']})")
if result['contradictions']:
    print("检测到逻辑矛盾:")
    for c in result['contradictions']:
        print(f"  {c['claim_a'][:40]} ↔ {c['claim_b'][:40]}")
```

### 第七步：向量搜索找参考素材

写作过程中随时可以调用向量库找参考：

```python
from engines.vector_search import search_all, search_writer, search_literary

# 1. 找马督工对某个话题的原话
refs = search_writer("maqianzu", "芯片产业", top_k=3)
for ref in refs:
    print(f"睡前消息参考: {ref['document'][:100]}...")

# 2. 找合适的成语
idiom = search_literary("坚持不懈的精神", type_filter="idioms", top_k=1)
print(f"推荐成语: {idiom[0]['document']}")

# 3. 找诗词引用
poem = search_literary("奋斗", type_filter="poem_sentences", top_k=1)
print(f"推荐诗句: {poem[0]['document']}")
```

---

## 参数调优指南

### 调整检测阈值

所有检测阈值在引擎源码顶部以常量形式定义，可直接修改：

**edge_detector_essay.py:**
```python
# 句长节奏阈值
MIN_SENTENCES = 10         # 最少句子数，少于则判定 too_short
RHYTHM_STD_THRESHOLD = 10  # 句长方差低于此值判为 flat

# 数据密度阈值
DATA_STATUS = {
    "data_void": 1,    # <1条/千字
    "sparse": 3,       # <3条/千字
    "good": 12,        # 3-12条/千字 为理想区间
}

# AI安全词密度
SAFE_WORD_THRESHOLDS = {
    "heavy": 3,        # >3条/千字 → critical
    "noticeable": 1.5, # >1.5条/千字 → warning
}

# 重复用词
OBSESSIVE_THRESHOLD = 0.08  # 同一词占比>8%标记
TOP3_SHARE_WARN = 0.30      # 前3高频词占比>30%报警
```

**argument_controller.py:**
```python
# 论证结构权重
STAGE_WEIGHTS = {
    "问题提出": 1,
    "数据呈现": 2,    # 数据最重要
    "原因分析": 2,
    "方案建议": 2,
}
```

**citation_guard.py:**
```python
# 引用评分权重
SOURCE_RATIO_WEIGHT = 60   # 来源占比权重
DATA_VOLUME_WEIGHT = 40    # 数据量权重
```

### 调整风格配置文件

`style_profile_engine.py` 中每个写手有独立的配置块。以马前卒为例：

```python
"maqianzu": {
    "data_requirements": {
        "min_data_points": 3,      # 最少数据点数
        "preferred_min": 5,        # 推荐数据点数
        "density_per_1000": 2.0,   # 千字密度
    },
    "forbidden": [
        # 添加你自己的禁忌规则
        {"name": "行业黑话", "pattern": r"赋能|闭环|抓手|颗粒度",
         "suggestion": "用大白话替换行业黑话"},
    ],
    "sentence_patterns": {
        "ratio_limits": {
            "设问句比例": [">=", 0.08],  # 设问句至少 8%
        }
    }
}
```

### 调整论证结构模板

`argument_controller.py` 中每个写手有 stage 配置。可调整每阶段的最少字数：

```python
"maqianzu": {
    "stages": [
        {"name": "问题提出", "min_chars": 200},   # 最少200字
        {"name": "数据呈现", "min_chars": 300},   # 最少300字
        {"name": "原因分析", "min_chars": 400},
        {"name": "方案建议", "min_chars": 300},
    ]
}
```

---

## 写作工作流速查

```
                          ┌──────────────────┐
                          │  写手 Agent 生成  │
                          │  (MD提示词驱动)   │
                          └────────┬─────────┘
                                   ↓
                    ┌──────────────────────────┐
                    │  向量搜索找参考素材       │
                    │  vector_search.search()  │
                    └────────┬─────────────────┘
                             ↓
              ┌──────────────────────────────┐
              │  5个引擎逐层校验              │
              │                              │
              │  ① edge_detector  → AI味检测  │
              │  ② style_profile → 风格合规   │
              │  ③ citation_guard → 引用质量  │
              │  ④ logic_guard   → 逻辑一致性 │
              │  ⑤ argument_ctrl  → 结构校验  │
              └────────┬─────────────────────┘
                       ↓
              ┌──────────────────┐
              │  根据报告修改     │
              │  重新校验         │
              │  直到 pass        │
              └──────────────────┘
```

---

## Quick Start

```bash
pip install chromadb sentence-transformers
```

```python
# 1. Detect AI taste
from engines.edge_detector_essay import full_report
report = full_report(open("article.txt").read())
print(report["status"], report["overall_score"])

# 2. Validate style
from engines.style_profile_engine import validate_against_profile
result = validate_against_profile(open("article.txt").read(), "maqianzu")

# 3. Generate outline
from engines.argument_controller import ArgumentController
ctrl = ArgumentController("maqianzu")
outline = ctrl.generate_outline("semiconductor industry")

# 4. Check citations
from engines.citation_guard import CitationGuard
guard = CitationGuard()
guard.scan(open("article.txt").read())

# 5. Logic check (bilingual)
from engines.logic_guard import LogicGuard
LogicGuard().scan(open("article.txt").read())
```

---

## Architecture

```
stylized-writing-workshop/
├── agents/                    # Agent configs
│   ├── stylized-writer-maqianzu.md   Ma Qianzu style
│   ├── stylized-writer-jiubian.md    Jiubian style   ⚠️ no vector data
│   ├── stylized-writer-lukewen.md    Lu Kewen style  ⚠️ no vector data
│   ├── stylized-writer-natgeo.md     NatGeo style
│   ├── stylized-writing-auditor.md   Style auditor
│   └── stylized-writing-team-lead.md Team coordinator
├── engines/                   # Python deterministic engines
│   ├── research_orchestrator.py      [NEW] Autonomous research & writing pipeline
│   ├── vector_search.py              [NEW] Unified vector search (all DBs)
│   ├── lang_config.py               Trilingual pattern config (ZH/EN/JA)
│   ├── edge_detector_essay.py       7-dim AI-taste detection
│   ├── style_profile_engine.py      Style rule validation
│   ├── argument_controller.py       Argument structure control
│   ├── citation_guard.py            Citation quality guard
│   └── logic_guard.py               Logic consistency guard
├── vector_db/                 # ChromaDB vector stores (LFS)
│   ├── maqianzu/                   Ma Qianzu corpus (198MB)
│   └── literary_ref/               Idioms + poems (550MB)
├── skills/styles/             # Style analysis references
└── scripts/                   # Build tools
```

---

## Style Profiles

| Writer | Structure | Vector Data | Notes |
|--------|-----------|-------------|-------|
| **Ma Qianzu** | Problem → Data → Analysis → Solution | ✅ 1,376 chunks | Engineer's lens, data-driven |
| **Jiubian** | Background → Phenomenon → Deep → Open | ⚠️ Pending | Long-form social commentary |
| **Lu Kewen** | Geopolitical context → Conflict → Logic → Outlook | ⚠️ Pending | Grand narrative, geopolitics |
| **NatGeo** | Discovery → Science → Evidence → Meaning | ✅ Idioms+Poems for reference | Scientific storytelling |

---

## Tags

`ai-writing` `style-transfer` `writing-quality` `chinese-nlp` `content-detection` `chromadb` `nlp` `writing-tools` `aigc-detection` `essay-analysis`

## License

MIT

## Credits

- 衍梦文枢 v2 — Edge detection philosophy: "Good works go to extremes. AI safety is mediocrity."
- btnews — Ma Qianzu's Bedtime News corpus (https://github.com/mdark-org/btnews)
- THUOCL — Tsinghua Open Chinese Lexicon
