# スタイライズド・ライティング工房

> 自動AI文章作成パイプライン：調査 → 執筆 → 品質検査 → 修正 → 完了
> 中文版: README.md | English: README.en.md

---

## 一言で

```
テーマを指定 → 自動Web調査 → 自動アウトライン生成 → スタイル指定で執筆
→ 5つのエンジンでAI臭を検出 → 品質达标まで自動修正
```

---

## クイックスタート

```bash
pip install chromadb sentence-transformers
```

### 自動執筆（推奨）

```python
from engines.research_orchestrator import ResearchOrchestrator

robot = ResearchOrchestrator()
article = robot.write(
    topic="半導体産業の現状と未来",
    style="maqianzu",
    max_iterations=3,
)

print(article["content"])
print(f"品質スコア: {article['quality_score']}/100")
```

### 既存文章の品質チェック

```python
from engines.edge_detector_essay import full_report

report = full_report("この問題は重要な意義を持つ。")
print(f"Status: {report['status']} / Score: {report['overall_score']}/100")
# 自動検出 ja ✅
```

---

## エンジン一覧

| エンジン | 機能 |
|---------|------|
| **research_orchestrator** | 自動パイプライン：調査→執筆→QC→反復 |
| **vector_search** | 統合ベクトル検索 |
| **edge_detector_essay** | 7次元AI臭検出 |
| **style_profile_engine** | スタイル準拠チェック |
| **argument_controller** | 三段論法の強制とアウトライン生成 |
| **citation_guard** | 引用品質チェック |
| **logic_guard** | 論理一貫性チェック |

---

## ベクトルDB (Git LFS)

| DB | サイズ | 内容 |
|----|--------|------|
| `vector_db/maqianzu/` | 198MB | 中国語コメンタリー 1376件 |
| `vector_db/literary_ref/` | 550MB | 中国語成語30K＋詩詞10K |

---

## 言語サポート

自動検出：中文 / English / 日本語

```python
full_report("This cannot be overstated.")       # → en
full_report("この問題は重要な意義を持つ。")     # → ja
full_report("这个问题值得深思。")                # → zh
```

## Tags

`ai-writing` `style-transfer` `writing-quality` `chinese-nlp` `aigc-detection` `chromadb` `nlp` `writing-tools` `content-detection` `essay-analysis`

## License

MIT
