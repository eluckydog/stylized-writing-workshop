# -*- coding: utf-8 -*-
"""
citation_guard.py — 引用守卫引擎

数据来源标注强制器与引用校验：
1. 检测无来源的数据声明（"增长率达到15%" → 缺少出处）
2. 数字引用标注检查（是否有"据XXX/根据XXX"前缀）
3. 声明可信度分级（有来源 > 有具体数字 > 模糊表述 > 无依据）
4. 自动触发向量库搜索寻找支撑证据

用法:
    from engines.citation_guard import CitationGuard
    
    guard = CitationGuard()
    result = guard.scan(text)
    # → {"claims": [...], "issues": [...], "suggestions": [...]}
    
    # 可选：挂载向量搜索
    guard.set_vector_search(search_fn)
    evidence = guard.find_evidence("中国芯片进口3500亿美元")
"""

from __future__ import annotations
import re
from typing import Callable, Optional


# ============================================================
#  声明检测器
# ============================================================

# 数据声明模式
DATA_CLAIM_PATTERNS = [
    # 百分比声明
    (r'(\d+\.?\d*%)(?!\s*(?:的|的[^。！？]{0,10}(?:数据|统计|报告|调查|研究)))',
     "percentage", "无来源百分比"),
    # 数字+单位声明
    (r'(?:超过|达到|高达|低至|不足|仅仅|约|近)?'
     r'(\d{1,3}(?:,\d{3})*|\d+\.?\d*)'
     r'(?:万|亿|美元|欧元|元|人|家|个|辆|吨|公里|平方米|亿人|亿次)'
     r'(?!\s*(?:的[^。！？]{0,10}(?:数据|统计|报告)|，据|。据))',
     "numeric", "无来源数字"),
    # 排名/对比声明
    (r'(?:排名|位列|位居|排在第)\s*[第]?\d+'
     r'(?!\s*(?:的[^。！？]{0,10}(?:数据|统计|报告)|，据|。据|，来自))',
     "ranking", "无来源排名"),
    # 增长率/比例声明
    (r'(?:增长|下降|上升|降低|增加|减少)[了约近]?\s*\d+\.?\d*%'
     r'(?!\s*(?:[，。；]据))',
     "change_rate", "无来源变化率"),
    # "是XX倍" 对比
    (r'[是约为]?\s*\d+\.?\d*\s*倍'
     r'(?!\s*(?:[，。；]据))',
     "multiple", "无来源倍数对比"),
]

# 来源前缀（好的引用）
SOURCE_PREFIXES = [
    r'(?:据|根据|来自|引用|援引|依照|按照|基于)',
    r'(?:数据|统计|报告|调查|研究|分析)[显示表明指出称]',
    r'(?:据.{2,20}(?:数据|统计|报告|调查))',
    r'(?:来自.{2,20}(?:的报告|的数据|的研究))',
]

# 模糊表述（需要加固的声明）
VAGUE_PATTERNS = [
    r'(?:大量|许多|众多|不少|部分|一些|有些)[^。！？]{0,15}(?:数据|统计|研究|调查|案例)',
    r'(?:普遍|广泛|通常|一般[来]?[说讲]|总体[上来]?)',
    r'(?:明显|显著|大幅|快速|迅猛|急剧)[^。！？]{0,10}(?:增长|下降|上升|降低|变化|提升)',
]


class CitationGuard:
    """引用守卫"""

    def __init__(self):
        self._vector_search_fn: Optional[Callable] = None
        self._source_prefix_re = re.compile('|'.join(SOURCE_PREFIXES))
        self._compiled_claims = [(re.compile(pat), kind, label) for pat, kind, label in DATA_CLAIM_PATTERNS]
        self._vague_re = re.compile('|'.join(VAGUE_PATTERNS))

    def set_vector_search(self, search_fn: Callable):
        """
        挂载向量搜索函数
        
        search_fn(query: str) -> list[dict]
        返回: [{"document": "...", "metadata": {...}, "distance": 0.1}, ...]
        """
        self._vector_search_fn = search_fn

    def scan(self, text: str) -> dict:
        """
        扫描文本中的声明，检测引用质量

        返回:
            {"claims": [...], "vague_statements": [...], 
             "issues": [...], "suggestions": [...],
             "citation_score": 0-100}
        """
        # 分割为句子
        sents = [s.strip() for s in re.split(r'(?<=[。！？；\n])', text) if len(s.strip()) > 10]
        total_sents = len(sents)

        claims = []
        vague_statements = []
        sourced_count = 0
        unsourced_count = 0

        for sent in sents:
            # 检查是否有来源前缀
            has_source = bool(self._source_prefix_re.search(sent))

            # 检测数据声明
            for pattern, kind, label in self._compiled_claims:
                matches = pattern.findall(sent)
                if matches:
                    claim = {
                        "sentence": sent[:80] + "..." if len(sent) > 80 else sent,
                        "value": str(matches[0]) if matches else "",
                        "type": kind,
                        "label": label,
                        "has_source": has_source,
                    }
                    claims.append(claim)
                    if has_source:
                        sourced_count += 1
                    else:
                        unsourced_count += 1
                    break  # 一句只记一个声明

            # 检测模糊表述
            if not has_source and self._vague_re.search(sent):
                vague_statements.append({
                    "sentence": sent[:80] + "..." if len(sent) > 80 else sent,
                    "pattern": self._vague_re.search(sent).group(),
                })

        # 生成问题列表
        issues = []
        suggestions = []

        if unsourced_count > 0:
            issues.append(f"[无来源] {unsourced_count}处数字/数据声明缺少来源标注")
            suggestions.append(f"为{unsourced_count}处数据添加来源：'据XXX数据/报告/统计'")

        if sourced_count == 0 and unsourced_count > 0:
            issues.append("[全无来源] 所有数据声明均缺少出处")
            suggestions.append("每条数据都应标注来源，如'据国家统计局数据'/'根据XX报告'")

        if sourced_count > 0 and unsourced_count > sourced_count:
            issues.append(f"[来源不足] 仅{sourced_count}/{sourced_count + unsourced_count}处声明有来源")
            suggestions.append("提高来源标注比例，建议至少50%的声明有出处")

        if vague_statements:
            issues.append(f"[模糊表述] {len(vague_statements)}处使用模糊表述")
            suggestions.append(f"将{len(vague_statements)}处模糊表述替换为具体数据")

        if not claims and not vague_statements:
            issues.append("[无数据] 全篇无数据支撑")
            suggestions.append("政论文章建议至少引用3-5个数据点")

        # 引用评分
        total_claims = len(claims)
        if total_claims == 0:
            citation_score = 10  # 无数据极低分
        else:
            source_ratio = sourced_count / total_claims
            # 来源比例占60分，数据量占40分
            score = source_ratio * 60 + min(40, total_claims * 8)
            citation_score = round(min(100, score), 1)

        return {
            "citation_score": citation_score,
            "total_sentences": total_sents,
            "total_claims": total_claims,
            "sourced_claims": sourced_count,
            "unsourced_claims": unsourced_count,
            "claims": claims,
            "vague_statements": vague_statements,
            "issues": issues,
            "suggestions": suggestions,
        }

    def find_evidence(self, text_segment: str, top_k: int = 3) -> list[dict]:
        """
        对特定声明片段搜索向量库寻找支撑证据
        
        需要在初始化时通过 set_vector_search 挂载搜索函数
        """
        if not self._vector_search_fn:
            return [{"error": "未挂载向量搜索函数，请调用 set_vector_search()"}]

        results = self._vector_search_fn(text_segment, top_k=top_k)
        evidence = []
        for r in results:
            evidence.append({
                "source": r.get("metadata", {}).get("title", "未知"),
                "section": r.get("metadata", {}).get("section", ""),
                "document": r["document"][:200] if len(r["document"]) > 200 else r["document"],
                "distance": r.get("distance", 0),
                "relevance": "high" if r.get("distance", 1) < 0.7 else "medium",
            })
        return evidence

    def extract_key_claims(self, text: str) -> list[dict]:
        """提取文本中的所有关键声明（需要引用的陈述句）"""
        sents = [s.strip() for s in re.split(r'(?<=[。！？；\n])', text) if 20 < len(s.strip()) < 200]
        key_claims = []

        for sent in sents:
            # 包含判断性/观点性表述
            if any(re.search(p, sent) for p in [
                r'是[^。！？]{5,40}的[关键重要核心根本]',
                r'决定[了]?|导致|引发|驱动|推动|阻碍|制约',
                r'意味[着]?|标志[着]?|说明[了]?',
                r'因为|所以|因此|从而|进而|据此',
            ]):
                has_source = bool(self._source_prefix_re.search(sent))
                key_claims.append({
                    "sentence": sent[:100],
                    "has_source": has_source,
                    "needs_citation": not has_source,
                })

        return key_claims


# ============================================================
#  便捷接口
# ============================================================

def scan_citations(text: str) -> dict:
    """扫描文本引用质量"""
    guard = CitationGuard()
    return guard.scan(text)


def extract_claims(text: str) -> list[dict]:
    """提取所有关键声明"""
    guard = CitationGuard()
    return guard.extract_key_claims(text)


if __name__ == "__main__":
    import json

    guard = CitationGuard()

    # 测试
    test = """最近几年，中国的芯片产业取得了显著进步。
据海关总署数据，2023年中国进口芯片金额超过3500亿美元。
这导致国产芯片自给率不到20%，大量企业面临供应链风险。
从数据来看，国内芯片设计企业数量增长了30%以上。
许多研究表明，技术人才的短缺是制约行业发展的关键因素。
解决问题需要从教育体制和产业政策两方面入手。
根据SEMI的报告，全球半导体设备市场规模达到1070亿美元。"""

    result = guard.scan(test)
    print("=== 引用扫描报告 ===")
    print(f"引用可信度评分: {result['citation_score']}/100")
    print(f"声明总数: {result['total_claims']} (有来源: {result['sourced_claims']}, 无来源: {result['unsourced_claims']})")
    print()

    print("问题:")
    for i in result["issues"]:
        print(f"  {i}")
    print()

    print("建议:")
    for s in result["suggestions"]:
        print("  - " + s)
    print()

    print("声明详情:")
    for c in result["claims"]:
        src = "✓" if c["has_source"] else "✗"
        check = "YES" if c["has_source"] else "NO "
        print(f"  [{check}] {c['label']}: {c['sentence'][:60]}...")

    if result["vague_statements"]:
        print()
        print("模糊表述:")
        for v in result["vague_statements"]:
            print(f"  [{v['pattern']}] {v['sentence'][:60]}...")

    # 提取关键声明
    print("\n=== 关键声明 ===")
    claims = guard.extract_key_claims(test)
    for c in claims:
        src = "✓" if c["has_source"] else "✗ 需补充来源"
        check = "YES" if c["has_source"] else "NO "
        print(f"  [{check}] {c['sentence'][:60]}...")
