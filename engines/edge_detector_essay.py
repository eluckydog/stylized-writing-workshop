# -*- coding: utf-8 -*-
"""
edge_detector_essay.py — 政经评论风格检测器

改编自 衍梦文枢v2 edge_detector_v2.py
核心哲学：好作品走极端，AI安全就是平庸。

检测维度（政经评论专版）:
1. 句长节奏     — 蓄力→爆发→回落 vs 均匀安全
2. 数据密度     — 数字/百分比/对比引用频率（马前卒核心指标）
3. 金句密度     — 排比/反问/对仗，政论金句阈值降低
4. AI安全词     — "值得深思、具有重要意义"等套话检测
5. 论证结构     — 问题→分析→方案三段论完整性
6. 修辞集中度   — 政论修辞（排比/反问/对比）空间分布
"""

import re
import math
from collections import Counter
from typing import Optional

# lang_config for bilingual support
try:
    from . import lang_config as lc
except ImportError:
    import lang_config as lc


# ═══════════════════════════════════════════════
# 1. 句长节奏检测
# ═══════════════════════════════════════════════
def detect_sentence_rhythm(text: str) -> dict:
    """
    分析句长结构是否为"蓄力→爆发→回落"有机节奏。
    政经评论的句长通常比小说更长、更稳定。
    """
    sents = [s.strip() for s in re.split(r'[。！？\n；]', text) if len(s.strip()) > 5]
    if len(sents) < 10:
        return {"std_sent": 0, "rhythm_score": 50, "is_safe": False, "pattern": "too_short"}

    sent_lens = [len(s) for s in sents]
    n = len(sent_lens)
    avg = sum(sent_lens) / n
    std = (sum((x - avg) ** 2 for x in sent_lens) / n) ** 0.5

    # 滑动窗口方差
    window = min(7, max(3, n // 4))
    window_vars = []
    for i in range(n - window + 1):
        w = sent_lens[i:i + window]
        w_avg = sum(w) / len(w)
        w_var = sum((x - w_avg) ** 2 for x in w) / len(w)
        window_vars.append(w_var)
    avg_window_var = sum(window_vars) / len(window_vars) if window_vars else 0

    # 节奏交替检测（短-长-短或长-短-长）
    rhythm_strength = 0
    for i in range(1, n - 1):
        prev, cur, nxt = sent_lens[i - 1], sent_lens[i], sent_lens[i + 1]
        if (cur < prev and cur < nxt) or (cur > prev and cur > nxt):
            rhythm_strength += 1
    rhythm_ratio = rhythm_strength / max(1, n - 2)

    # 极值段落检测
    outlier_segments = 0
    for i in range(0, n - 3, 3):
        segment = sent_lens[i:i + 3]
        if max(segment) > avg * 1.8 or min(segment) < avg * 0.4:
            outlier_segments += 1
    outlier_ratio = outlier_segments / max(1, n // 3)

    # 综合评分（政论版阈值微调）
    std_score = min(100, std / 18 * 100)
    win_score = min(100, avg_window_var / 25 * 100)
    rhythm_score_val = min(100, rhythm_ratio / 0.25 * 100)
    outlier_score = min(100, outlier_ratio / 0.12 * 100)
    total = (std_score * 0.25 + win_score * 0.25 + rhythm_score_val * 0.25 + outlier_score * 0.25)

    # 模式判断
    if std < 10 and win_score < 25:
        pattern, is_safe = "flat", True
    elif avg_window_var < 12 and outlier_ratio < 0.04:
        pattern, is_safe = "too_smooth", True
    else:
        pattern, is_safe = "has_rhythm", False

    return {
        "std_sent": round(std, 1),
        "avg_sent_len": round(avg, 1),
        "rhythm_score": round(total, 1),
        "rhythm_alternation": round(rhythm_ratio * 100, 1),
        "outlier_segment_ratio": round(outlier_ratio * 100, 1),
        "is_safe": is_safe,
        "pattern": pattern
    }


# ═══════════════════════════════════════════════
# 2. 数据密度检测（政论专属）
# ═══════════════════════════════════════════════
def detect_data_density(text: str) -> dict:
    """
    检测文本中数据引用密度——马前卒风格核心指标。
    
    好政论：数据密度3-10条/千字，分布均匀
    AI文章：数据密度<1条/千字（空洞），或>15条/千字（堆砌）
    """
    total_chars = len(text)
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 20]
    if not paras:
        return {"density": 0, "status": "empty", "data_types": {}, "score": 0}

    total_paras = len(paras)
    paras_with_data = 0

    # 数据引用模式
    data_patterns = {
        "percentage": r'\d+\.?\d*%',                     # 百分比
        "number":     r'(?:^|[\s，。；、：])'                    # 数字引用
                      r'(\d{1,3}(?:,\d{3})*|\d+\.?\d*)'
                      r'(?:万|亿|美元|元|人|家|个|辆|吨|公里|平方米|亿人|亿次|年|月|日)',
        "ratio":      r'[一二两三四五六七八九十]分之[一二两三四五六七八九十]'
                      r'|\.\d+倍|\d+倍|比[例率]|占比|率[达超]',
        "range":      r'\d+[～~-]\d+|从\s*\d+\s*到\s*\d+|介于|处于',
        "comparison": r'超过|不足|仅仅|高达|低至|同比|环比|年均|累计|达到|突破',
    }

    compiled = {k: re.compile(v) for k, v in data_patterns.items()}

    data_counts = Counter()
    for p in paras:
        para_hit = False
        for kind, pat in compiled.items():
            hits = pat.findall(p)
            if hits:
                data_counts[kind] += len(hits)
                para_hit = True
        if para_hit:
            paras_with_data += 1

    total_data = sum(data_counts.values())
    density = total_data / max(1, total_chars / 1000)

    # 数据分布：有数据的段落占比
    data_spread = paras_with_data / max(1, total_paras)

    # 评分
    if density < 1:
        status, score = "data_void", 0
    elif density < 3:
        status, score = "sparse", 30
    elif density < 12:
        status, score = "good", 85
    elif density < 18:
        status, score = "dense", 70
    else:
        status, score = "overload", 40

    return {
        "density": round(density, 2),
        "total_data_points": total_data,
        "data_types": dict(data_counts),
        "data_spread": round(data_spread, 3),
        "paras_with_data_ratio": round(paras_with_data / max(1, total_paras), 3),
        "status": status,
        "score": score
    }


# ═══════════════════════════════════════════════
# 3. 金句密度检测（政论版）
# ═══════════════════════════════════════════════
def detect_golden_sentence(text: str) -> dict:
    """
    政论版金句检测。
    政经评论的金句阈值更低——3-8%即优秀，>15%浮夸。
    """
    total_chars = len(text)
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 20]
    if not paras:
        return {"density_pct": 0, "distribution": "too_short", "status": "unknown", "score": 0}

    # 政论金句特征（排比、对仗、设问、对比、警句）
    golden_patterns = [
        r'(?:不是|并非|绝不是)[^。！？;；]{4,30}(?:而是|乃是|而是说)[^。！？;；]{4,30}',
        r'(?:为什么|何以|为何|凭什么|怎么[会能]).{5,50}[？?].{5,80}[。！]',
        r'(?:无论|不管|不论).{3,20}(?:还是|或是).{3,20}(?:都|均|总)',
        r'(?:越|愈)[^。！？，；]{3,20}(?:越|愈)[^。！？，；]{3,20}',
        r'(?:从|在|当|让|把|将|用|以)[^。！？，；]{5,25}(?:，|;)[^。！？，；]{5,25}(?:，|;)[^。！？，；]{5,25}',
        r'(?:所谓|正(如|是)|可(谓|见)|不难看[出到]|归根结底|本(质|源)[上]?|从来[没有]|真正[的])',
        r'(?:不只|不仅|不但|非但).{3,25}(?:而且|还|更|也|亦|同样|甚至).{3,25}(?:更|甚至|乃至|况且)',
        r'决定[性]?的[^。！？]{2,20}不在于[^。！？]{2,20}',
    ]

    golden_chars = 0
    golden_spans = []

    for p in paras:
        for pat in golden_patterns:
            for m in re.finditer(pat, p):
                golden_spans.append((m.start(), m.end(), p))
                golden_chars += m.end() - m.start()

    # 合并重叠区间
    total_golden = 0
    if golden_spans:
        flat_spans = [(s, e) for s, e, _ in golden_spans]
        flat_spans.sort()
        merged = [flat_spans[0]]
        for s, e in flat_spans[1:]:
            if s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        total_golden = sum(e - s for s, e in merged)

    density = total_golden / max(1, total_chars) * 100

    # 分布判断
    if golden_spans and len(paras) > 3:
        mid = len(paras) // 3
        positions = []
        for s, e, p in golden_spans:
            try:
                positions.append(paras.index(p))
            except ValueError:
                pass
        if positions:
            first_third = sum(1 for pos in positions if pos < mid)
            last_third = sum(1 for pos in positions if pos >= 2 * mid)
            total_pos = len(positions)
            scatter = (first_third + last_third) / max(1, total_pos)
            distribution = "scattered" if scatter > 0.7 else "concentrated"
        else:
            distribution = "none"
    else:
        distribution = "none"

    # 状态（政论：3-8%为佳）
    if density > 18:
        status, score = "too_many", 20
    elif density > 10:
        status, score = "slight_excess", 50
    elif density > 2.5:
        status, score = "good", 90
    else:
        status, score = "few", 30

    return {
        "density_pct": round(density, 2),
        "golden_span_count": len(golden_spans),
        "distribution": distribution,
        "status": status,
        "score": score,
        "warning": density > 15 or (density > 10 and distribution == "scattered")
    }


# ═══════════════════════════════════════════════
# 4. AI安全词检测（政论专属）
# ═══════════════════════════════════════════════
def detect_ai_safe_words(text: str, lang: str = "zh") -> dict:
    """
    检测 AI 套话/安全词——政经评论的特有"AI味"指标。
    
    AI文章特征：大量使用表意模糊的宏大词汇、安全表态、
    空泛评价等"说了等于没说"的句式。
    """
    total_chars = len(text)

    # 安全词分类（支持中英文，从 lang_config 加载）
    safe_word_categories = lc.get_nested("edge_detector", "ai_safe_words", lang=lang)
    if not safe_word_categories:
        safe_word_categories = {
        "空洞表态": [
            r'值得[我深]?[们思]?[深思关注思考警惕注意重视肯定称道]',
            r'具有[极其]?[重要深远重大特殊][意(?:义|思)][深远]?',
            r'不[可容]?[忽视忽略小觑低估]',
            r'引[起了广泛关注热议讨论思考]',
            r'得到了[社会各界的广泛认可高度评价一致好评普遍赞誉]',
        ],
        "万能结论": [
            r'路[还]?[很长仍然漫长尚远]',
            r'任[重务]?[而道远艰巨]',
            r'[迟迟](?:早|将).{0,10}(?:实现|解决|到来)',
            r'有待[进一步深入持续]?(?:观察|研究|完善|改进|加强|提高|探索)',
            r'需要[我们全社会各方共同努力携手合作协同推进]',
        ],
        "模糊递进": [
            r'不[仅仅光但]?[是如止]此',
            r'更[为重关键的]?[重要关键核心的是]',
            r'从[某种根本宏观的]?[意义角度层面][上来说看讲]',
            r'在[很大某种一定]?[程度上意义层面]',
            r'归根[到底结底]',
        ],
        "空泛评价": [
            r'[开启谱写书写迎来迈入开创]了[新的崭新全新时代篇章征程局面]',
            r'[有力显著切实充分]地[推动促进提升增强推进加强]',
            r'[必将会将]?[为推动为促进为加快]',
            r'标志[了着]?[一个新的重要的历史性]?[开始开端起点里程碑]',
            r'体现了[我党我国政府我们各方]?的[高度巨大充分]?[重视决心诚意担当]',
        ],
    }

    category_hits = {}
    total_hits = 0

    for category, patterns in safe_word_categories.items():
        hits = []
        for pat in patterns:
            matches = re.findall(pat, text)
            hits.extend(matches)
        if hits:
            category_hits[category] = len(hits)
            total_hits += len(hits)

    density = total_hits / max(1, total_chars / 1000)

    if density > 3:
        status, score = "heavy", 15
    elif density > 1.5:
        status, score = "noticeable", 40
    elif density > 0.5:
        status, score = "light", 70
    else:
        status, score = "clean", 95

    return {
        "density": round(density, 2),
        "total_hits": total_hits,
        "categories": category_hits,
        "status": status,
        "score": score
    }


# ═══════════════════════════════════════════════
# 5. 论证结构检测
# ═══════════════════════════════════════════════
def detect_argument_structure(text: str) -> dict:
    """
    检测论证三段论的完整性：问题→分析→方案。
    
    好政论：三要素齐全，且按顺序排列
    AI文章：三要素缺失或结构混乱
    """
    # 问题信号
    problem_signals = [
        r'(?:什么|为何|怎么|如何|怎样|为什么|何以|难道|是否)',
        r'(?:问题|矛盾|困境|危机|挑战|风险|隐忧|症结|弊端|困境)',
        r'(?:值得|需要|令人|引人)[关注深思警惕思考重视]',
    ]
    analysis_signals = [
        r'(?:本质|根源|原因|逻辑|机理|机制|规律|模式|结构|框架)',
        r'(?:第一|第二|第三|首先|其次|再次|最后|一方面|另一方面)',
        r'(?:数据|统计|调研|研究|分析|对比|案例|样本|趋势|拐点)',
        r'(?:从[^。！？]{4,30}看[来]?|[^。！？]{4,30}表明|数据显示)',
    ]
    solution_signals = [
        r'(?:建议|方案|对策|措施|路径|出路|方向|目标|策略|办法)',
        r'(?:应当|应该|需要|必须|务必|建议|提倡|鼓励|支持|推动)',
        r'(?:如果|假如|假设)[^。！？]{5,50}(?:那么|则|就|便)',
        r'(?:关键是|核心是|重点是|当务之急|首要任务|重中之重)',
    ]

    # 分段检测
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 30]
    total = len(paras)
    if total < 3:
        return {"has_problem": False, "has_analysis": False, "has_solution": False,
                "structure_score": 0, "status": "too_short"}

    para_flags = []
    for p in paras:
        flags = {"problem": False, "analysis": False, "solution": False}
        for pat in problem_signals:
            if re.search(pat, p):
                flags["problem"] = True
                break
        for pat in analysis_signals:
            if re.search(pat, p):
                flags["analysis"] = True
                break
        for pat in solution_signals:
            if re.search(pat, p):
                flags["solution"] = True
                break
        para_flags.append(flags)

    has_problem = any(f["problem"] for f in para_flags)
    has_analysis = any(f["analysis"] for f in para_flags)
    has_solution = any(f["solution"] for f in para_flags)

    # 检测顺序：问题在前1/3，分析在中段，方案在后1/3
    order_score = 0
    prob_pos = next((i for i, f in enumerate(para_flags) if f["problem"]), None)
    anal_pos = next((i for i, f in enumerate(para_flags) if f["analysis"]), None)
    solu_pos = next((i for i, f in enumerate(para_flags) if f["solution"]), None)

    if prob_pos is not None and prob_pos < total * 0.5:
        order_score += 35
    if anal_pos is not None and (solu_pos is None or anal_pos < solu_pos):
        order_score += 35
    if solu_pos is not None and solu_pos > total * 0.3:
        order_score += 30

    completeness = sum([has_problem, has_analysis, has_solution])
    if completeness == 3:
        status = "complete"
    elif completeness == 2:
        status = "partial"
    else:
        status = "weak"

    return {
        "has_problem": has_problem,
        "has_analysis": has_analysis,
        "has_solution": has_solution,
        "structure_score": order_score,
        "status": status,
        "problem_position": round(prob_pos / max(1, total), 2) if prob_pos is not None else None,
        "analysis_position": round(anal_pos / max(1, total), 2) if anal_pos is not None else None,
        "solution_position": round(solu_pos / max(1, total), 2) if solu_pos is not None else None,
    }


# ═══════════════════════════════════════════════
# 6. 修辞集中度检测（政论版）
# ═══════════════════════════════════════════════
def detect_rhetoric_clustering(text: str) -> dict:
    """
    政论版修辞检测。政论修辞以排比、对比、反问为主。
    """
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 20]
    if len(paras) < 5:
        return {"clustering_score": 50, "gini_coefficient": 0, "is_uniform": False, "reason": "too_few_paragraphs"}

    rhetoric_patterns = [
        r'不(仅|但|光|只)[^。！？]{3,25}(?:而且|还|更|也|亦)',  # 递进
        r'不是[^。！？]{3,25}而是[^。！？]{3,25}',  # 对比
        r'难道|岂非|何尝|怎能|如何能',  # 反问
        r'越[^。！？，；]{2,15}越[^。！？，；]{2,15}',  # 越…越
        r'无论|不管|不论.{3,20}(?:还是|或是).{3,20}(?:都|均|总)',  # 条件排比
        r'一[边面方][^。！？，；]{2,15}一[边面方][^。！？，；]{2,15}',  # 对举
        r'从[^。！？，；]{3,20}到[^。！？，；]{3,20}',  # 从…到
        r'既[^。！？，；]{2,15}又[^。！？，；]{2,15}',  # 既…又
    ]

    para_densities = []
    for p in paras:
        count = sum(len(re.findall(pat, p)) for pat in rhetoric_patterns)
        density = count / max(1, len(p)) * 1000
        para_densities.append(density)

    n = len(para_densities)
    total_den = sum(para_densities)
    avg_den = total_den / n

    # 基尼系数
    sorted_dens = sorted(para_densities)
    gini = 0
    for i, d in enumerate(sorted_dens):
        gini += (2 * i - n + 1) * d
    if n > 0 and total_den > 0:
        gini = gini / (n * total_den)
    else:
        gini = 0

    # Top-3聚集度
    indexed = sorted([(d, i) for i, d in enumerate(para_densities)], reverse=True)
    top3_indices = sorted([idx for _, idx in indexed[:3]])
    spread = (top3_indices[-1] - top3_indices[0]) / max(1, n) if len(top3_indices) > 1 else 0

    gini_score = min(100, gini / 0.4 * 100)
    spread_score = 100 - min(100, spread / 0.6 * 100)
    total = gini_score * 0.5 + spread_score * 0.5
    is_uniform = gini < 0.25

    return {
        "clustering_score": round(total, 1),
        "overall_density": round(avg_den, 2),
        "gini_coefficient": round(gini, 3),
        "top3_spread_ratio": round(spread, 3),
        "is_uniform": is_uniform
    }


# ═══════════════════════════════════════════════
# 综合评分
# ═══════════════════════════════════════════════
def full_report(text: str, lang: Optional[str] = None) -> dict:
    """返回完整的政经评论风格检测报告
    
    lang: "zh" | "en", 默认自动检测
    """
    if lang is None:
        lang = lc.detect_lang(text)
    """返回完整的政经评论风格检测报告"""
    rhythm = detect_sentence_rhythm(text)
    data_density = detect_data_density(text)
    golden = detect_golden_sentence(text)
    ai_safe = detect_ai_safe_words(text)
    argument = detect_argument_structure(text)
    rhetoric = detect_rhetoric_clustering(text)

    # 综合评分
    scores = {
        "节奏感": rhythm["rhythm_score"],
        "数据密度": data_density["score"],
        "金句质量": golden["score"],
        "AI套话控制": ai_safe["score"],
        "论证结构": argument["structure_score"],
        "修辞集中度": rhetoric["clustering_score"],
    }
    overall = round(sum(scores.values()) / len(scores), 1)

    # 问题列表
    issues = []
    if rhythm["is_safe"]:
        issues.append({"dimension": "句长节奏", "severity": "warning",
                       "detail": f"过于均匀({rhythm['pattern']})，建议在关键段落制造长短反差"})
    if data_density["status"] == "data_void":
        issues.append({"dimension": "数据密度", "severity": "critical",
                       "detail": "全文无数据支撑，政论文章大忌"})
    elif data_density["status"] in ("sparse",):
        issues.append({"dimension": "数据密度", "severity": "warning",
                       "detail": f"数据引用偏少({data_density['density']}/千字)"})
    if golden["warning"]:
        issues.append({"dimension": "金句密度", "severity": "warning",
                       "detail": f"金句密度{golden['density_pct']}%过高，政论文章宜克制"})
    if ai_safe["status"] in ("heavy", "noticeable"):
        issues.append({"dimension": "AI套话", "severity": "critical" if ai_safe["status"] == "heavy" else "warning",
                       "detail": f"安全词密度{ai_safe['density']}/千字，含{list(ai_safe['categories'].keys())}等类别"})
    if argument["status"] == "weak":
        issues.append({"dimension": "论证结构", "severity": "critical",
                       "detail": "缺问题/分析/方案三段论要素"})
    elif argument["status"] == "partial":
        missing = []
        if not argument["has_problem"]:
            missing.append("问题")
        if not argument["has_analysis"]:
            missing.append("分析")
        if not argument["has_solution"]:
            missing.append("方案")
        issues.append({"dimension": "论证结构", "severity": "warning",
                       "detail": f"缺少{'/'.join(missing)}要素"})
    if rhetoric["is_uniform"]:
        issues.append({"dimension": "修辞分布", "severity": "notice",
                       "detail": f"修辞均匀分布(gini={rhetoric['gini_coefficient']})，建议集中到关键段落"})

    total_severity = sum(1 for i in issues if i["severity"] == "critical") * 3 \
                     + sum(1 for i in issues if i["severity"] == "warning") * 2 \
                     + sum(1 for i in issues if i["severity"] == "notice")

    if total_severity >= 6:
        status = "ai_taste"
    elif total_severity >= 3:
        status = "needs_revision"
    elif total_severity >= 1:
        status = "minor_issues"
    else:
        status = "good"

    return {
        "status": status,
        "overall_score": overall,
        "scores": scores,
        "issues": issues,
        "details": {
            "rhythm": rhythm,
            "data_density": data_density,
            "golden": golden,
            "ai_safe_words": ai_safe,
            "argument_structure": argument,
            "rhetoric": rhetoric,
        }
    }


def generate_advice(text: str, lang: Optional[str] = None) -> list[str]:
    """基于检测结果生成修改建议"""
    report = full_report(text)
    advice = []
    for issue in report["issues"]:
        advice.append(f"[{issue['severity'].upper()}] {issue['dimension']}: {issue['detail']}")
    if not advice:
        advice.append("文章风格质量良好，无明显AI味。")
    return advice


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
        print(json.dumps(full_report(text), ensure_ascii=False, indent=2))
        print("\n=== 修改建议 ===")
        for a in generate_advice(text):
            print(f"  {a}")
    else:
        # 自测
        test = """最近几年，中国的房地产市场经历了一系列调整。
值得关注的是，这一轮调整的深度和广度都超出了市场预期。
从数据来看，2024年全国商品房销售面积同比下降了15.2%，销售额下降了18.5%。
这不仅仅是周期性的波动，更是结构性转变的信号。
为什么会出现这种情况？归根结底，是过去二十年形成的"土地财政"模式走到了尽头。
当人口结构发生变化、城市化率接近瓶颈时，依靠房地产拉动经济的旧模式必然面临转型。
解决方案是什么？核心在于两点：一是建立多层次的住房供应体系，真正实现"租购并举"；
二是改革地方政府的收入结构，摆脱对土地出让金的依赖。
这需要财税体制的深层改革，路还很长。"""
        print(json.dumps(full_report(test), ensure_ascii=False, indent=2))
        print("\n=== 修改建议 ===")
        for a in generate_advice(test):
            print(f"  {a}")
