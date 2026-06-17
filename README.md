# 风格化写作工坊 · Stylized Writing Workshop

> **Python deterministic engines + ChromaDB vector retrieval = engineering-grade AI writing quality control**
> 中文 | [English](./README.en.md)

这不是一个"写文章"的工具，而是一套 **"让AI写出来的东西不像AI写的"** 的质量控制系统。核心思路：**"好作品走极端，AI安全就是平庸"**。

> WorkBuddy Agent · qclaw Skill · 中英文双语

---

## 技术特色 · Features

### 五层确定性引擎 · Five Deterministic Engines

放弃 prompt 约束风格，改用 Python 确定性规则引擎：

| Engine | What | How |
|--------|------|-----|
| **edge_detector_essay** | Detect "AI taste" | sentence variance / Gini coefficient / data density / AI-safe words |
| **style_profile_engine** | Style compliance | argument structure matching / forbidden list / data thresholds |
| **argument_controller** | Force 3-stage logic | problem→analysis→solution paragraph validation + outline generation |
| **citation_guard** | Citation quality | source prefix matching / vague statement detection / credibility scoring |
| **logic_guard** | Logic & hallucination | causal chain completeness / fact claim tagging / contradiction detection / timeline check |

All detections are **deterministic** (regex, statistics, Gini coefficient). No LLM-as-judge needed.

### 双向量库 · Dual Vector Databases

- **maqianzu corpus** (198MB): 1,376 semantic chunks from btnews (832 episodes + 40 opinions + 446 references + 60 slang)
- **Literary reference** (550MB): 30,310 Chinese idioms + 10,000 classical poem sentences (THUOCL)

### 多语言支持 · Bilingual

```python
from engines.edge_detector_essay import full_report

# Auto-detect language
report = full_report("This cannot be overstated. A long way to go.")
# → detects English AI-safe words ✓

# Or specify explicitly
report = full_report("这个问题值得深思。", lang="zh")
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
│   ├── lang_config.py               Bilingual pattern config
│   ├── edge_detector_essay.py       AI-taste detection
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
