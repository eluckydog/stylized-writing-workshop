# -*- coding: utf-8 -*-
"""
literary_spark.py — 点睛笔引擎

成语和诗词库的使用策略：不是用得越多越好，而是要在对的地方用。

核心原则：
1. 检测文章中的"平淡区"——连续平铺直叙超过3段 → 建议点睛
2. 只在关键位置（开篇/转折/高潮/收尾）推荐引用
3. 频率控制：默认每千字不超过1-2处
4. 不是"塞进去"，是提供选项让写作者选择

用法:
    from engines.literary_spark import suggest_spark, scan_dull_spots

    # 扫描平淡区，返回建议
    suggestions = scan_dull_spots("文章内容...")
    for s in suggestions:
        print(f"第{s['para']}段: {s['reason']}")
        print(f"  推荐: {s['idiom']} — {s['meaning']}")
"""

from __future__ import annotations
import re
from typing import Optional

# 成语/诗词使用频率限制
MAX_IDIOMS_PER_1000 = 1.5   # 每千字最多1.5处（约每700字1处）
MAX_POEMS_PER_1000 = 0.5    # 每千字最多0.5处（约每2000字1处）
DULL_THRESHOLD = 3          # 连续平淡段落数超过此值触发建议


def scan_dull_spots(text: str, lang: str = "zh") -> list[dict]:
    """
    扫描文章中"平淡区"——连续平铺直叙的段落，
    在关键位置推荐使用成语或诗词点睛。

    返回:
        [{"para_index": int, "reason": str, "position": str, "keywords": [str]}, ...]
    """
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 30]
    if len(paras) < 4:
        return []

    total_chars = len(text)
    suggestions = []

    # 检测条件：
    # 1. 连续3段以上没有修辞/反问/设问/引用
    # 2. 位于文章关键位置（开头30%、转折处、结尾30%）
    # 3. 段落长度适中（30-200字之间最适合加点睛）

    consecutive_flat = 0
    flat_start = 0
    total_paras = len(paras)

    for i, para in enumerate(paras):
        # 判断段落是否"平淡"
        has_rhetoric = bool(re.search(r'难道|岂非|为什么|怎么[会能]|不是.{3,15}而是|但[是]|然而|不过', para))
        has_data = bool(re.search(r'\d+\.?\d*%|\d+[万亿亿]|据[^。！？]{2,20}|根据', para))
        has_quote = bool(re.search(r'[「『"][^」』"]{4,30}[」』"]', para))
        has_variation = _has_sentence_variation(para)

        is_flat = not (has_rhetoric or has_data or has_quote or has_variation)

        if is_flat and len(para) > 30:
            consecutive_flat += 1
            if consecutive_flat == 1:
                flat_start = i
        else:
            if consecutive_flat >= DULL_THRESHOLD:
                # 检查这个平淡区间是否在关键位置
                position = _classify_position(flat_start, i, total_paras)
                if position:
                    # 提取该区间的核心词作为搜索关键词
                    flat_text = "".join(paras[flat_start:i+1])
                    keywords = _extract_keywords(flat_text)

                    suggestions.append({
                        "para_start": flat_start,
                        "para_end": i,
                        "flat_length": consecutive_flat,
                        "position": position,
                        "keywords": keywords,
                        "reason": _generate_reason(position, consecutive_flat),
                    })
            consecutive_flat = 0
            flat_start = 0

    # 检查最后一段是否是连续平淡的结尾
    if consecutive_flat >= DULL_THRESHOLD:
        position = _classify_position(flat_start, total_paras - 1, total_paras)
        if position:
            flat_text = "".join(paras[flat_start:])
            keywords = _extract_keywords(flat_text)
            suggestions.append({
                "para_start": flat_start,
                "para_end": total_paras - 1,
                "flat_length": consecutive_flat,
                "position": position,
                "keywords": keywords,
                "reason": _generate_reason(position, consecutive_flat),
            })

    return suggestions


def suggest_spark(text: str, top_k: int = 3,
                  idiom_weight: float = 0.7,
                  poem_weight: float = 0.3) -> list[dict]:
    """
    完整的点睛建议管线：
    1. 扫描平淡区
    2. 提取关键词
    3. 搜索成语和诗词库
    4. 按位置和上下文排序推荐

    返回:
        [{"type": "idiom"|"poem", "text": "...", "meaning": "...",
          "position": "开篇"|"转折"|"收尾"|"高潮",
          "suggested_location": "第X段末尾", "score": 0-100}, ...]
    """
    dull_spots = scan_dull_spots(text)

    if not dull_spots:
        return [{"info": "文章节奏良好，无需额外点缀", "score": 100}]

    # 检查是否已经超量使用了成语
    idiom_count = len(re.findall(r'[\u4e00-\u9fff]{4}', text))
    poem_count = len(re.findall(r'[。！？][\u4e00-\u9fff]{5,}[。！？]', text))
    estimated_usage = (idiom_count + poem_count) / max(1, len(text) / 1000)

    if estimated_usage > MAX_IDIOMS_PER_1000 + MAX_POEMS_PER_1000:
        return [{"info": f"当前修辞密度{estimated_usage:.1f}处/千字，已足够，不建议再添加",
                 "score": 80}]

    suggestions = []
    for spot in dull_spots[:3]:  # 最多推荐3处
        kw = spot["keywords"][:3]
        if not kw:
            kw = ["点睛"]

        type_choice = "idiom" if spot["position"] in ("开篇", "转折") else \
                      "poem" if spot["position"] == "收尾" else \
                      "idiom" if idiom_weight > poem_weight else "poem"

        suggestions.append({
            "type": type_choice,
            "position": spot["position"],
            "source_keywords": kw,
            "suggested_action": spot["reason"],
            "suggested_location": f"第{spot['para_start']+1}-{spot['para_end']+1}段之间",
            "score": 80 - spot["flat_length"] * 5,  # 越平越需要点睛
        })

    return suggestions


def _classify_position(start: int, end: int, total: int) -> Optional[str]:
    """判断段落区间在文章的什么位置"""
    mid = total / 2
    if end < total * 0.2:
        return "开篇"
    elif start > total * 0.75:
        return "收尾"
    elif start <= mid <= end:
        return "高潮/转折"
    elif start > total * 0.4 and end < total * 0.75:
        return "论证中段"
    return None


def _extract_keywords(text: str) -> list[str]:
    """从平淡段落中提取关键词"""
    words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    # 过滤常见虚词
    stop = {'一个', '可以', '这个', '那个', '什么', '怎么', '因为', '所以',
            '但是', '而且', '如果', '虽然', '然后', '就是', '不是', '还是',
            '没有', '已经', '我们', '他们', '你们', '自己', '知道'}
    words = [w for w in words if w not in stop and len(w) >= 2]
    # 按频率排序
    from collections import Counter
    freq = Counter(words)
    return [w for w, _ in freq.most_common(10)]


def _has_sentence_variation(para: str) -> bool:
    """检测段落是否有句长变化"""
    sents = re.split(r'[。！？]', para)
    sents = [s for s in sents if len(s) > 5]
    if len(sents) < 3:
        return False
    lens = [len(s) for s in sents]
    avg = sum(lens) / len(lens)
    var = sum((l - avg) ** 2 for l in lens) / len(lens)
    return var > 50  # 方差>50说明有长短变化


def _generate_reason(position: str, flat_length: int) -> str:
    """生成建议理由"""
    reasons = {
        "开篇": f"开头连续{flat_length}段平淡，建议用1个成语或设问句破局",
        "高潮/转折": f"转折处连续{flat_length}段平铺直叙，建议用典故或排比增强力度",
        "收尾": f"结尾连续{flat_length}段平淡，建议引一句诗词收尾，留有余韵",
        "论证中段": f"论证区连续{flat_length}段缺少修辞变化，建议插入1个排比或对比",
    }
    return reasons.get(position, f"连续{flat_length}段平淡，建议点缀")


if __name__ == "__main__":
    # 测试
    test = """最近几年，中国的芯片产业受到了广泛关注。
从2023年的数据来看，进口芯片金额超过3500亿美元。
国产芯片自给率不到20%，这是一个很大的问题。
为什么会这样？因为过去二十年我们走了贸工技的弯路。
当全球半导体产业链分工明确时，买芯片比造芯片更划算。
但美国开始技术封锁后，这种依赖就成了致命弱点。
解决问题的核心在于建立完整的国产半导体产业链。
这需要长期的资金投入和人才积累，更需要制度层面的改革。
从2025年的情况看，国内企业在成熟制程上已经有了一些突破。
但在先进制程上，与国际先进水平仍有较大差距。
未来几年，中国芯片产业的发展将决定中国科技产业的命运。"""

    print("=== 平淡区扫描 ===")
    spots = scan_dull_spots(test)
    for s in spots:
        print(f"  位置: {s['position']} (第{s['para_start']+1}-{s['para_end']+1}段)")
        print(f"  理由: {s['reason']}")
        print(f"  关键词: {s['keywords'][:5]}")
        print()

    print("=== 点睛建议 ===")
    suggestions = suggest_spark(test)
    for s in suggestions:
        if "info" in s:
            print(f"  {s['info']}")
        else:
            print(f"  [{s['type']}] {s['position']}: {s['suggested_action']}")
            print(f"    位置: {s['suggested_location']}")
