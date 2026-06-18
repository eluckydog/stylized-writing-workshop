# Stylized Writing Workshop

> Python deterministic engines + ChromaDB vector retrieval = engineering-grade AI writing quality control

This is not a "write an article" tool. It's a **quality control system that makes AI-generated text stop sounding like AI**. Core philosophy: **"Good works go to extremes. AI safety is mediocrity."**

---

## Quick Start

```bash
pip install chromadb sentence-transformers
```

```python
from engines.edge_detector_essay import full_report

# Auto-detects language (Chinese / English / Japanese)
report = full_report("This cannot be overstated.")
report = full_report("この問題は重要な意義を持つ。")   # Japanese auto-detect ✓
print(report["status"], report["overall_score"])
```

## 5 Deterministic Engines · Trilingual (ZH/EN/JA)

| Engine | Detects | Method |
|--------|---------|--------|
| **edge_detector_essay** | "AI taste" (7 dims) | sentence variance / Gini coefficient / data density / safe words / repetition / golden sentences / rhetoric |
| **style_profile_engine** | Style compliance | argument structure matching / forbidden lists |
| **argument_controller** | 3-stage logic | problem→analysis→solution validation |
| **citation_guard** | Citation quality | source prefix matching / vague statement detection |
| **logic_guard** | Logic & hallucination | causal chain completeness / contradiction detection |

All engines use **deterministic rules** (regex, statistics, Gini coefficient). No LLM-as-judge.

## Vector Databases (via Git LFS)

| DB | Size | Contents |
|----|------|----------|
| `vector_db/maqianzu/` | 198MB | 1,376 semantic chunks from Chinese commentary |
| `vector_db/literary_ref/` | 550MB | 30K idioms + 10K classical poem sentences |

## Tags

`ai-writing` `style-transfer` `writing-quality` `chinese-nlp` `content-detection` `chromadb` `nlp` `writing-tools` `aigc-detection` `essay-analysis`

## License

MIT
