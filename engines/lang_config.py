# -*- coding: utf-8 -*-
"""
lang_config.py — 多语言模式配置

集中管理所有引擎的语言相关模式。
新增语言只需在此文件添加对应集合。

用法:
    from engines.lang_config import detect_lang, get_patterns
    patterns = get_patterns("edge_detector", lang="en")
"""

from __future__ import annotations
import re
from typing import Literal

Lang = Literal["zh", "en", "ja"]


# ============================================================
#  语言检测
# ============================================================

def detect_lang(text: str) -> Lang:
    """
    自动检测文本语言
    抽样前 200 字符：
    - 含平假名/片假名 → ja
    - 中文字符占比 > 10% → zh
    - 否则 → en
    """
    sample = text[:200]
    hira_kata = sum(1 for c in sample if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
    if hira_kata >= 2:
        return "ja"
    cn_chars = sum(1 for c in sample if '\u4e00' <= c <= '\u9fff')
    return "zh" if cn_chars > len(sample) * 0.1 else "en"


# ============================================================
#  句子分割
# ============================================================

SENTENCE_SPLIT = {
    "zh": r'(?<=[。！？；\n])',
    "en": r'(?<=[.!?;\n])',
    "ja": r'(?<=[。！？\n])',
}


# ============================================================
#  edge_detector_essay 模式
# ============================================================

EDGE_DETECTOR = {
    # = 句法分割 =
    "sentence_split": {
        "zh": r'[。！？\n；]',
        "en": r'[.!?\n;]',
        "ja": r'[。！？\n]',
    },

    # = 金句模式 =
    "golden_patterns": {
        "zh": [
            r'(?:不是|并非|绝不是)[^。！？;；]{4,30}(?:而是|乃是|而是说)[^。！？;；]{4,30}',
            r'(?:为什么|何以|为何|凭什么|怎么[会能]).{5,50}[？?].{5,80}[。！]',
            r'(?:无论|不管|不论).{3,20}(?:还是|或是).{3,20}(?:都|均|总)',
            r'(?:越|愈)[^。！？，；]{3,20}(?:越|愈)[^。！？，；]{3,20}',
            r'(?:从|在|当|让|把|将|用|以)[^。！？，；]{5,25}(?:，|;)[^。！？，；]{5,25}(?:，|;)[^。！？，；]{5,25}',
            r'(?:所谓|正(如|是)|可(谓|见)|不难看[出到]|归根结底|本(质|源)[上]?|从来[没有]|真正[的])',
            r'(?:不只|不仅|不但|非但).{3,25}(?:而且|还|更|也|亦|同样|甚至).{3,25}(?:更|甚至|乃至|况且)',
            r'决定[性]?的[^。！？]{2,20}不在于[^。！？]{2,20}',
        ],
        "en": [
            r'(?:It is not|This is not|That is not)[^.!?;]{4,40}(?:but rather|but|but instead)[^.!?;]{4,40}',
            r'(?:Why|How|What|Where)[^.!?;]{5,50}[?][^.!?;]{5,80}[.]',
            r'(?:Whether|No matter|Regardless of)[^.!?;]{3,30}(?:or)[^.!?;]{3,30}(?:,|;)[^.!?;]{3,30}',
            r'(?:The more|The less|The harder)[^.!?;]{3,30}(?:the more|the less|the harder)[^.!?;]{3,30}',
            r'(?:From|In|At|By|With|Through)[^.!?;]{5,25}(?:,|;)[^.!?;]{5,25}(?:,|;)[^.!?;]{5,25}',
            r'(?:In other words|That is to say|What this means is|At its core|Fundamentally|Ultimately)',
            r'(?:Not only|Not just|Not merely)[^.!?;]{3,30}(?:but also|but|yet|still)[^.!?;]{3,30}',
        ],
        "ja": [
            r'(?:なぜ|どうして|何故)[^。！？]{5,50}[？?][^。！？]{5,80}[。！]',
            r'(?:ただの|単なる|単に)[^。！？]{4,30}(?:ではなく|ではなくて|じゃなく)[^。！？]{4,30}',
            r'(?:もし|仮に|万が一)[^。！？]{5,50}(?:ならば|たら|れば|と)',
            r'(?:〜ば〜ほど|すればするほど|になればなるほど)',
            r'(?:言い換えれば|つまり|すなわち|要するに|結論として|本質的に)',
            r'(?:だけでなく|のみならず|ばかりか)[^。！？]{3,25}(?:もまた|さらに|加えて|その上)',
        ],
    },

    # = 数据模式 =
    "data_patterns": {
        "zh": {
            "percentage": r'\d+\.?\d*%',
            "number": r'(?:^|[\s，。；、：])'
                      r'(\d{1,3}(?:,\d{3})*|\d+\.?\d*)'
                      r'(?:万|亿|美元|元|人|家|个|辆|吨|公里|平方米|亿人|亿次|年|月|日)',
            "ratio": r'[一二两三四五六七八九十]分之[一二两三四五六七八九十]'
                     r'|\.\d+倍|\d+倍|比[例率]|占比|率[达超]',
            "comparison": r'超过|不足|仅仅|高达|低至|同比|环比|年均|累计|达到|突破',
        },
        "en": {
            "percentage": r'\d+\.?\d*%',
            "number": r'(?:\$|€|£)?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:million|billion|trillion|%|USD|EUR)?',
            "ratio": r'(?:ratio|rate|proportion|share|margin)[^.]{0,30}\d+\.?\d*',
            "comparison": r'(?:increase|decrease|rise|fall|grow|decline|surge|plunge)[^.]{0,20}\d+',
        },
    },

    # = AI安全词 =
    "ai_safe_words": {
        "zh": {
            "空洞表态": [
                r'值得[我深]?[们思]?[深思关注思考警惕注意重视肯定称道]',
                r'具有[极其]?[重要深远重大特殊][意(?:义|思)][深远]?',
                r'不[可容]?[忽视忽略小觑低估]',
            ],
            "万能结论": [
                r'路[还]?[很长仍然漫长尚远]',
                r'任[重务]?[而道远艰巨]',
                r'有待[进一步深入持续]?(?:观察|研究|完善|改进|加强)',
            ],
            "模糊递进": [
                r'不[仅仅光但]?[是如止]此',
                r'更[为重关键的]?[重要关键核心的是]',
                r'从[某种根本宏观的]?[意义角度层面][上来说看讲]',
            ],
            "空泛评价": [
                r'[开启谱写书写迎来迈入开创]了[新的崭新全新时代篇章征程局面]',
                r'[有力显著切实充分]地[推动促进提升增强推进加强]',
            ],
        },
        "en": {
            "empty_platitudes": [
                r'(?:It is|This is)\s+(?:worth\s+noting|important\s+to\s+note|worth\s+considering)',
                r'(?:cannot|cannot)\s+be\s+(?:overstated|overemphasized|ignored|overlooked)',
                r'(?:of\s+great|of\s+paramount|of\s+utmost)\s+(?:importance|significance|concern)',
            ],
            "vague_conclusions": [
                r'(?:remains\s+to\s+be\s+seen|remains\s+uncertain|time\s+will\s+tell)',
                r'(?:warrants|merits|deserves)\s+(?:further|more|continued)\s+(?:research|study|investigation|exploration)',
                r'(?:a\s+long\s+way\s+to\s+go|much\s+work\s+remains|challenges\s+lie\s+ahead)',
            ],
            "vague_hedging": [
                r'(?:to\s+a\s+certain\s+extent|in\s+a\s+sense|in\s+many\s+ways|to\s+some\s+degree)',
                r'(?:it\s+could\s+be\s+argued|one\s+could\s+say|it\s+might\s+be)',
            ],
            "hollow_praise": [
                r'(?:usher\s+in|mark\s+|herald\s+|signal\s+|pave\s+the\s+way\s+for)\s+(?:a\s+new|new\s+era|new\s+chapter|groundbreaking)',
                r'(?:significantly|substantially|meaningfully)\s+(?:enhance|improve|strengthen|advance)',
            ],
        },
        "ja": {
            "空疎な決意": [
                r'考慮[するする]?必要[があるとなる]',
                r'重要な[意義意味役割]を[持つ果たす担う]',
                r'無視[できな?い?|してはならない]',
                r'注目[すべき?|に値する]',
            ],
            "曖昧な結論": [
                r'さらなる[研究検討考察分析]が[必要求められる]',
                r'今後の[課題と[なる?する?]|展望が[期待される?]]',
                r'長い目で[見る見守る]必要がある',
            ],
            "婉曲な表現": [
                r'ある[意味程度]では',
                r'[考えられ?]なくはない|言えなくもない',
                r'一概に[は]?[言えな?い?|否定できな?い?]',
            ],
            "空虚な評価": [
                r'[新た新しい]な[時代局面ステージ]を[迎える切り開く築く]',
                r'[大きく顕著に著しく]?[向上改善進展促進]',
                r'[高く大きく]?[評価期待]される',
            ],
        },
    },

    # = 修辞模式 =
    "rhetoric_patterns": {
        "zh": [
            r'不(仅|但|光|只)[^。！？]{3,25}(?:而且|还|更|也|亦)',
            r'不是[^。！？]{3,25}而是[^。！？]{3,25}',
            r'难道|岂非|何尝|怎能|如何能',
            r'越[^。！？，；]{2,15}越[^。！？，；]{2,15}',
            r'无论|不管|不论.{3,20}(?:还是|或是).{3,20}(?:都|均|总)',
            r'一[边面方][^。！？，；]{2,15}一[边面方][^。！？，；]{2,15}',
            r'从[^。！？，；]{3,20}到[^。！？，；]{3,20}',
            r'既[^。！？，；]{2,15}又[^。！？，；]{2,15}',
        ],
        "en": [
            r'(?:not only|not just|not merely)[^.!?;]{3,25}(?:but also|but|yet|still)',
            r'(?:it is not|this is not|that is not)[^.!?;]{3,25}(?:but rather|but|but instead)',
            r'(?:how\s+can|could\s+it\s+be|is\s+it\s+any\s+wonder|what\s+could)',
            r'(?:the more|the less|the harder|the longer)[^.!?;]{2,20}(?:the more|the less|the harder)',
            r'(?:whether|no matter|regardless of)[^.!?;]{3,20}(?:or)[^.!?;]{3,20}',
            r'(?:on\s+one\s+hand|on\s+the\s+one\s+hand)[^.!?;]{3,30}(?:on\s+the\s+other\s+hand|on\s+the\s+other)',
            r'(?:from|between)[^.!?;]{3,20}(?:to|and)[^.!?;]{3,20}',
            r'(?:both|either)[^.!?;]{2,15}(?:and|or)[^.!?;]{2,15}',
        ],
        "ja": [
            r'(?:だけでなく|のみならず|ばかりか)[^。！？]{3,20}(?:も|また|さらに)',
            r'(?:ではなく|ではなくて|じゃなく)[^。！？]{3,20}(?:である|だ|です)',
            r'(?:だろうか|ではないか|といえる|とは|何だろう)',
            r'(?:〜ば〜ほど|すればするほど|なればなるほど)',
            r'(?:でも|ても|でも|でも)[^。！？]{2,15}(?:ても|でも)',
            r'(?:一方で|他方で)[^。！？]{3,25}(?:また|他方)',
            r'(?:から|より|まで)[^。！？]{3,20}(?:に|へ|まで)',
            r'(?:も[あい]?れば|も[あい]?れば)[^。！？]{2,15}(?:も|ほど)',
        ],
    },
}


# ============================================================
#  logic_guard 模式
# ============================================================

LOGIC_GUARD = {
    "fact_patterns": {
        "zh": [
            (r'(?:在|于|从)\s*(\d{4})\s*年\s*', "历史日期"),
            (r'(?:根据|依照|按照)\s*[《「『].{2,30}[》」』]', "政策法规"),
            (r'\d{4}\s*年\s*[^。！？]{0,20}(?:达到|超过|实现|完成|发布|出台|成立|建立|发生)', "事件声明"),
            (r'(?:全球|全国|世界|亚洲|位居)[^。！？]{3,20}(?:第一|第二|第三|首位|前列|领先)', "排名"),
            (r'[《「「『][^》」」』]{4,30}[》」」』]', "政策文件名称"),
            (r'\d+\.?\d*%[^。！？]{0,20}(?:表明|显示|说明|意味)', "数据推论"),
        ],
        "en": [
            (r'(?:in|on|during|since|by)\s*(\d{4})\s*', "historical_date"),
            (r'(?:according\s+to|per|pursuant\s+to|under)\s+(?:the\s+)?(?:Act|Law|Regulation|Policy|Agreement|Treaty)', "policy_law"),
        ],
        "ja": [
            (r'(?:\d{4})\s*年\s*', "historical_date"),
            (r'(?:[「『][^」』]{2,30}[」』])', "policy_doc"),
            (r'(?:In|By|Since|After)\s*\d{4}[^.!?]{0,30}(?:reached|surpassed|achieved|completed|released|launched|established|signed)', "event_claim"),
            (r'(?:global|world|national|regional)[^.!?]{3,30}(?:first|top|leading|largest|highest|ranked)', "ranking"),
            (r'"(?:[A-Z][^"]{4,60})"(?:\s+(?:Act|Treaty|Agreement|Plan|Initiative|Program))?', "policy_document"),
            (r'\d+\.?\d*%[^.!?]{0,20}(?:indicate|suggest|show|demonstrate|reveal)', "data_inference"),
        ],
    },

    "causal_signals": {
        "forward": {   # cause → effect
            "zh": r'因为|由于|源于|来自于|起因于|得益于',
            "en": r'because|since|due\s+to|owing\s+to|stem\s+from|result\s+from|driven\s+by',
            "ja": r'なぜなら|というのも|だって|からには|により|によって|のため',
        },
        "backward": {   # effect ← cause
            "zh": r'因此|所以|从而|进而|于是|导致|引发|带来|催生|促使',
            "en": r'therefore|thus|hence|consequently|as\s+a\s+result|lead\s+to|result\s+in|give\s+rise\s+to|spark|trigger|fuel',
            "ja": r'したがって|だから|ゆえに|そのため|よって|引き起こす|もたらす|導く|招く|生む|起因する',
        },
    },

    "contradiction_signals": {
        "zh": r'然而|但是|不过|相反|恰恰|倒[是]?|实则|其实',
        "en": r'however|but|yet|nevertheless|nonetheless|on\s+the\s+contrary|conversely|in\s+contrast',
        "ja": r'しかし|だが|けれども|ところが|にもかかわらず|一方で|それに対して|逆に|反対に',
    },

    "certainty": {
        "high": {
            "zh": r'肯定|必然|一定|毫无疑问|毋庸置疑|事实证明|历史证明',
            "en": r'certainly|inevitably|undoubtedly|without\s+doubt|beyond\s+question|proven|demonstrated',
            "ja": r'必ず|間違いなく|絶対に|確かに|明らかに|疑いなく|証明された',
        },
        "medium": {
            "zh": r'大概率|很可能|有望|应该|预计',
            "en": r'likely|probably|expected|projected|anticipated|should|would',
        },
        "low": {
            "zh": r'也许|或许|可能|大概|似乎|恐怕|猜测|推测|不一定',
            "en": r'maybe|perhaps|possibly|might|could|apparently|seems|speculate|guess|unclear',
        },
    },

    "evidence_signals": {
        "zh": r'据[^。！？]{2,20}(?:数据|统计|报告|研究|调查|分析)|根据[^。！？]{2,20}',
        "en": r'(?:according\s+to|per|based\s+on|citing|data\s+(?:shows|suggests|indicates)|research\s+(?:finds|suggests))',
    },
}


# ============================================================
#  citation_guard 模式
# ============================================================

CITATION_GUARD = {
    "source_prefixes": {
        "zh": [
            r'(?:据|根据|来自|引用|援引|依照|按照|基于)',
            r'(?:数据|统计|报告|调查|研究|分析)[显示表明指出称]',
            r'(?:据.{2,20}(?:数据|统计|报告|调查))',
            r'(?:来自.{2,20}(?:的报告|的数据|的研究))',
        ],
        "en": [
            r'(?:according\s+to|per|based\s+on|citing|following)',
            r'(?:data|research|studies|reports|surveys|analysis)\s+(?:show|suggest|indicate|find|reveal|demonstrate)',
            r'(?:as\s+reported\s+by|as\s+stated\s+in|as\s+noted\s+by|as\s+of)',
            r'(?:source[ds]?\s+(?:say|suggest|indicate|report|claim)|sources\s+(?:say|suggest|indicate))',
        ],
    },

    "vague_patterns": {
        "zh": [
            r'(?:大量|许多|众多|不少|部分|一些|有些)[^。！？]{0,15}(?:数据|统计|研究|调查|案例)',
            r'(?:普遍|广泛|通常|一般[来]?[说讲]|总体[上来]?)',
            r'(?:明显|显著|大幅|快速|迅猛|急剧)[^。！？]{0,10}(?:增长|下降|上升|降低|变化|提升)',
        ],
        "en": [
            r'(?:many|lots\s+of|numerous|several|some|various)[^.!?]{0,20}(?:studies|reports|data|research|cases)',
            r'(?:widely|broadly|commonly|generally|typically|largely)',
            r'(?:significantly|dramatically|sharply|rapidly|quickly|substantially)[^.!?]{0,10}(?:increased|decreased|rose|fell|changed|improved)',
        ],
    },
}


# ============================================================
#  便捷获取接口
# ============================================================

_CONFIGS = {
    "edge_detector": EDGE_DETECTOR,
    "logic_guard": LOGIC_GUARD,
    "citation_guard": CITATION_GUARD,
}


def get_patterns(module: str, lang: Lang) -> dict:
    """获取指定模块的语言模式"""
    config = _CONFIGS.get(module, {})
    result = {}
    for key, val in config.items():
        if isinstance(val, dict) and lang in val:
            result[key] = val[lang]
        else:
            result[key] = val
    return result


def get_nested(module: str, *keys: str, lang: Lang) -> any:
    """获取深层嵌套的模式"""
    config = _CONFIGS.get(module, {})
    val = config
    for key in keys:
        if isinstance(val, dict):
            val = val.get(key, {})
            if isinstance(val, dict) and lang in val:
                val = val[lang]
        else:
            return None
    return val


if __name__ == "__main__":
    # 测试
    tests = [
        "这是中文文本，包含一些中文字符用于测试。",
        "This is an English text with no Chinese characters at all.",
        "Mixed 中英文 content 在一起.",
    ]
    for t in tests:
        print(f"  {t[:40]}... → {detect_lang(t)}")

    print()
    en_golden = get_nested("edge_detector", "golden_patterns", lang="en")
    print(f"英文金句模式数: {len(en_golden)}")
    zh_golden = get_nested("edge_detector", "golden_patterns", lang="zh")
    print(f"中文金句模式数: {len(zh_golden)}")
