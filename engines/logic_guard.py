# -*- coding: utf-8 -*-
"""
logic_guard.py — 逻辑一致性与幻觉守卫引擎

改编自衍梦文枢 v2 的 HallucinationDetector + TimelineTracker + CausalLogic
针对政经评论场景重新设计：

检测维度:
1. 事实声明标记  — 识别需要验证的断言（数字/日期/政策引用）
2. 逻辑矛盾检测  — 前后不一致的论点（"A导致B" vs "A与B无关"）
3. 因果链完整性  — 论点间是否有完整的因果推理（因为X所以Y）
4. 时间线一致性  — 事件时间顺序是否合理

用法:
    from engines.logic_guard import LogicGuard
    guard = LogicGuard()
    result = guard.scan(text)
    # → {"statements": [...], "contradictions": [...], "causal_score": 0-100, ...}
"""

from __future__ import annotations
import re
from collections import defaultdict
from typing import Optional


# ============================================================
#  事实声明提取
# ============================================================

# 需要验证的事实声明模式
FACT_PATTERNS = [
    # 历史日期声明
    (r'(?:在|于|从)\s*(\d{4})\s*年\s*', "历史日期"),
    # 政策/法律引用
    (r'(?:根据|依照|按照)\s*[《「『].{2,30}[》」』]', "政策法规"),
    # 具体数据声明
    (r'\d{4}\s*年\s*[^。！？]{0,20}(?:达到|超过|实现|完成|发布|出台|成立|建立|发生)', "事件声明"),
    # 排名/对比
    (r'(?:全球|全国|世界|亚洲|位居)[^。！？]{3,20}(?:第一|第二|第三|首位|前列|领先)', "排名"),
    # 制度/政策名称
    (r'[《「「『][^》」」』]{4,30}[》」」』]', "政策文件名称"),
    # 百分比/数据声明
    (r'\d+\.?\d*%[^。！？]{0,20}(?:表明|显示|说明|意味)', "数据推论"),
]

# 声明可信度关键词
CERTAINTY_HIGH = r'肯定|必然|一定|毫无疑问|毋庸置疑|事实证明|历史证明'
CERTAINTY_MED = r'大概率|很可能|有望|应该|预计|大概率'
CERTAINTY_LOW = r'也许|或许|可能|大概|似乎|恐怕|猜测|推测|不一定'


# ============================================================
#  逻辑信号词
# ============================================================

# 因果信号
CAUSAL_FORWARD = r'因为|由于|源于|来自于|起因于|得益于'  # 原因→结果
CAUSAL_BACKWARD = r'因此|所以|从而|进而|于是|导致|引发|带来|催生|促使'  # 结果←原因

# 转折/矛盾信号
CONTRADICTION_SIGNALS = r'然而|但是|不过|相反|恰恰|倒[是]?|实则|其实'

# 对立论点模式
OPPOSING_CLAIMS = [
    (r'(?:A|甲|前[者]?).{3,30}(?:比|优于|好于|强于|超过).{3,30}(?:B|乙|后[者]?)', "比较级"),
    (r'不是.{4,30}而是.{4,30}', "否定肯定"),
    (r'虽然.{3,30}但是.{3,30}', "转折让步"),
    (r'与其.{3,30}不如.{3,30}', "取舍比较"),
]


# ============================================================
#  LogicGuard 核心类
# ============================================================

class LogicGuard:
    """逻辑一致性与幻觉守卫"""

    def __init__(self):
        self._claims: dict[str, list[dict]] = defaultdict(list)
        self._timeline: list[dict] = []

    def scan(self, text: str) -> dict:
        """
        扫描文本的逻辑一致性和事实声明质量

        返回:
            {"facts": [...], "contradictions": [...],
             "causal_chain": {...}, "timeline": {...},
             "summary": {...}}
        """
        sents = [s.strip() for s in re.split(r'(?<=[。！？\n])', text) if len(s.strip()) > 15]
        total_sents = len(sents)

        facts = []
        contradictions = []
        causal_links = []
        timeline_events = []
        claim_pairs = []  # 用于矛盾检测

        for i, sent in enumerate(sents):
            sent_clean = sent.strip()

            # === 1. 提取事实声明 ===
            for pattern, fact_type in FACT_PATTERNS:
                matches = re.findall(pattern, sent_clean)
                if matches:
                    # 判断可信度
                    certainty = "high" if re.search(CERTAINTY_HIGH, sent_clean) else \
                                "medium" if re.search(CERTAINTY_MED, sent_clean) else \
                                "low" if re.search(CERTAINTY_LOW, sent_clean) else "unstated"

                    # 提取年份
                    years = re.findall(r'(\d{4})\s*年', sent_clean)

                    facts.append({
                        "sentence": sent_clean[:80] + ("..." if len(sent_clean) > 80 else ""),
                        "type": fact_type,
                        "certainty": certainty,
                        "year": years[0] if years else None,
                        "para_index": i,
                    })

                    # 记录声明内容用于矛盾检测
                    claim_pairs.append((i, sent_clean[:60], fact_type))
                    break

            # === 2. 因果链提取 ===
            has_cause = bool(re.search(CAUSAL_FORWARD, sent_clean))
            has_effect = bool(re.search(CAUSAL_BACKWARD, sent_clean))

            if has_cause or has_effect:
                causal_links.append({
                    "sentence": sent_clean[:80] + "...",
                    "direction": "cause→effect" if has_cause else "effect←cause",
                    "para_index": i,
                })

            # === 3. 时间线事件提取 ===
            year_match = re.search(r'(\d{4})\s*年', sent_clean)
            if year_match:
                year = int(year_match.group(1))
                # 找事件关键词
                event_match = re.search(r'(?:[^。！？]{5,40}?(?:成立|发布|出台|举办|召开|爆发|发生|实施|启动|签署|达成))', sent_clean)
                if event_match:
                    timeline_events.append({
                        "year": year,
                        "event": event_match.group()[:40],
                        "sentence": sent_clean[:60] + "...",
                        "para_index": i,
                    })

        # === 4. 矛盾检测 ===
        contradictions = self._detect_contradictions(claim_pairs, sents)

        # === 5. 时间线一致性 ===
        timeline_issues = self._check_timeline(timeline_events)

        # === 6. 综合评分 ===
        stats = {
            "total_sentences": total_sents,
            "fact_claims": len(facts),
            "causal_links": len(causal_links),
            "timeline_events": len(timeline_events),
            "contradictions_found": len(contradictions),
            "timeline_issues": len(timeline_issues),
        }

        # 评分
        fact_score = min(100, stats["fact_claims"] * 10)  # 有事实声明加分
        causal_score = min(100, stats["causal_links"] * 15 + 10)  # 有因果链加分
        contradiction_penalty = stats["contradictions_found"] * 25  # 矛盾扣分
        timeline_score = max(0, 100 - stats["timeline_issues"] * 30) if stats["timeline_events"] > 0 else 50

        overall = max(0, min(100, (fact_score + causal_score + timeline_score) / 3 - contradiction_penalty / 3))

        status = "good" if overall >= 70 else \
                 "needs_revision" if overall >= 40 else "has_issues"

        issues = []
        if contradictions:
            issues.append(f"检测到 {len(contradictions)} 处逻辑矛盾")
        if timeline_issues:
            issues.append(f"时间线有 {len(timeline_issues)} 处问题")
        if stats["causal_links"] == 0:
            issues.append("全文无因果推理链，文章可能只是事实罗列")
        if stats["fact_claims"] == 0:
            issues.append("未检测到明确的事实声明，文章可能偏空洞")
        if stats["fact_claims"] > 0:
            low_certainty = sum(1 for f in facts if f["certainty"] == "low")
            if low_certainty > stats["fact_claims"] * 0.5:
                issues.append(f"超过半数事实声明使用模糊措辞({low_certainty}/{stats['fact_claims']})")

        return {
            "overall_score": round(overall, 1),
            "status": status,
            "scores": {
                "fact_quality": fact_score,
                "causal_logic": causal_score,
                "timeline": timeline_score,
            },
            "stats": stats,
            "facts": facts[:15],  # 只返回前15条
            "causal_links": causal_links[:10],
            "timeline_events": timeline_events[:10],
            "contradictions": contradictions,
            "timeline_issues": timeline_issues,
            "issues": issues,
        }

    def _detect_contradictions(self, claim_pairs: list[tuple], sents: list[str]) -> list[dict]:
        """检测前后矛盾：对同一主题持相反立场"""
        contradictions = []

        # 简单的否定-否定检测
        negated_claims = defaultdict(list)

        for i, claim_text, claim_type in claim_pairs:
            # 检查包含否定词的声明
            negation = re.search(r'不[是否会是能应该可以具有]|没有[什么任何]|并非|绝不是', claim_text)
            if negation:
                # 提取主题词（去掉否定词）
                topic = claim_text[:negation.start()].strip()[-10:] if negation.start() > 5 else claim_text[:20]
                negated_claims[topic].append({
                    "para_index": i,
                    "original": claim_text + "...",
                    "negation": negation.group(),
                })

        # 检查同一主题是否既肯定又否定
        # （简化版：如果有两个否定声明相近，标记为潜在矛盾）
        for topic, claims in negated_claims.items():
            if len(claims) >= 2:
                for j in range(len(claims) - 1):
                    c1, c2 = claims[j], claims[j + 1]
                    if abs(c1["para_index"] - c2["para_index"]) > 2:  # 相隔2段以上
                        contradictions.append({
                            "type": "可能矛盾",
                            "topic": topic,
                            "claim_a": c1["original"],
                            "claim_b": c2["original"],
                            "position_a": c1["para_index"],
                            "position_b": c2["para_index"],
                        })

        return contradictions[:5]

    def _check_timeline(self, events: list[dict]) -> list[dict]:
        """检查时间线一致性：事件应按时间顺序排列"""
        issues = []
        for i in range(1, len(events)):
            if events[i]["year"] < events[i - 1]["year"]:
                # 允许少量回溯（回忆、对比历史）
                gap = events[i - 1]["year"] - events[i]["year"]
                if gap > 5:  # 回溯超过5年需要标记
                    issues.append({
                        "type": "时间跳跃回溯",
                        "from": events[i - 1]["year"],
                        "to": events[i]["year"],
                        "gap": gap,
                        "event_before": events[i - 1]["event"],
                        "event_after": events[i]["event"],
                    })
        return issues

    def extract_unsupported_claims(self, text: str) -> list[dict]:
        """
        提取缺乏支撑的断言（需要额外验证的声明）

        用于写作过程中的自查：哪些断言需要补充来源或论据
        """
        sents = [s.strip() for s in re.split(r'(?<=[。！？\n])', text) if 25 < len(s.strip()) < 200]
        unsupported = []

        # 强判断但不含来源的句子
        for i, sent in enumerate(sents):
            # 含有强判断词
            has_judgment = bool(re.search(r'决定[了]?|必然|一定[会]?|毫无疑问|肯定[不]?[会不会是]|必须|绝对', sent))
            has_hedging = bool(re.search(r'也许|或许|可能|大概|似乎|恐怕', sent))
            has_source = bool(re.search(r'据[^。！？]{2,20}(?:数据|统计|报告|研究|调查|分析)|根据[^。！？]{2,20}', sent))
            has_signal = bool(re.search(r'因为|所以|因此|从而|据此|由此[可看]?[见知]?|表明|显示|证明', sent))

            # 强判断 + 无来源 + 有推理信号 → 可疑断言
            if has_judgment and not has_source and has_signal:
                unsupported.append({
                    "sentence": sent[:80] + ("..." if len(sent) > 80 else ""),
                    "reason": "强判断结论缺少数据支撑",
                    "para_index": i,
                })
            # 弱判断 + 无来源 + 有推理信号 → 可接受的推断
            elif has_hedging and not has_source:
                unsupported.append({
                    "sentence": sent[:80] + ("..." if len(sent) > 80 else ""),
                    "reason": "推断性结论，建议补充论据",
                    "para_index": i,
                })

        return unsupported[:10]

    def check_causal_completeness(self, text: str) -> dict:
        """
        检查因果链完整性：
        好的文章有完整的"原因→中间变量→结果"链条
        AI文章常出现"跳跃式因果"——直接从原因跳到结论
        """
        sents = [s.strip() for s in re.split(r'(?<=[。！？\n])', text) if len(s.strip()) > 20]

        # 统计因果信号间距
        causal_positions = []
        for i, sent in enumerate(sents):
            if re.search(CAUSAL_FORWARD, sent) or re.search(CAUSAL_BACKWARD, sent):
                causal_positions.append(i)

        if len(causal_positions) < 2:
            return {"causal_density": 0, "status": "no_causal_logic", "suggestion": "文章缺少因果推理链"}

        # 因果间距：越密集说明推理越充分
        avg_gap = sum(causal_positions[j] - causal_positions[j - 1]
                      for j in range(1, len(causal_positions))) / max(1, len(causal_positions) - 1)

        # 如果因果信号平均间隔超过5句，说明跳跃过大
        if avg_gap > 5:
            status = "jumpy"
            suggestion = f"因果推理跳跃过大(平均间隔{avg_gap:.0f}句)，建议在原因和结论之间补充中间论证"
        elif avg_gap > 3:
            status = "adequate"
            suggestion = "因果推理链条基本完整"
        else:
            status = "dense"
            suggestion = "因果推理密度高，逻辑紧密"

        return {
            "causal_density": round(len(causal_positions) / max(1, len(sents)) * 100, 1),
            "causal_signal_count": len(causal_positions),
            "avg_gap_sentences": round(avg_gap, 1),
            "status": status,
            "suggestion": suggestion,
        }


# ============================================================
#  便捷接口
# ============================================================

def scan_logic(text: str) -> dict:
    """扫描文本逻辑质量"""
    guard = LogicGuard()
    return guard.scan(text)


def check_causal(text: str) -> dict:
    """检查因果链完整性"""
    guard = LogicGuard()
    return guard.check_causal_completeness(text)


if __name__ == "__main__":
    import json

    guard = LogicGuard()

    # 测试1: 正常文章
    test1 = """为什么中国的芯片产业总是被卡脖子？
从数据来看，2023年中国进口芯片金额超过3500亿美元，是全球最大的芯片消费市场。
这个问题的本质，在于过去二十年我们走了"贸工技"的弯路。
当全球半导体产业链分工明确时，买芯片比造芯片更划算。
因此，当美国开始技术封锁时，这种依赖就成了致命弱点。
解决问题的核心，在于建立完整的国产半导体产业链。
2006年国家发布了《国家中长期科学和技术发展规划纲要》，将芯片列为重点攻关方向。
但十几年过去了，国产芯片自给率仍然不到20%。"""

    print("=== 测试1: 逻辑扫描 ===")
    r1 = guard.scan(test1)
    print(f"评分: {r1['overall_score']}/100 ({r1['status']})")
    print(f"事实声明: {r1['stats']['fact_claims']} | 因果链: {r1['stats']['causal_links']} | 矛盾: {r1['stats']['contradictions_found']}")
    for i in r1["issues"]:
        print(f"  - {i}")
    print()

    print("=== 测试2: 因果链完整性 ===")
    r2 = guard.check_causal_completeness(test1)
    print(f"密度: {r2['causal_density']}% | 间距: {r2['avg_gap_sentences']}句 | {r2['status']}")
    print(f"建议: {r2['suggestion']}")
    print()

    # 测试3: 矛盾检测
    test2 = """从长期来看，降低关税必然有利于国内产业升级。
因为国际竞争会倒逼企业提高效率。
但是，降低关税也必然导致国内产业萎缩。
大量企业会在国际竞争中被淘汰。"""
    print("=== 测试3: 矛盾检测 ===")
    r3 = guard.scan(test2)
    print(f"评分: {r3['overall_score']}/100")
    for c in r3["contradictions"]:
        print(f"  矛盾: {c['claim_a'][:40]}... ↔ {c['claim_b'][:40]}...")
    for i in r3["issues"]:
        print(f"  - {i}")
