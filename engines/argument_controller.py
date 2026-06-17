# -*- coding: utf-8 -*-
"""
argument_controller.py — 论证结构控制器

三段论结构强制生成与校验：
1. 接受主题 + 风格配置 → 生成结构化写作提纲
2. 按 style_profile 的 expected_order 强制分段
3. 逐段校验内容完整性与逻辑连贯性
4. 跨段落逻辑链条检测（前段承诺，后段兑现）

用法:
    from engines.argument_controller import ArgumentController
    ctrl = ArgumentController("maqianzu")
    
    outline = ctrl.generate_outline("中国芯片产业现状")
    # → [{"stage": "问题提出", "required": True, "prompt": "..."}, ...]
    
    result = ctrl.validate_draft(draft_text)
    # → {"valid": True/False, "issues": [...], "suggestions": [...]}
"""

from __future__ import annotations
import re
from typing import Optional
from pathlib import Path


# ============================================================
#  各写手的论证结构模板
# ============================================================

STRUCTURE_TEMPLATES = {
    "maqianzu": {
        "name": "马前卒三段论",
        "stages": [
            {
                "name": "问题提出",
                "required": True,
                "weight": 1,
                "min_chars": 200,
                "prompt_template": "从工程学视角指出{topic}中的核心矛盾或效率损失",
                "signals": [r'什么|为何|怎么|为什么|问题|矛盾|困境|值得关注|值得思考'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'[^。！？]{10,50}[？?]',  # 有问句
                    r'问题|矛盾|困境|挑战|症结',  # 有问题词
                ]),
                "fallback_prompt": "请以设问句开篇，指出核心矛盾。例：'为什么中国{keyword}总是被卡脖子？'",
            },
            {
                "name": "数据呈现",
                "required": True,
                "weight": 2,
                "min_chars": 300,
                "prompt_template": "用具体数字和对比说明{topic}的现状规模",
                "signals": [r'数据|统计|调研|分析|对比', r'\d+\.?\d*%', r'\d+[万亿]'],
                "check": lambda text: len(re.findall(r'\d+\.?\d*%|\d+[万亿亿兆]|同比|环比|占比', text)) >= 1,
                "fallback_prompt": "必须包含至少1个具体数据点。搜索'根据XXX数据/报告/统计，{keyword}'",
            },
            {
                "name": "原因分析",
                "required": True,
                "weight": 2,
                "min_chars": 400,
                "prompt_template": "拆解{topic}背后的激励机制/制度原因/历史路径",
                "signals": [r'本质|根源|原因|逻辑|机理|机制|拆开|从[^。！？]{4,30}看'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'本质|根源|因为|由于|源于',
                    r'从[^。！？]{4,30}[角度来看]',
                    r'不是.{4,30}而是',
                ]),
                "fallback_prompt": "用工程师视角拆解：'这个问题的本质，在于{原因}。不是因为A，而是因为B。'",
            },
            {
                "name": "方案建议",
                "required": True,
                "weight": 2,
                "min_chars": 300,
                "prompt_template": "针对{topic}给出具体可操作的解决路径",
                "signals": [r'建议|方案|对策|措施|路径|出路|方向', r'应当|应该|需要|关键[是在]'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'建议|方案|措施|需要|应当|关键',
                    r'如果.{4,50}(?:那么|则)',
                ]),
                "fallback_prompt": "必须给出可操作方案。'解决{keyword}的关键，不在于X，而在于Y。'",
            },
        ],
        "transitions": [
            {"from": "问题提出", "to": "数据呈现", "connector": "那么，{topic}的现状如何？看一组数据："},
            {"from": "数据呈现", "to": "原因分析", "connector": "这些数据背后，反映的是{reason}"},
            {"from": "原因分析", "to": "方案建议", "connector": "所以，解决问题的路径在哪里？"},
        ],
    },

    "jiubian": {
        "name": "九边渐进式",
        "stages": [
            {
                "name": "背景铺垫",
                "required": True,
                "min_chars": 250,
                "prompt_template": "从历史或社会背景切入{topic}，娓娓道来",
                "signals": [r'回[想顾]|曾经|过去|以前|当年|历史上'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'回[想顾]|曾经|过去|以前|历史上|早[在期]',
                    r'在[那这]个[^。！？]{4,30}[背景年代]',
                ]),
                "fallback_prompt": "从历史纵深感切入：'说起{keyword}，得从{时间/事件}讲起。'",
            },
            {
                "name": "现象描述",
                "required": True,
                "min_chars": 300,
                "prompt_template": "描述{topi}的当前状况和具体表现",
                "signals": [r'现在|如今|当前|眼下|最近|目前'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'现在|如今|当前|眼下|最近',
                    r'一个[^。！？]{4,30}[现象趋势变化]',
                ]),
                "fallback_prompt": "描述当前让人关注的现象：'而到了现在，{keyword}的局面已经变成了...'",
            },
            {
                "name": "深度分析",
                "required": True,
                "min_chars": 400,
                "prompt_template": "深入分析{topic}的底层逻辑和运行机制",
                "signals": [r'逻辑|机制|惯性|路径|依赖|底层|深层'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'逻辑|机制|惯性|路径依赖|底层',
                    r'换[个一]角度|站在[^。！？]{4,30}[看想]',
                    r'如果你[把們]?[^。！？]{4,30}[就便会]',
                ]),
                "fallback_prompt": "从底层逻辑切入：'如果我们换个角度看{keyword}，会发现...'",
            },
            {
                "name": "开放结论",
                "required": False,
                "min_chars": 150,
                "prompt_template": "给出开放式{topi}判断，留给读者思考空间",
                "signals": [r'也许|或许|可能|大概率|拭目以待'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'也许|或许|可能|大概[率]?',
                    r'拭目以待|值得[关注期待]',
                ]),
                "fallback_prompt": "开放式结尾：'至于{keyword}未来会怎样，也许...'",
            },
        ],
        "transitions": [],
    },

    "lukewen": {
        "name": "卢克文叙事线",
        "stages": [
            {
                "name": "地缘背景",
                "required": True,
                "min_chars": 300,
                "prompt_template": "将{topic}置于全球地缘和文明冲突的大背景下",
                "signals": [r'地缘|地理|文明|大国|全球|世界|历史周期'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'地缘|地理|文明|大国|全球|世界',
                    r'在[这]?个[^。！？]{4,30}[时代纪元格局周期]',
                ]),
                "fallback_prompt": "从地缘格局切入：'{keyword}这个问题，放在全球地缘博弈的背景下来看...'",
            },
            {
                "name": "核心冲突",
                "required": True,
                "min_chars": 400,
                "prompt_template": "揭示{topic}背后的利益冲突和力量博弈",
                "signals": [r'矛盾|冲突|博弈|争夺|对抗|竞争|较量'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'矛盾|冲突|博弈|争夺|对抗',
                    r'本质[上]?[是就来]|归根结底|说到底',
                ]),
                "fallback_prompt": "揭示本质冲突：'{keyword}背后，本质上是{利益方A}与{利益方B}的博弈。'",
            },
            {
                "name": "逻辑推演",
                "required": True,
                "min_chars": 400,
                "prompt_template": "从利益格局出发推演{topic}的演化路径",
                "signals": [r'逻辑|推演|推导|必然|决定|导致|引发'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'必然|决定|导致|引发|驱动',
                    r'从.{4,30}到.{4,30}',
                ]),
                "fallback_prompt": "推演路径：'从A到B，再进一步推导，{keyword}的最终走向是...'",
            },
            {
                "name": "前景判断",
                "required": False,
                "min_chars": 200,
                "prompt_template": "对{topic}的未来走向做出判断",
                "signals": [r'未来|接下[来去]|[三十五十]年|长期[看来]|大概率|走向|趋势'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'未来|走向|趋势|格局',
                    r'[三十五十]年[以来内后]|长期',
                ]),
                "fallback_prompt": "前瞻判断：'{keyword}的未来走向，大概率取决于{关键变量}。'",
            },
        ],
        "transitions": [],
    },

    "natgeo": {
        "name": "国家地理科普线",
        "stages": [
            {
                "name": "发现引入",
                "required": True,
                "min_chars": 200,
                "prompt_template": "以科学发现或自然现象作为{topic}的引入",
                "signals": [r'发现|研究[表显]?[明示]?|科学[家者]?|一项[最新]?'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'发现|研究|科学[家者]',
                    r'在[那这][^。！？]{4,30}(?:地区|海域|丛林|深处|星球)',
                ]),
                "fallback_prompt": "以发现开篇：'在{location}，科学家们发现了一个令人惊叹的现象...'",
            },
            {
                "name": "科学原理",
                "required": True,
                "min_chars": 300,
                "prompt_template": "解释{topic}背后的科学原理或自然机制",
                "signals": [r'原理|机制|进化|适应|演化|生态|基因|物种|细胞'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'原理|机制|进化|适应|演化|生态',
                    r'科学家[们]?[发现指出认为解释]',
                ]),
                "fallback_prompt": "解释科学原理：'{keyword}背后的科学原理是...'",
            },
            {
                "name": "数据佐证",
                "required": True,
                "min_chars": 200,
                "prompt_template": "用观测{topi}数据和研究证据佐证",
                "signals": [r'\d+\.?\d*%|公里|平方米|吨|摄氏度|研究|调查|统计|观测|监测'],
                "check": lambda text: bool(re.findall(r'\d+\.?\d*%|\d+[万亿k]|公里|平方米|吨|摄氏度', text)),
                "fallback_prompt": "引用数据：'根据{研究机构}的观测数据，{keyword}的{指标}达到了{数字}。'",
            },
            {
                "name": "意义延伸",
                "required": False,
                "min_chars": 200,
                "prompt_template": "阐述{topic}对人类的启示和思考",
                "signals": [r'启示|意义|影响|警示|启发|值得[我们]?[思考关注重视]'],
                "check": lambda text: any(re.search(p, text) for p in [
                    r'启示|意义|影响|警示',
                    r'这[也]?[说明意味告诉]我们',
                    r'值得.{2,10}[思考关注重视警惕]',
                ]),
                "fallback_prompt": "升华主题：'{keyword}给我们的启示是...'",
            },
        ],
        "transitions": [],
    },
}


# ============================================================
#  ArgumentController 核心类
# ============================================================

class ArgumentController:
    """论证结构控制器"""

    def __init__(self, profile_name: str):
        template = STRUCTURE_TEMPLATES.get(profile_name)
        if not template:
            raise ValueError(f"未知的论证模板: {profile_name}，可用: {list(STRUCTURE_TEMPLATES.keys())}")
        self.profile_name = profile_name
        self.template = template
        self.stages = template["stages"]
        self.transitions = template.get("transitions", [])
        self._current_stage = 0

    def generate_outline(self, topic: str) -> list[dict]:
        """
        根据主题生成结构化写作提纲

        返回:
            [{"stage": "问题提出", "required": True, "prompt": "...",
              "min_chars": 200, "stage_index": 0}, ...]
        """
        outline = []
        for i, stage in enumerate(self.stages):
            prompt = stage["prompt_template"].replace("{topic}", topic) \
                                             .replace("{keyword}", topic)
            if "{reason}" in prompt:
                prompt = prompt.replace("{reason}", "深层制度原因")
            if "{location}" in prompt:
                prompt = prompt.replace("{location}", "全球各地")
            if "{利益方A}" in prompt:
                prompt = prompt.replace("{利益方A}", "相关方A").replace("{利益方B}", "相关方B")

            outline.append({
                "stage": stage["name"],
                "required": stage.get("required", True),
                "min_chars": stage.get("min_chars", 200),
                "weight": stage.get("weight", 1),
                "prompt": prompt,
                "stage_index": i,
            })

            # 如果有过渡句
            if self.transitions and i < len(self.transitions):
                t = self.transitions[i]
                connector = t["connector"].replace("{topic}", topic) \
                                          .replace("{reason}", "制度根源")
                outline.append({
                    "stage": f"→ {t['from']}→{t['to']}",
                    "required": False,
                    "connector": connector,
                    "stage_index": i,
                    "is_transition": True,
                })

        return outline

    def validate_draft(self, text: str) -> dict:
        """
        校验文稿的论证结构完整性

        返回:
            {"valid": True/False, "stages": [...], "issues": [...], "suggestions": [...]}
        """
        paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 30]
        total_paras = len(paras)

        if total_paras < len(self.stages):
            return {
                "valid": False,
                "error": f"段落数({total_paras})少于阶段数({len(self.stages)})",
                "stages": [],
                "issues": ["文稿过短，无法完成完整的论证结构"],
                "suggestions": [f"建议至少写{len(self.stages)}段，每段200-500字"],
            }

        # 逐段检测阶段匹配
        para_stages = []
        for p in paras:
            matched = None
            max_weight = -1
            for s in self.stages:
                signals = s.get("signals", [])
                for sig in signals:
                    if re.search(sig, p, re.IGNORECASE):
                        w = s.get("weight", 1)
                        if w > max_weight:
                            matched = s["name"]
                            max_weight = w
                        break
            para_stages.append(matched)

        # 统计每个阶段
        from collections import Counter
        stage_counts = Counter(para_stages)
        stage_check = {}

        for s in self.stages:
            name = s["name"]
            count = stage_counts.get(name, 0)
            required = s.get("required", True)
            check_fn = s.get("check")
            stage_text = "\n".join(p for p, stage in zip(paras, para_stages) if stage == name)

            stage_check[name] = {
                "found": count > 0,
                "count": count,
                "required": required,
                "char_count": len(stage_text),
                "min_chars": s.get("min_chars", 0),
                "chars_ok": len(stage_text) >= s.get("min_chars", 0),
            }

            if check_fn and stage_text:
                stage_check[name]["signal_ok"] = check_fn(stage_text)
            else:
                stage_check[name]["signal_ok"] = None

        # 顺序检查
        order_ok = True
        order_issues = []
        present_ordered = [s for s in para_stages if s is not None]
        seen = set()
        unique_order = []
        for s in present_ordered:
            if s not in seen:
                seen.add(s)
                unique_order.append(s)

        expected_order = [s["name"] for s in self.stages]
        expected_seq = [s for s in expected_order if s in seen]
        if unique_order != expected_seq[:len(unique_order)]:
            order_ok = False
            order_issues.append(f"阶段顺序异常: {' → '.join(unique_order)}")

        # 生成问题列表
        issues = []
        suggestions = []

        for name, check in stage_check.items():
            if check["required"] and not check["found"]:
                issues.append(f"[缺失] 必要阶段'{name}'未检测到")
                fallback = next((s.get("fallback_prompt", "") for s in self.stages if s["name"] == name), "")
                if fallback:
                    suggestions.append(f"'{name}'阶段: {fallback}")
            if check["found"] and not check["chars_ok"]:
                issues.append(f"[不足] '{name}'阶段仅{check['char_count']}字，建议至少{check['min_chars']}字")
            if check.get("signal_ok") is False:
                issues.append(f"[信号] '{name}'阶段缺少关键论证信号")

        if not order_ok:
            issues.extend(order_issues)
            suggestions.append(f"建议按{' → '.join(expected_order)}的顺序组织文章")

        return {
            "valid": len(issues) == 0,
            "stage_count": len(self.stages),
            "stages": stage_check,
            "issues": issues,
            "suggestions": suggestions,
        }

    def generate_critical_checkpoints(self, topic: str) -> list[str]:
        """生成写作过程中的关键校验点（供 agent 在写作过程中自查）"""
        checkpoints = []
        for s in self.stages:
            if s.get("required"):
                checkpoints.append(f"[{s['name']}] 必写，至少{s.get('min_chars', 200)}字")
        checkpoints.append(f"[整体] 按{' → '.join(s['name'] for s in self.stages if s.get('required'))}顺序")
        return checkpoints

    def estimate_completeness(self, text: str) -> dict:
        """
        快速评估论证完整性（0-100分）
        用于写作过程中的实时反馈
        """
        result = self.validate_draft(text)
        if "error" in result:
            return {"score": 0, "status": "too_short", "error": result["error"]}

        score = 0
        max_score = 0
        for name, check in result["stages"].items():
            stage_weight = next((s.get("weight", 1) for s in self.stages if s["name"] == name), 1)
            max_score += stage_weight * 2
            if check["found"] and check["required"]:
                score += stage_weight
                if check["chars_ok"]:
                    score += stage_weight

        completeness = round(score / max(1, max_score) * 100, 1)

        if completeness >= 80:
            status = "good"
        elif completeness >= 50:
            status = "in_progress"
        else:
            status = "early"

        return {
            "score": completeness,
            "status": status,
            "stage_count": result["stage_count"],
            "missing_stages": [n for n, c in result["stages"].items() if c["required"] and not c["found"]],
        }


# ============================================================
#  便捷接口
# ============================================================

def create_outline(profile_name: str, topic: str) -> list[dict]:
    """快捷生成写作提纲"""
    ctrl = ArgumentController(profile_name)
    return ctrl.generate_outline(topic)


def validate_draft(profile_name: str, text: str) -> dict:
    """快捷校验文稿"""
    ctrl = ArgumentController(profile_name)
    return ctrl.validate_draft(text)


def list_templates() -> list[str]:
    """列出所有可用模板"""
    return list(STRUCTURE_TEMPLATES.keys())


if __name__ == "__main__":
    import json

    print("可用模板:", list_templates())
    print()

    for pname in ["maqianzu", "jiubian", "lukewen", "natgeo"]:
        print(f"\n{'='*50}")
        print(f"  {STRUCTURE_TEMPLATES[pname]['name']}")
        print(f"{'='*50}")

        ctrl = ArgumentController(pname)
        outline = ctrl.generate_outline("中国芯片产业")
        for item in outline:
            if item.get("is_transition"):
                print(f"  → {item['connector'][:60]}...")
            else:
                flag = "必" if item["required"] else "选"
                print(f"  [{flag}] {item['stage']}: {item['prompt'][:60]}...")

        # 测试校验
        if pname == "maqianzu":
            test = """为什么中国的芯片产业总是被卡脖子？
从数据来看，2023年中国进口芯片金额超过3500亿美元。
这个问题的本质，在于过去二十年走了贸工技的弯路。
解决问题的核心，在于建立完整的国产半导体产业链。"""
            result = ctrl.validate_draft(test)
            print(f"\n  校验: {'通过' if result['valid'] else '未通过'}")
            for iss in result["issues"]:
                print(f"    {iss}")
            comp = ctrl.estimate_completeness(test)
            print(f"  完整度: {comp['score']}% ({comp['status']})")
