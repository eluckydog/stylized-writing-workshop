# -*- coding: utf-8 -*-
"""
methodology/distill.py — 方法论蒸馏器（离线）

目标：把三巨头语料库（马前卒/卢克文/九边）从"检索表"升级为"方法论标本库"。
从 chroma 向量库【数据驱动】抽取每位写手的：

  - corpus_stats        语料规模
  - markers             招牌标记词频率（论点/转折/举例）
  - opening_patterns    高频开场句式
  - signature_viewpoints  真实论点句样本（思维链证据，可直接 inspect）
  - structure           四段论证骨架（合并自 argument_controller 手写配置）

输出：methodology/profiles/<writer>_profile.json
      —— 完全可检视、可审计、非黑盒。

用法：
    python methodology/distill.py
"""

import os, re, json, glob
from pathlib import Path
from collections import Counter

WORKSHOP = Path(__file__).resolve().parent.parent
PROFILES_DIR = WORKSHOP / "methodology" / "profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

# ---- 离线加载 chroma（不触碰网络）----
import chromadb
from chromadb.config import Settings

VECTOR_DB = WORKSHOP / "vector_db"
PLUGIN_ROOT = Path(os.path.expanduser(
    "~/.workbuddy/plugins/marketplaces/my-experts/plugins/stylized-writing-workshop/vector_db"))

# 四段论证骨架（结构命名来自 engines/argument_controller.py 手写配置，此处集中引用）
STRUCTURE = {
    "maqianzu": {
        "label": "问题→数据→分析→方案",
        "stages": [
            ("问题", "抛一个具体矛盾/现象，制造认知落差"),
            ("数据", "用公开数据把问题拆开（统计/对比/百分比）"),
            ("分析", "挖机制/根源，从结构而非情绪看"),
            ("方案", "给对策/出路/方向"),
        ],
        "core": "工程师视角，数据驱动，硬核时政",
    },
    "jiubian": {
        "label": "背景→现象→深度→开放",
        "stages": [
            ("背景", "用历史/长期视角铺垫，先把时间线拉长"),
            ("现象", "落到当下某个具体变化"),
            ("深度", "挖机制/惯性/底层逻辑，而非表面情绪"),
            ("开放", "留白，给概率判断而非绝对结论"),
        ],
        "core": "认知升级视角，故事化，贴个体读者",
    },
    "lukewen": {
        "label": "地缘→冲突→推演→前景",
        "stages": [
            ("地缘", "把议题定位到文明/大国坐标"),
            ("冲突", "点出矛盾/博弈/争夺"),
            ("推演", "按逻辑必然性推导走向"),
            ("前景", "给出未来趋势判断"),
        ],
        "core": "宏大国际叙事，地缘政治推演",
    },
}

# 招牌标记词（用于频率统计 + 论点句抽取）
MARKER_GROUPS = {
    "viewpoint": ["其实", "说白了", "本质上", "关键在于", "问题在于", "真相是",
                  "一句话", "说到底", "换句话说", "平心而论", "仔细想想", "说句公道话"],
    "transition": ["但是", "然而", "不过", "与此同时", "另一方面", "回到", "话说回来",
                   "顺带", "有意思的是", "值得注意的是", "反过来看", "站在"],
    "example": ["比如", "举个例子", "我有个朋友", "我认识一个", "我见过", "我身边",
                "有一次", "记得", "前两年", "去年", "我同事"],
}

SENT_SPLIT = re.compile(r"[。！？\n]")


def load_docs(writer: str):
    """优先插件版库，回退工作区版库；分页拉取所有文档（避免 chromadb SQL variables 限制）"""
    for root in (PLUGIN_ROOT, VECTOR_DB):
        path = root / writer
        if path.exists():
            client = chromadb.PersistentClient(
                path=str(path), settings=Settings(anonymized_telemetry=False))
            try:
                col = client.get_collection(writer)
                total = col.count()
                all_docs, all_metas = [], []
                for offset in range(0, total, 1000):
                    data = col.get(include=["documents", "metadatas"],
                                   limit=1000, offset=offset)
                    all_docs.extend(data["documents"])
                    all_metas.extend(data["metadatas"])
                return all_docs, all_metas
            except Exception:
                continue
    return [], []


def distill_writer(writer: str) -> dict:
    docs, metas = load_docs(writer)
    if not docs:
        raise RuntimeError(f"未找到 {writer} 的向量库")

    total_chars = sum(len(d) for d in docs)
    # 标记词频率
    marker_counts = {g: Counter() for g in MARKER_GROUPS}
    for d in docs:
        for g, words in MARKER_GROUPS.items():
            for w in words:
                c = d.count(w)
                if c:
                    marker_counts[g][w] += c

    # 开场句式：每块首 12 字
    opening = Counter()
    for d in docs:
        s = d.strip()[:12]
        if len(s) >= 4:
            opening[s] += 1

    # 论点句样本（含 viewpoint 标记的真实句子，作为思维链证据）
    sig = []
    seen = set()
    for d in docs:
        for sent in SENT_SPLIT.split(d):
            sent = sent.strip()
            if len(sent) < 12 or len(sent) > 80:
                continue
            if any(w in sent for w in MARKER_GROUPS["viewpoint"]):
                key = sent[:20]
                if key in seen:
                    continue
                seen.add(key)
                sig.append(sent)
                if len(sig) >= 40:
                    break
        if len(sig) >= 40:
            break

    struct = STRUCTURE.get(writer, {})
    profile = {
        "writer": writer,
        "corpus_stats": {
            "chunks": len(docs),
            "total_chars": total_chars,
            "avg_chunk_chars": round(total_chars / max(len(docs), 1)),
        },
        "markers": {g: dict(marker_counts[g].most_common()) for g in marker_counts},
        "top_openings": [o for o, _ in opening.most_common(15)],
        "signature_viewpoints": sig,
        "structure": {
            "label": struct.get("label", ""),
            "core": struct.get("core", ""),
            "stages": [{"name": n, "purpose": p} for n, p in struct.get("stages", [])],
        },
    }
    return profile


def main():
    for writer in ("maqianzu", "lukewen", "jiubian"):
        print(f"[蒸馏] {writer} ...")
        try:
            prof = distill_writer(writer)
        except Exception as e:
            print(f"  ✗ {writer} 失败: {e}")
            continue
        out = PROFILES_DIR / f"{writer}_profile.json"
        out.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ {writer}: {prof['corpus_stats']['chunks']} 块 | "
              f"{len(prof['signature_viewpoints'])} 论点句 | -> {out.name}")


if __name__ == "__main__":
    main()
