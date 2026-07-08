# -*- coding: utf-8 -*-
"""
methodology/methodology_engine.py — 方法论迁移引擎

把蒸馏出的「方法论画像」套到【任意新题】上，生成结构化写作骨架。
核心原则（对齐用户对"黑盒"的拒绝）：
  - 骨架由方法论驱动，不依赖 RAG 是否命中 —— 因此能分析语料里【从未出现】的新事物
  - RAG 检索降级为「已覆盖话题」的可选证据补充
  - 招牌论点句作为"角度风格样本"直接 expose，模型模仿的是"怎么想"而非"写了什么"

用法：
    from methodology.methodology_engine import instantiate
    scaffold = instantiate("jiubian", "2026 年的量子计算对普通人意味着什么")
    # scaffold["outline"] 即为四段骨架；scaffold["rag_evidence"] 为可选真实引用
"""

import os, json
from pathlib import Path
from typing import Optional

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

PROFILE_DIR = Path(__file__).resolve().parent / "profiles"
_profile_cache: dict = {}

# 每个论证阶段的方法论提示词（融合画像的标记风格，教模型"怎么想"）
STAGE_HINTS = {
    "背景": "用历史/长期视角拉长时间线铺垫，先用'其实'式认知反转破除常识误区",
    "现象": "落到当下某个具体、可感知的变化，多用'但是/不过'制造认知落差",
    "深度": "挖机制/惯性/底层逻辑，避免情绪化；可用'本质上/关键在于'收束判断",
    "开放": "给概率判断而非绝对结论，留白；用'也许/大概率/拭目以待'收尾",
    "问题": "抛一个具体矛盾/现象，制造认知落差，点出'为什么值得关注'",
    "数据": "用公开数据把问题拆开（统计/对比/百分比），让数字说话",
    "分析": "挖机制/根源，从结构而非情绪看；用'本质/机理/逻辑'推进",
    "方案": "给对策/出路/方向，用'应当/需要/关键是'落地",
    "地缘": "把议题定位到文明/大国坐标，先定'在哪盘棋里'",
    "冲突": "点出矛盾/博弈/争夺，用'然而/不过'强化张力",
    "推演": "按逻辑必然性推导走向，用'导致/引发/决定'串因果",
    "前景": "给出未来趋势判断，用'未来/大概率/走向'收束",
}


def load_profile(writer: str) -> Optional[dict]:
    if writer in _profile_cache:
        return _profile_cache[writer]
    path = PROFILE_DIR / f"{writer}_profile.json"
    if not path.exists():
        return None
    prof = json.loads(path.read_text(encoding="utf-8"))
    _profile_cache[writer] = prof
    return prof


def instantiate(writer: str, topic: str, supplement_rag: bool = True,
                top_k: int = 3, max_distance: float = 0.8) -> dict:
    """把方法论画像实例化到新题，返回结构化写作骨架。

    即使该话题在语料中从未出现，也能产出骨架（方法论与话题无关）。
    max_distance: RAG 命中距离阈值，高于此值的视为不相关噪声直接丢弃，
                  保证"未覆盖话题"的 rag_evidence 真正为空。
    """
    prof = load_profile(writer)
    if prof is None:
        return {"error": f"未找到 {writer} 的方法论画像，请先运行 distill.py"}

    stages = prof["structure"]["stages"]
    outline = []
    for st in stages:
        name = st["name"]
        outline.append({
            "stage": name,
            "purpose": st["purpose"],
            "method_hint": STAGE_HINTS.get(name, st["purpose"]),
        })

    # 招牌论点句作为"角度风格样本"（取前 8 条，控制注入量）
    angle_samples = prof.get("signature_viewpoints", [])[:8]

    # 可选 RAG 补充：仅当话题在语料中确实被覆盖（距离低于阈值）时才有意义
    rag_evidence = []
    if supplement_rag:
        try:
            from engines.vector_search import search_writer
            hits = search_writer(writer, topic, top_k=top_k)
            for h in hits:
                dist = h.get("distance", 1.0)
                if dist > max_distance:
                    continue  # 无关噪声，丢弃
                doc = h.get("document") or ""
                if doc.strip():
                    rag_evidence.append({
                        "distance": round(dist, 3),
                        "quote": doc[:160].replace("\n", " "),
                    })
        except Exception:
            pass  # RAG 失败不影响方法论骨架

    return {
        "writer": writer,
        "topic": topic,
        "methodology_label": prof["structure"]["label"],
        "core": prof["structure"]["core"],
        "corpus_basis": prof["corpus_stats"],
        "outline": outline,
        "angle_samples": angle_samples,
        "rag_evidence": rag_evidence,
        "note": ("骨架由方法论驱动，已覆盖话题额外附 RAG 真实引用；"
                 "若 rag_evidence 为空，说明该话题语料未覆盖，"
                 "仍可凭方法论骨架写作（这正是方法论迁移的价值）。"),
    }


def format_scaffold(scaffold: dict) -> str:
    """把骨架渲染成可读文本，便于直接注入写作 prompt 或人工审阅。"""
    if "error" in scaffold:
        return scaffold["error"]
    lines = []
    lines.append(f"# 方法论实例化骨架 · {scaffold['writer']}")
    lines.append(f"话题：{scaffold['topic']}")
    lines.append(f"论证结构：{scaffold['methodology_label']}（{scaffold['core']}）")
    lines.append("")
    lines.append("## 四段骨架")
    for i, o in enumerate(scaffold["outline"], 1):
        lines.append(f"{i}. 【{o['stage']}】{o['purpose']}")
        lines.append(f"   方法提示：{o['method_hint']}")
    lines.append("")
    if scaffold["angle_samples"]:
        lines.append("## 角度风格样本（模仿「怎么想」，非「写了什么」）")
        for s in scaffold["angle_samples"]:
            lines.append(f"  - {s}")
        lines.append("")
    if scaffold["rag_evidence"]:
        lines.append("## RAG 真实证据（已覆盖话题补充）")
        for e in scaffold["rag_evidence"]:
            lines.append(f"  - [{e['distance']}] {e['quote']}")
    else:
        lines.append("## RAG 证据：空（该话题语料未覆盖，凭方法论骨架写作）")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    w = sys.argv[1] if len(sys.argv) > 1 else "jiubian"
    t = sys.argv[2] if len(sys.argv) > 2 else "2026 年的量子计算对普通人意味着什么"
    sc = instantiate(w, t)
    print(format_scaffold(sc))
