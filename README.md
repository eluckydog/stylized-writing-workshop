# 风格化写作工坊 · Stylized Writing Workshop

一套基于 **Python 确定性引擎 + ChromaDB 向量检索** 的风格化写作系统。支持马前卒、九边、卢克文、国家地理科普四种风格的自动化写作与质量检测。

> WorkBuddy 专家团 | qclaw 技能适配
> 本项目同时兼容 WorkBuddy Agent 和 qclaw Skill 两种运行环境。

---

## 架构概览

```
stylized-writing-workshop/
├── agents/                    # Agent 配置（WorkBuddy & qclaw 双平台）
│   ├── stylized-writer-maqianzu.md   马前卒风格写手
│   ├── stylized-writer-jiubian.md    九边风格写手
│   ├── stylized-writer-lukewen.md    卢克文风格写手
│   ├── stylized-writer-natgeo.md     国家地理(科普)风格写手
│   ├── stylized-writing-auditor.md   风格审计
│   └── stylized-writing-team-lead.md 团队协调
├── engines/                   # Python 确定性引擎（核心）
│   ├── edge_detector_essay.py       风格质量检测器
│   ├── style_profile_engine.py      风格规则配置与校验
│   ├── argument_controller.py       论证结构强制与提纲生成
│   └── citation_guard.py            引用来源校验
├── skills/styles/             # 风格分析参考文件
└── scripts/                   # 工具脚本（构建向量库等）
```

## 四大引擎

| 引擎 | 功能 | 调用方式 |
|------|------|---------|
| **edge_detector_essay** | 6维检测：句长节奏/数据密度/金句质量/AI套话/论证结构/修辞分布 | `full_report(text)` |
| **style_profile_engine** | 4位写手规则配置 + 结构/禁忌/数据密度校验 | `validate_against_profile(text, name)` |
| **argument_controller** | 三段论提纲生成 + 写作过程完整性校验 | `generate_outline(topic)` / `validate_draft(text)` |
| **citation_guard** | 来源标注检查 + 声明可信度评分 | `scan(text)` |

### 核心理念

- **衍生自衍梦文枢 v2**：参考了衍梦文枢的 edge_detector_v2 检测哲学——"好作品走极端，AI安全就是平庸"
- **政论特化**：针对政经评论的特点，增设数据密度检测、AI安全词检测、论证三段论校验
- **确定性检测**：所有检测基于确定性规则（正则/统计/基尼系数），不依赖 LLM 判断

## 部署指南

### 环境要求

- Python 3.10+
- ChromaDB >= 1.5.0
- sentence-transformers >= 2.7.0
- BAAI/bge-small-zh-v1.5 embedding 模型

```bash
pip install chromadb sentence-transformers
```

### 向量库构建

#### 1. 马前卒语料向量库

准备 btnews 语料（https://github.com/mdark-org/btnews），然后运行：

```bash
# 配置语料路径，然后运行
python scripts/vectorize_maqianzu.py
```

#### 2. 文学向量库（成语 + 诗词名句）

从工作区主 ChromaDB 复制 idioms 和 poem_sentences 集合：

```bash
python scripts/build_literary_db.py
```

### qclaw 适配

在 qclaw 中使用时，将本项目注册为 skill，通过 import 方式调用引擎：

```python
# qclaw skill 中调用
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from engines.edge_detector_essay import full_report
report = full_report(generated_text)
```

### WorkBuddy 适配

作为 Expert Agent 注册，在 agent 的 workflow 中增加引擎调用步骤。

## 风格配置详情

### 马前卒（maqianzu）

- **论证结构**: 问题提出 → 数据呈现 → 原因分析 → 方案建议
- **核心指标**: 数据密度 >= 3条/篇，设问句 >= 8%，禁情绪化感叹和空洞口号
- **数据来源**: btnews 睡前消息语料库 + 红会博爱笔枢

### 九边（jiubian）

- **论证结构**: 背景铺垫 → 现象描述 → 深度分析 → 开放结论
- **风格特征**: 历史纵深感，娓娓道来，结论开放不绝对
- **数据来源**: 待补充本地向量库

### 卢克文（lukewen）

- **论证结构**: 地缘背景 → 核心冲突 → 逻辑推演 → 前景判断
- **风格特征**: 宏大叙事，地缘政治视角，文明竞争框架
- **数据来源**: 待补充本地向量库

### 国家地理·科普（natgeo）

- **论证结构**: 发现引入 → 科学原理 → 数据佐证 → 意义延伸
- **风格特征**: 科学叙事，发现视角，数据可视化思维
- **数据来源**: 待补充本地向量库

## 命令行使用

```bash
# 检测文章风格质量
python -c "
from engines.edge_detector_essay import full_report
text = open('article.txt').read()
print(full_report(text))
"

# 生成写作提纲
python -c "
from engines.argument_controller import create_outline
outline = create_outline('maqianzu', '芯片产业')
for item in outline:
    print(f\"[{item['stage']}] {item['prompt']}\")
"

# 校验引用质量
python -c "
from engines.citation_guard import scan_citations
print(scan_citations(open('article.txt').read()))
"
```

## Roadmap

- [x] 四大 Python 引擎
- [x] 马前卒语料向量库（1376条切片）
- [x] 文学向量库（成语30K + 诗词10K）
- [ ] 九边/卢克文/NatGeo 本地向量库
- [ ] 端到端写作工作流自动化
- [ ] Web UI / API 接口

## 许可

MIT License

## 致谢

- 衍梦文枢 v2 — edge_detector 检测哲学来源
- btnews — 马前卒睡前消息语料
- THUOCL — 诗词名词语料
