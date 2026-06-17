# -*- coding: utf-8 -*-
"""
style_profile_engine.py — 风格规则引擎

基于衍梦文枢 Monte Carlo Temperature + PowerLaw Breathing 思想
为每个写手提供确定性风格控制：

1. 论证结构模板     — 马前卒三段论 / 九边渐进式 / 卢克文叙事线
2. 句式频率控制     — 设问/反问/排比的使用比例
3. 数据密度要求     — 最小数据引用条数
4. 禁忌清单         — 禁止使用的句式/词汇
5. 向量库注入       — 自动检索 idioms/poem_sentences 作为文采素材

用法:
    from engines.style_profile_engine import StyleProfile, load_profile
    
    profile = load_profile("maqianzu")
    profile.validate_structure("...")  → {"valid": True, "suggestions": [...]}
    profile.suggest_data_points(...)    → ["需要补充数据", ...]
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional


# ============================================================
#  风格配置文件定义
# ============================================================

class StyleProfile:
    """风格规则配置"""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.cn_name = config.get("cn_name", name)
        self.structure = config.get("structure", {})
        self.sentence_patterns = config.get("sentence_patterns", {})
        self.data_requirements = config.get("data_requirements", {})
        self.forbidden = config.get("forbidden", [])
        self.vector_db_refs = config.get("vector_db_refs", [])
        self.description = config.get("description", "")

    def validate_structure(self, text: str) -> dict:
        """校验文本是否满足该写手的论证结构要求"""
        struct_type = self.structure.get("type", "free")
        stages = self.structure.get("stages", [])
        expected_order = self.structure.get("expected_order", [])

        if struct_type == "free":
            return {"valid": True, "struct_type": "free", "suggestions": []}

        # 检测每段所属阶段
        paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 30]
        if not paras:
            return {"valid": False, "error": "empty_text"}

        para_stages = []
        for p in paras:
            matched = None
            for stage_name, stage_config in stages.items():
                signals = stage_config.get("signals", [])
                for sig in signals:
                    if re.search(sig, p):
                        matched = stage_name
                        break
                if matched:
                    break
            para_stages.append(matched)

        # 检查覆盖度
        present = set(s for s in para_stages if s is not None)
        missing = [s for s in expected_order if s not in present]
        order_ok = True

        # 顺序检查（如果定义了期望顺序）
        if expected_order and present:
            present_ordered = [s for s in para_stages if s is not None]
            # 去重保留顺序
            seen = set()
            unique_order = []
            for s in present_ordered:
                if s not in seen:
                    seen.add(s)
                    unique_order.append(s)
            # 检查子序列
            expected_seq = [s for s in expected_order if s in present]
            order_ok = unique_order == expected_seq[:len(unique_order)]

        suggestions = []
        if missing:
            suggestions.append(f"缺少阶段: {'/'.join(missing)}")
        if not order_ok:
            suggestions.append("阶段顺序异常，建议按 {0} 排列".format(' → '.join(expected_order)))

        return {
            "valid": len(missing) == 0 and order_ok,
            "present_stages": list(present),
            "missing_stages": missing,
            "order_ok": order_ok,
            "struct_type": struct_type,
            "suggestions": suggestions
        }

    def check_forbidden(self, text: str) -> list[str]:
        """检查文本中是否包含禁忌内容"""
        violations = []
        for rule in self.forbidden:
            pattern = rule.get("pattern", "")
            if not pattern:
                continue
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                violations.append({
                    "rule": rule.get("name", "未命名"),
                    "pattern": pattern,
                    "matches": matches[:5],
                    "suggestion": rule.get("suggestion", "")
                })
        return violations

    def check_data_density(self, text: str) -> dict:
        """检查数据密度是否达标"""
        min_count = self.data_requirements.get("min_data_points", 0)
        preferred_min = self.data_requirements.get("preferred_min", min_count)

        # 数据模式
        data_patterns = [
            r'\d+\.?\d*%',
            r'(?:\d{1,3}(?:,\d{3})*|\d+\.?\d*)(?:万|亿|美元|元|人|个|辆|吨|公里)',
            r'\d+倍|比[例率]|占比|率[达超]',
            r'超过|不足|仅仅|高达|低至|同比|环比',
        ]
        total = sum(len(re.findall(pat, text)) for pat in data_patterns)

        return {
            "count": total,
            "min_required": min_count,
            "preferred_min": preferred_min,
            "met": total >= min_count,
            "gap": max(0, preferred_min - total)
        }

    def suggest_vector_search(self, topic: str) -> list[str]:
        """根据主题建议搜索哪些向量库"""
        suggestions = []
        for ref in self.vector_db_refs:
            db_name = ref.get("db", "")
            query_prefix = ref.get("query_prefix", "")
            suggestions.append(f"{db_name}: {query_prefix}{topic}")
        return suggestions

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cn_name": self.cn_name,
            "description": self.description,
            "structure_type": self.structure.get("type", "free"),
            "data_min": self.data_requirements.get("min_data_points", 0),
            "forbidden_rules": len(self.forbidden),
        }


# ============================================================
#  写手配置文件
# ============================================================

PROFILES = {
    "maqianzu": {
        "cn_name": "马前卒",
        "description": "工程师视角拆解社会问题，数据驱动，发现问题必提方案",
        "structure": {
            "type": "stage_sequential",
            "stages": {
                "问题提出": {
                    "signals": [
                        r'什么|为何|怎么|如何|为什么|问题|矛盾|困境|值得关注',
                    ]
                },
                "数据呈现": {
                    "signals": [
                        r'数据|统计|调研|研究|分析|对比|案例|样本|趋势',
                        r'\d+\.?\d*%|\d+[万亿]|同比|环比',
                    ]
                },
                "原因分析": {
                    "signals": [
                        r'本质|根源|原因|逻辑|机理|机制|规律',
                        r'拆开[来看]?|从[^。！？]{4,30}看',
                    ]
                },
                "方案建议": {
                    "signals": [
                        r'建议|方案|对策|措施|路径|出路|方向|目标',
                        r'应当|应该|需要|必须|如果.{4,50}(?:那么|则|就)',
                    ]
                },
            },
            "expected_order": ["问题提出", "数据呈现", "原因分析", "方案建议"],
        },
        "sentence_patterns": {
            "recommended": {
                "设问推进": r'为什么.{5,50}[？?]',
                "数据前置": r'[第有从]?\d+\.?\d*[%万亿]',
                "对比反差": r'(?:很多人|传统|过去)[^。！？]{4,30}但[^。！？]{4,30}',
            },
            "ratio_limits": {
                "反问句比例": ["<=", 0.05],
                "设问句比例": [">=", 0.08],
            }
        },
        "data_requirements": {
            "min_data_points": 3,
            "preferred_min": 5,
            "density_per_1000": 2.0,
        },
        "forbidden": [
            {"name": "情绪化感叹", "pattern": r'震惊|愤怒|令人发指|天理难容|岂有此理',
             "suggestion": "用数据说话，避免情绪化表达"},
            {"name": "空洞口号", "pattern": r'必须加强|高度重视|切实落实|大力推进',
             "suggestion": "替换为具体措施+责任人+时间表"},
            {"name": "神秘主义", "pattern": r'背后[必定]?有[深不]?[可意]?[告测]?|不可告人',
             "suggestion": "分析可见因素，避免暗示阴谋论"},
        ],
        "vector_db_refs": [
            {"db": "literary_ref/idioms", "query_prefix": "关于"},
            {"db": "maqianzu_chroma", "query_prefix": ""},
        ]
    },

    "jiubian": {
        "cn_name": "九边",
        "description": "长线社会观察，历史纵深感，娓娓道来",
        "structure": {
            "type": "stage_sequential",
            "stages": {
                "背景铺垫": {
                    "signals": [
                        r'回[想顾]|[早过]些年|曾经|过去|以前|当年|历史上',
                        r'众所[周同]知|一般来[说说讲]',
                    ]
                },
                "现象描述": {
                    "signals": [
                        r'现在|如今|当前|眼下|最近的|这两年|目前|观察',
                        r'让人[感到觉得]|一个[有趣值得][的]?现象',
                    ]
                },
                "深度分析": {
                    "signals": [
                        r'逻辑|链条|链条|机制|惯性|路径|依赖|底层|深层',
                        r'如果[你]?[把们]?|换[个一]角度|站在',
                    ]
                },
                "开放结论": {
                    "signals": [
                        r'也许|或许|可能|大概率|小概率|拭目以待|值得[跟进期待关注]',
                    ]
                },
            },
            "expected_order": ["背景铺垫", "现象描述", "深度分析", "开放结论"],
        },
        "sentence_patterns": {
            "recommended": {
                "历史类比": r'从[^。！？]{4,30}到[^。！？]{4,30}',
                "背景介绍": r'在[那这]个[^。！？]{4,30}[背景环境年代周期时期]',
                "条件假设": r'如果[没有]?[^。！？]{4,40}(?:那么|则|就)',
            },
        },
        "data_requirements": {
            "min_data_points": 2,
            "preferred_min": 4,
        },
        "forbidden": [
            {"name": "结论绝对化", "pattern": r'一定[会是]|绝对|必然|毫无疑问|毋庸置疑',
             "suggestion": "九边风格偏开放式结论，避免绝对化表述"},
            {"name": "过度情绪", "pattern": r'泪目|破防|哭了|扎心|太[好难棒]了',
             "suggestion": "保持理性温和，让读者自己感受"},
        ],
        "vector_db_refs": [
            {"db": "literary_ref/idioms", "query_prefix": "关于"},
            {"db": "literary_ref/poem_sentences", "query_prefix": ""},
        ]
    },

    "lukewen": {
        "cn_name": "卢克文",
        "description": "宏大叙事，地缘政治，文明竞争视角",
        "structure": {
            "type": "stage_sequential",
            "stages": {
                "地缘背景": {
                    "signals": [
                        r'地缘|地理|文明|大国|全球|世界|历史周期',
                        r'在[这]?个[^。！？]{4,30}[时代纪元背景格局]',
                    ]
                },
                "核心冲突": {
                    "signals": [
                        r'矛盾|冲突|博弈|争夺|对抗|竞争|较量|角力',
                        r'本质[上]?[是就来]|归根结底|说到底',
                    ]
                },
                "逻辑推演": {
                    "signals": [
                        r'逻辑[上链]?|推演|推导|必然|决定[了]?|导致|引发',
                        r'从[一个].[^。！？]{4,40}到[另一个].[^。！？]{4,40}',
                    ]
                },
                "前景判断": {
                    "signals": [
                        r'未来的|[接下]?[来去]的|[三十五十]年|长期[看来]',
                        r'大概率|走向|趋势[是]?|方向[是]?|格局[将]?',
                    ]
                },
            },
            "expected_order": ["地缘背景", "核心冲突", "逻辑推演", "前景判断"],
        },
        "sentence_patterns": {
            "recommended": {
                "历史对照": r'想起|回顾|对比[于]?|参照|回溯',
                "叙事张力": r'但[是]?[^。！？]{3,30}关键[在是]|然而|不过',
                "宏大对比": r'一边[是]?.{4,30}一边[是]?.{4,30}',
            },
        },
        "data_requirements": {
            "min_data_points": 1,
            "preferred_min": 3,
        },
        "forbidden": [
            {"name": "局部细节过度", "pattern": r'具体[到]?[每某][个一]|[技术细节操作层面]',
             "suggestion": "卢克文风格重宏大叙事，避免微观技术细节"},
            {"name": "情绪化价值判断", "pattern": r'邪恶|正义[的]?[必将]?|万恶|绝对正确',
             "suggestion": "从利益和格局角度分析，避免道德评价"},
        ],
        "vector_db_refs": [
            {"db": "literary_ref/poem_sentences", "query_prefix": ""},
        ]
    },

    "natgeo": {
        "cn_name": "国家地理(科普)",
        "description": "科学叙事，发现视角，数据可视化思维",
        "structure": {
            "type": "stage_sequential",
            "stages": {
                "发现引入": {
                    "signals": [
                        r'发现|研究[表显]?[明示]?|科学[家者]?|一项[最新]?',
                        r'在[那这].[^。！？]{4,30}(?:地区|海域|丛林|深处)',
                    ]
                },
                "科学原理": {
                    "signals": [
                        r'原理|机制|进化|适应|演化|生态|基因|物种|细胞',
                        r'科学家[们]?[发现指出认为]',
                    ]
                },
                "数据佐证": {
                    "signals": [
                        r'\d+\.?\d*%|\d+[万亿]|公里|平方米|吨|摄氏度',
                        r'研究[数据结果]|调查|统计|观测|监测',
                    ]
                },
                "意义延伸": {
                    "signals": [
                        r'启示|意义|影响|警示|启发|值得[我们]?[思考关注重视]',
                        r'这[也]?[说明意味告诉]我们',
                    ]
                },
            },
            "expected_order": ["发现引入", "科学原理", "数据佐证", "意义延伸"],
        },
        "data_requirements": {
            "min_data_points": 2,
            "preferred_min": 4,
        },
        "forbidden": [
            {"name": "拟人化过度", "pattern": r'大[自然地]母亲|地球妈妈|[动植]物[也]?[会想感觉]',
             "suggestion": "保持科学叙事风格，避免过度拟人化"},
            {"name": "伪科学表述", "pattern": r'能量[场圈]|磁[场力]疗|灵性|开悟',
             "suggestion": "只引用经同行评议的科学结论"},
        ],
        "vector_db_refs": [
            {"db": "literary_ref/poem_sentences", "query_prefix": ""},
        ]
    },
}


# ============================================================
#  加载与便捷接口
# ============================================================

def load_profile(name: str) -> Optional[StyleProfile]:
    """加载指定写手的风格规则配置"""
    config = PROFILES.get(name)
    if not config:
        return None
    return StyleProfile(name, config)


def list_profiles() -> list[dict]:
    """列出所有可用的风格配置"""
    return [
        {"name": name, "cn_name": cfg["cn_name"], "desc": cfg["description"]}
        for name, cfg in PROFILES.items()
    ]


def validate_against_profile(text: str, profile_name: str) -> dict:
    """对文本执行一次完整的风格校验"""
    profile = load_profile(profile_name)
    if not profile:
        return {"error": f"未知风格: {profile_name}"}

    result = {
        "profile": profile_name,
        "profile_cn": profile.cn_name,
        "structure": profile.validate_structure(text),
        "forbidden": profile.check_forbidden(text),
        "data_density": profile.check_data_density(text),
    }

    # 综合评分
    issues = []
    if not result["structure"]["valid"]:
        issues.extend(result["structure"]["suggestions"])
    if result["forbidden"]:
        for v in result["forbidden"]:
            issues.append(f"[违禁] {v['rule']}: {v['matches'][0] if v['matches'] else ''}")
    if not result["data_density"]["met"]:
        issues.append(f"[数据不足] 引用{result['data_density']['count']}条，建议至少{result['data_density']['preferred_min']}条")

    result["issues"] = issues
    result["pass"] = len(issues) == 0
    return result


if __name__ == "__main__":
    import sys, json
    profiles = list_profiles()
    print(f"可用风格配置 ({len(profiles)}):")
    for p in profiles:
        print(f"  {p['name']} ({p['cn_name']}): {p['desc']}")
    print()

    # 测试马前卒
    if len(sys.argv) > 1:
        text = open(sys.argv[1], 'r', encoding='utf-8').read()
        result = validate_against_profile(text, "maqianzu")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        test = """为什么中国的芯片产业总是被"卡脖子"？
从数据来看，2023年中国进口芯片金额超过3500亿美元，是全球最大的芯片消费市场。
但国产芯片自给率只有不到20%，高端芯片几乎完全依赖进口。
这个问题的本质，在于过去二十年我们走了"贸工技"的弯路。
当全球半导体产业链分工明确时，买芯片比造芯片更划算。
但当美国开始技术封锁时，这种依赖就成了致命弱点。
解决问题的核心是什么？关键不在于短期内造出3nm芯片，
而在于建立完整的国产半导体产业链，哪怕从成熟制程开始。
这需要长期的资金投入和人才积累，更需要制度层面的改革。"""
        result = validate_against_profile(test, "maqianzu")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
