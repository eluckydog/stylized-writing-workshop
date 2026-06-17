# 风格化写作工坊 · Stylized Writing Workshop

**Python 确定性引擎 + ChromaDB 向量检索 = 可工程化的 AI 写作质量控制**

这不是一个"写文章"的工具，而是一套 **"让AI写出来的东西不像AI写的"** 的质量控制系统。核心思路来自衍梦文枢 v2 的一句话——**"好作品走极端，AI安全就是平庸"**。

> WorkBuddy 专家团 | qclaw 技能适配
> 同时兼容 WorkBuddy Agent 和 qclaw Skill 两种运行环境。

---

## 技术特色

### 1. 五层确定性引擎

放弃传统靠 prompt 约束写作风格的做法，改用 **Python 确定性规则引擎**：

| 引擎 | 做什么 | 怎么做的 |
|------|--------|---------|
| **edge_detector_essay** | 检测"AI味" | 句长方差/基尼系数/数据密度/AI安全词频率 |
| **style_profile_engine** | 校验风格合规 | 论证结构匹配/禁忌清单/数据密度阈值 |
| **argument_controller** | 强制三段论 | 问题→分析→方案逐段校验 + 写作提纲生成 |
| **citation_guard** | 检查引用质量 | 来源前缀匹配/模糊表述检测/可信度评分 |
| **logic_guard** | 逻辑与幻觉检测 | 因果链完整性/事实声明标记/矛盾检测/时间线一致性 |

所有检测基于 **正则匹配、统计分布、基尼系数** 等确定性方法，不需要 LLM 做二次判断。

### 2. 双向量库

#### 马前卒语料库（198MB）
- **来源**: btnews 仓库（睡前消息 832 期 + 高见 40 篇 + 参考信息 446 篇 + 讲点黑话 60 篇）
- **模型**: BAAI/bge-small-zh-v1.5（512维中文embedding）
- **切片**: 1376 条语义块
- **用途**: 写作前检索"马督工对XXX的原话"作为参考素材

#### 文学引用库（550MB）
- **idioms**: 30,310 条成语向量
- **poem_sentences**: 10,000 条诗词名句（含清华 THUOCL 词频数据）
- **用途**: 写作过程中自动推荐合适的成语和诗句，提升文采

### 3. 不依赖 LLM 的质量控制

AI 写作最常见的几个问题——句长均匀无节奏、数据空洞、金句堆砌、安全词泛滥——全部可以用 **确定性统计方法** 检测出来。引擎层做了这些事，agent 层只负责"写什么"，不需要自己判断"写得好不好"。

---

## 架构概览

```
stylized-writing-workshop/
├── agents/                    # Agent 配置（轻量提示词层）
│   ├── stylized-writer-maqianzu.md   马前卒风格
│   ├── stylized-writer-jiubian.md    九边风格    ⚠️ 待补充向量数据
│   ├── stylized-writer-lukewen.md    卢克文风格  ⚠️ 待补充向量数据
│   ├── stylized-writer-natgeo.md     国家地理科普
│   ├── stylized-writing-auditor.md   风格审计
│   └── stylized-writing-team-lead.md 团队协调
├── engines/                   # Python 确定性引擎层
│   ├── edge_detector_essay.py       风格质量检测
│   ├── style_profile_engine.py      风格规则校验
│   ├── argument_controller.py       论证结构控制
│   ├── citation_guard.py            引用来源守卫
│   └── logic_guard.py               逻辑一致性与幻觉检测
├── vector_db/                 # ChromaDB 向量库
│   ├── maqianzu/                   马前卒语料 (198MB)
│   └── literary_ref/               成语+诗词 (550MB)
├── skills/styles/             # 风格分析参考文件
└── scripts/                   # 工具脚本
```

---

## 向量库说明

仓库已通过 Git LFS 附带完整的向量库，克隆后可直接使用，无需重新构建。

| 向量库 | 大小 | LFS | 内容 |
|--------|------|-----|------|
| `vector_db/maqianzu/` | 198MB | ✅ | 马前卒语料 1376 条语义切片 |
| `vector_db/literary_ref/` | 550MB | ✅ | idioms 30K + poem_sentences 10K |

### 关于九边和卢克文

目前仅马前卒（睡前消息）有完整的本地向量库。九边和卢克文的 Agent 配置和风格分析已就位，引擎层也支持，但以下原因暂未进行向量化：

- **九边**: 公众号文章分散在各个平台，目前 IMA 知识库中有公众号内容导出，但尚未找到统一的、可公开分发的完整语料集
- **卢克文**: 同上，其 IP-Agent 智能体已在 IMA 知识库中，但原始文章需要整理和授权后才能向量化入库

引擎的 **规则校验功能**（论证结构检查/风格合规/引用质量）对九边和卢克文仍然完全可用，只是缺少**向量检索素材**（写作时搜索参考原文的能力）。待找到合适的公开语料后，可参考马前卒的流程补上。

---

## 快速开始

### 环境

```bash
pip install chromadb sentence-transformers
# 需要 BAAI/bge-small-zh-v1.5 embedding 模型（约 30MB，首次运行自动下载）
```

### 使用示例

```python
# 1. 检测文章有没有 AI 味
from engines.edge_detector_essay import full_report
report = full_report(open("article.txt").read())
print(report["status"], report["overall_score"])

# 2. 按马前卒风格校验文章
from engines.style_profile_engine import validate_against_profile
result = validate_against_profile(open("article.txt").read(), "maqianzu")
print(result["pass"], result["issues"])

# 3. 生成写作提纲
from engines.argument_controller import ArgumentController
ctrl = ArgumentController("maqianzu")
outline = ctrl.generate_outline("芯片产业")

# 4. 检查引用质量
from engines.citation_guard import CitationGuard
guard = CitationGuard()
guard.scan(open("article.txt").read())
```

---

## 风格配置详情

### 马前卒 · maqianzu ✅ 本地向量库就绪

工程师视角拆解社会问题，发现问题必提方案。
- **结构**: 问题提出 → 数据呈现 → 原因分析 → 方案建议
- **指标**: 数据密度 >= 3 条/篇，设问句 >= 8%
- **禁忌**: 情绪化感叹（"震惊""令人发指"）、空洞口号（"切实加强""高度重视"）

### 九边 · jiubian ⚠️ 待向量数据

长线社会观察，历史纵深感，娓娓道来而不急于下结论。
- **结构**: 背景铺垫 → 现象描述 → 深度分析 → 开放结论
- **特征**: 结论开放不绝对，多用"也许""可能"而非"必然""一定"

### 卢克文 · lukewen ⚠️ 待向量数据

宏大叙事，地缘政治视角，文明竞争分析框架。
- **结构**: 地缘背景 → 核心冲突 → 逻辑推演 → 前景判断
- **特征**: 从利益格局分析，避免道德评价

### 国家地理·科普 · natgeo

科学叙事，发现视角，数据可视化思维。
- **结构**: 发现引入 → 科学原理 → 数据佐证 → 意义延伸
- **特征**: 避免过度拟人化，只引用经同行评议的科学结论

---

## Roadmap

- [x] 五大 Python 确定性引擎（含防幻觉/逻辑一致性）
- [x] 马前卒语料向量库（1376 条切片）
- [x] 文学引用向量库（成语 30K + 诗词 10K）
- [ ] 九边/卢克文本地向量库（待找到合适的公开语料）
- [ ] 端到端写作工作流自动化
- [ ] Web UI / API 接口

---

## 致谢

- **衍梦文枢 v2** — edge_detector 检测哲学来源："好作品走极端，AI安全就是平庸"
- **btnews** — 马前卒睡前消息语料仓库（https://github.com/mdark-org/btnews）
- **THUOCL** — 清华大学开放中文词库（诗词名词语料）

## 许可

MIT License
