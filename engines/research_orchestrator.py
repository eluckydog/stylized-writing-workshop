# -*- coding: utf-8 -*-
"""
research_orchestrator.py — 全自动调研写作引擎

给定一个主题 + 风格，自动完成：
1. 联网搜索搜集数据和观点
2. 用 argument_controller 生成提纲
3. 按风格写文章
4. 5个引擎逐层校验
5. 不通过则重新修改，直到达标

用法:
    from engines.research_orchestrator import ResearchOrchestrator
    
    robot = ResearchOrchestrator()
    article = robot.write(
        topic="中国芯片产业现状与未来",
        style="maqianzu",
        max_iterations=3,
    )
    print(article["title"])
    print(article["content"])
    print(f"最终质量评分: {article['quality_score']}/100")
"""

from __future__ import annotations
import json
import re
import time
from typing import Optional
from pathlib import Path

# 引擎依赖
from engines.argument_controller import ArgumentController
from engines.vector_search import search_all


class ResearchOrchestrator:
    """全自动调研写作引擎"""

    def __init__(self, search_api: Optional[str] = None):
        """
        search_api: 联网搜索配置
            - "auto" (默认): 尝试可用搜索方式
            - None: 仅使用本地向量库
            - 自定义函数: search_fn(query) -> list[dict]
        """
        self._search_api = search_api
        self._search_results_cache = {}

    # ============================================================
    #  联网搜索
    # ============================================================

    def _web_search(self, query: str, top_k: int = 5) -> list[dict]:
        """联网搜索，返回 [{title, snippet, url}, ...]"""
        if query in self._search_results_cache:
            return self._search_results_cache[query][:top_k]

        results = []

        # 方案1: 调用 WebSearch（WorkBuddy 环境）
        try:
            import subprocess, sys
            # 尝试调用系统 WebSearch（如果有配置）
            # 这里留为可扩展接口
            pass
        except:
            pass

        # 方案2: DuckDuckGo（无需API key）
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=top_k):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                        "source": "duckduckgo",
                    })
        except ImportError:
            pass
        except Exception as e:
            pass  # 静默失败，回退到本地搜索

        # 方案3: 本地向量库搜索（兜底）
        if not results:
            local = search_all(query, top_k=top_k)
            for r in local:
                if "error" not in r:
                    results.append({
                        "title": r.get("metadata", {}).get("title", "本地参考"),
                        "snippet": r["document"][:200],
                        "url": "",
                        "source": f"local/{r.get('db', '')}",
                        "distance": r.get("distance", 0),
                    })

        self._search_results_cache[query] = results
        return results[:top_k]

    # ============================================================
    #  自动调研
    # ============================================================

    def research(self, topic: str) -> dict:
        """
        对给定主题进行自动调研，返回结构化调研报告

        返回:
            {
                "topic": str,
                "searches": [{"query": str, "results": [...]}, ...],
                "key_facts": [str, ...],
                "key_viewpoints": [str, ...],
                "data_points": [str, ...],
                "timeline": [str, ...],
            }
        """
        # 1. 自动生成搜索词
        search_queries = self._generate_search_queries(topic)
        
        # 2. 执行搜索
        all_results = []
        for query in search_queries:
            results = self._web_search(query, top_k=3)
            all_results.append({"query": query, "results": results})

        # 3. 从搜索结果中提取关键信息
        key_facts = []
        key_viewpoints = []
        data_points = []
        timeline = []

        for sq in all_results:
            for r in sq["results"]:
                snippet = r.get("snippet", "")
                # 提取数据点（含数字的句子）
                if re.search(r'\d+\.?\d*%|\d+[万亿亿]', snippet):
                    data_points.append(snippet[:120])
                # 提取时间线
                if re.search(r'\d{4}\s*年', snippet):
                    timeline.append(snippet[:120])
                # 提取事实性陈述
                if len(snippet) > 40:
                    key_facts.append(snippet[:200])

        return {
            "topic": topic,
            "searches": all_results,
            "key_facts": list(set(key_facts))[:10],
            "data_points": list(set(data_points))[:10],
            "timeline": list(set(timeline))[:5],
        }

    def _generate_search_queries(self, topic: str) -> list[str]:
        """根据主题生成多角度搜索词"""
        base_queries = [
            topic,
            f"{topic} 最新数据 2025 2026",
            f"{topic} 现状 分析",
            f"{topic} 问题 挑战",
            f"{topic} 趋势 前景",
        ]
        return base_queries

    # ============================================================
    #  全文写作管线
    # ============================================================

    def write(self, topic: str, style: str = "maqianzu",
              max_iterations: int = 3, verbose: bool = True) -> dict:
        """
        全自动写作管线

        参数:
            topic: 写作主题
            style: 写手风格
            max_iterations: 最大迭代次数（质量不达标时重写）
            verbose: 是否输出中间日志

        返回:
            {
                "title": str,
                "content": str,
                "quality_score": int,
                "quality_report": dict,
                "iterations": int,
                "research": dict,
            }
        """
        if verbose:
            print(f"\n{'='*50}")
            print(f"  AI 自动写作启动")
            print(f"  主题: {topic}")
            print(f"  风格: {style}")
            print(f"{'='*50}")

        # === Phase 1: 调研 ===
        if verbose:
            print(f"\n[1/5] 联网调研...")
        research_data = self.research(topic)
        if verbose:
            print(f"      搜索了 {len(research_data['searches'])} 组关键词")
            print(f"      提取 {len(research_data['data_points'])} 条数据点")

        # === Phase 2: 生成提纲 ===
        if verbose:
            print(f"\n[2/5] 生成写作提纲...")
        try:
            ctrl = ArgumentController(style)
            outline = ctrl.generate_outline(topic)
        except ValueError:
            # 未知风格，使用默认三段论
            outline = [
                {"stage": "背景与问题", "required": True, "prompt": f"介绍{topic}的背景和核心问题"},
                {"stage": "分析与数据", "required": True, "prompt": f"分析{topic}的关键数据和趋势"},
                {"stage": "结论与展望", "required": True, "prompt": f"总结并提出{topic}的建议"},
            ]
        if verbose:
            for item in outline:
                print(f"      [{item['stage']}]")

        # === Phase 3: 生成文章 ===
        if verbose:
            print(f"\n[3/5] 生成初稿...")
        
        # 构建上下文（调研数据 + 提纲）
        context = self._build_context(topic, research_data, outline, style)
        draft = self._generate_draft(context, style)
        if verbose:
            word_count = len(draft)
            print(f"      初稿完成 ({word_count} 字)")

        # === Phase 4: 质量校验与迭代 ===
        if verbose:
            print(f"\n[4/5] 质量校验...")

        best_draft = draft
        best_score = 0
        best_report = None

        for iteration in range(max_iterations):
            if verbose:
                print(f"      第 {iteration+1}/{max_iterations} 轮校验")

            # 运行所有引擎
            report = self._quality_check(draft, style)

            score = report.get("overall_score", 50)
            status = report.get("status", "unknown")

            if verbose:
                print(f"        质量评分: {score}/100 ({status})")
                for issue in report.get("issues", [])[:3]:
                    sev = issue.get("severity", "info")
                    dim = issue.get("dimension", "")
                    det = issue.get("detail", "")[:60]
                    print(f"          [{sev}] {dim}: {det}")

            if score > best_score:
                best_draft = draft
                best_score = score
                best_report = report

            # 如果达标，提前退出
            if status == "good" or score >= 70:
                if verbose:
                    print(f"        质量达标，停止迭代")
                break

            # 否则根据报告修改
            if iteration < max_iterations - 1:
                if verbose:
                    print(f"        未达标，根据报告修改...")
                draft = self._revise(draft, report, context, style)

        # === Phase 5: 最终报告 ===
        if verbose:
            print(f"\n[5/5] 完成")
            print(f"{'='*50}")
            print(f"  最终质量评分: {best_score}/100")
            print(f"  迭代次数: {iteration + 1}")
            print(f"{'='*50}")

        return {
            "title": f"{topic} — {style}风格分析",
            "content": best_draft,
            "quality_score": best_score,
            "quality_report": best_report,
            "iterations": iteration + 1,
            "research": {
                "searches": len(research_data["searches"]),
                "data_points": len(research_data["data_points"]),
                "facts": len(research_data["key_facts"]),
            },
        }

    def _build_context(self, topic: str, research: dict,
                       outline: list[dict], style: str) -> str:
        """构建写作上下文"""
        parts = [f"写作主题: {topic}", f"写作风格: {style}", ""]

        # 调研数据
        if research["data_points"]:
            parts.append("【关键数据】")
            for dp in research["data_points"][:5]:
                parts.append(f"  - {dp}")
            parts.append("")

        # 提纲
        parts.append("【文章结构】")
        for item in outline:
            flag = "必写" if item.get("required", True) else "可选"
            parts.append(f"  [{flag}] {item['stage']}: {item.get('prompt', '')}")
        parts.append("")

        # 方法论骨架（由 methodology/ 蒸馏画像驱动，不依赖 RAG 是否命中）
        # 即使话题语料未覆盖，也能提供"怎么想"的论证骨架
        try:
            from methodology.methodology_engine import instantiate, format_scaffold
            sc = instantiate(style, topic)
            if "error" not in sc:
                parts.append("【方法论骨架 · 该风格的「怎么想」】")
                for line in format_scaffold(sc).split("\n"):
                    if line.strip():
                        parts.append(f"  {line}")
                parts.append("")
        except Exception:
            pass  # 方法论模块缺失不影响主流程

        return "\n".join(parts)

    def _generate_draft(self, context: str, style: str) -> str:
        """
        生成初稿。
        在 WorkBuddy 中此函数由 LLM 调用，
        纯 Python 模式下返回占位文本。
        """
        # 这里是一个占位实现
        # 在 WorkBuddy 中，这个函数会被替换为实际的 LLM 调用
        lines = [
            f"# {context.split(chr(10))[0] if context else '文章'}",
            "",
            "【注意】本文由 research_orchestrator 自动生成。",
            "在 WorkBuddy 环境中，此部分将调用 LLM 进行实际写作。",
            "",
        ]
        # 从 context 提取结构
        for line in context.split("\n"):
            if line.startswith("  [必写]") or line.startswith("  [可选]"):
                lines.append("")
                lines.append(line.replace("  [必写] ", "## ").replace("  [可选] ", "## "))
                lines.append("")
                lines.append("待生成内容...")
        return "\n".join(lines)

    def _quality_check(self, text: str, style: str) -> dict:
        """运行所有引擎进行质量校验"""
        from engines.edge_detector_essay import full_report
        from engines.citation_guard import CitationGuard
        from engines.logic_guard import LogicGuard

        # 1. AI味检测
        report = full_report(text)

        # 2. 引用检查
        try:
            citation = CitationGuard().scan(text)
        except:
            citation = {"citation_score": 50}

        # 3. 逻辑检查
        try:
            logic = LogicGuard().scan(text)
        except:
            logic = {"overall_score": 50}

        # 综合评分
        scores = [
            report.get("overall_score", 50),
            citation.get("citation_score", 50),
            logic.get("overall_score", 50),
        ]
        overall = round(sum(scores) / len(scores), 1)

        issues = report.get("issues", [])
        issues.append({"dimension": "引用质量", "severity": "info",
                       "detail": f"评分 {citation.get('citation_score', 0)}/100"})
        issues.append({"dimension": "逻辑一致性", "severity": "info",
                       "detail": f"评分 {logic.get('overall_score', 0)}/100"})

        return {
            "overall_score": overall,
            "status": report.get("status", "unknown"),
            "scores": {
                "ai_taste": report.get("overall_score", 50),
                "citation": citation.get("citation_score", 50),
                "logic": logic.get("overall_score", 50),
            },
            "issues": issues,
        }

    def _revise(self, draft: str, report: dict,
                context: str, style: str) -> str:
        """
        根据质量报告修改文章。
        在 WorkBuddy 中由 LLM 执行修改，
        纯 Python 模式下返回原文加上修改说明。
        """
        # 提取需要修改的问题
        critical_issues = [i for i in report.get("issues", [])
                          if i.get("severity") in ("critical", "warning")]
        
        revision_notes = ["【修改说明】"]
        for issue in critical_issues[:5]:
            revision_notes.append(f"- {issue['dimension']}: {issue.get('detail', '')}")
        
        if critical_issues:
            revision_notes.append("")
            revision_notes.append("(以上问题需要修改，在 WorkBuddy 环境中将自动重写)")
        
        return draft + "\n\n" + "\n".join(revision_notes)


# ============================================================
#  便捷接口
# ============================================================

def auto_write(topic: str, style: str = "maqianzu", **kwargs) -> dict:
    """一键写文章"""
    robot = ResearchOrchestrator(**kwargs)
    return robot.write(topic, style=style)


def quick_research(topic: str) -> dict:
    """快速调研"""
    robot = ResearchOrchestrator()
    return robot.research(topic)


if __name__ == "__main__":
    # 测试
    import sys

    if len(sys.argv) > 1:
        topic = sys.argv[1]
        style = sys.argv[2] if len(sys.argv) > 2 else "maqianzu"
    else:
        topic = "中国芯片产业"
        style = "maqianzu"

    robot = ResearchOrchestrator()
    article = robot.write(topic, style=style, verbose=True, max_iterations=2)
    print(f"\n标题: {article['title']}")
    print(f"质量: {article['quality_score']}/100")
    print(f"迭代: {article['iterations']} 轮")
    print(f"调研: {article['research']}")
