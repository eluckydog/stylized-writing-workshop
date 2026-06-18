# Stylized Writing Workshop

> Autonomous AI writing pipeline: research → write → QC → revise → done
> 中文版: README.md | 日本語版: README.ja.md

---

## One-liner

```
Given a topic → auto web research → auto outline → style-guided writing
→ 5 engines detect AI-taste → auto revise until quality passes
```

---

## Quick Start

```bash
pip install chromadb sentence-transformers
pip install duckduckgo-search   # optional, for web search
```

Vector databases are included via Git LFS. Clone and use directly.

### Autonomous writing (recommended)

```python
from engines.research_orchestrator import ResearchOrchestrator

robot = ResearchOrchestrator()
article = robot.write(
    topic="Future of semiconductor industry",
    style="maqianzu",
    max_iterations=3,
)

print(article["content"])
print(f"Quality score: {article['quality_score']}/100")
```

### Quality check an existing article

```python
from engines.edge_detector_essay import full_report

report = full_report(open("article.txt").read())
print(f"Status: {report['status']} / Score: {report['overall_score']}/100")
# Supports zh, en, ja auto-detection
```

---

## Engines

| Engine | What it does |
|--------|-------------|
| **research_orchestrator** | Autonomous pipeline: research → write → QC → iterate |
| **vector_search** | Cross-DB search (corpus + idioms + poems) |
| **edge_detector_essay** | 7-dim AI-taste detection (rhythm, data, golden sentences, safe words, repetition, structure, rhetoric) |
| **style_profile_engine** | Style compliance validation |
| **argument_controller** | 3-stage logic enforcement + outline generation |
| **citation_guard** | Citation quality & credibility scoring |
| **logic_guard** | Logic consistency: causal chains, contradictions, timeline |

All engines use **deterministic rules** (regex, statistics, Gini coefficient). No LLM-as-judge.

---

## Vector Databases (Git LFS)

| DB | Size | Contents |
|----|------|----------|
| `vector_db/maqianzu/` | 198MB | 1,376 semantic chunks from Chinese commentary |
| `vector_db/literary_ref/` | 550MB | 30K idioms + 10K classical poems |

---

## Language Support

Auto-detects `zh` / `en` / `ja`:

```python
full_report("This cannot be overstated.")       # → en
full_report("この問題は重要な意義を持つ。")     # → ja
full_report("这个问题值得深思。")                # → zh
```

---

## Tags

`ai-writing` `style-transfer` `writing-quality` `chinese-nlp` `aigc-detection` `chromadb` `nlp` `writing-tools` `content-detection` `essay-analysis`

## License

MIT
