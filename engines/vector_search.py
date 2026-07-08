# -*- coding: utf-8 -*-
"""
vector_search.py — 向量检索引擎

统一检索写作工坊的所有向量数据库：
1. maqianzu/     — 马前卒语料 1376 条语义切片
2. lukewen/      — 卢克文文集 444 篇（约12K语义块）
3. jiubian/      — 九边公众号文集 562 篇（约12K语义块）
4. literary_ref/ — idioms 30K + poem_sentences 10K

用法:
    from engines.vector_search import search_all, search_writer

    # 跨库搜索
    results = search_all("房价", top_k=3)
    
    # 按写手搜索
    results = search_writer("maqianzu", "芯片产业")
    
    # 搜索文学引用
    results = search_literary("坚持不懈", top_k=5)
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from engines.lang_config import detect_lang

# 向量库根目录（相对于 workshop 根目录）
WORKSHOP_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = WORKSHOP_DIR / "vector_db"

SEARCHABLE_DBS = {
    "maqianzu": {
        "path": VECTOR_DIR / "maqianzu",
        "collections": ["maqianzu"],
        "description": "马前卒语料（睡前消息832期+高见40+参考信息446+黑话60）",
    },
    "lukewen": {
        "path": VECTOR_DIR / "lukewen",
        "collections": ["lukewen"],
        "description": "卢克文文集（444篇，约12K语义块）",
    },
    "jiubian": {
        "path": VECTOR_DIR / "jiubian",
        "collections": ["jiubian"],
        "description": "九边公众号文集（562篇，约12K语义块）",
    },
    "literary_ref": {
        "path": VECTOR_DIR / "literary_ref",
        "collections": ["idioms", "poem_sentences"],
        "description": "文学引用（成语30K + 诗词名句10K）",
    },
}

# 延迟加载 ChromaDB（避免 import 时阻塞）
_client_cache: dict[str, "chromadb.PersistentClient"] = {}
_model = None


def _get_client(db_key: str):
    """获取或创建 ChromaDB 客户端"""
    if db_key not in _client_cache:
        import chromadb
        from chromadb.config import Settings
        db_info = SEARCHABLE_DBS[db_key]
        _client_cache[db_key] = chromadb.PersistentClient(
            path=str(db_info["path"]),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client_cache[db_key]


def _get_model():
    """获取或创建 embedding 模型

    优先使用本地已缓存的 BAAI/bge-small-zh-v1.5 快照路径（彻底离线、绕 GFW）；
    若本地缓存缺失，回退到模型名（此时需要能访问 HuggingFace，仅作兜底）。
    """
    global _model
    if _model is None:
        import glob as _glob
        from sentence_transformers import SentenceTransformer
        _cache_root = os.path.expanduser(
            "~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots")
        _snaps = sorted(_glob.glob(os.path.join(_cache_root, "*")))
        _model_name = _snaps[-1] if _snaps else "BAAI/bge-small-zh-v1.5"
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        _model = SentenceTransformer(_model_name, trust_remote_code=True)
    return _model


def search(db_key: str, query: str, collection_name: Optional[str] = None,
           top_k: int = 5, where: Optional[dict] = None) -> list[dict]:
    """
    检索指定向量库

    参数:
        db_key: "maqianzu" | "literary_ref"
        query: 查询文本
        collection_name: 指定 collection（不指定则搜索所有）
        top_k: 返回条数
        where: metadata 过滤条件

    返回:
        [{"id", "document", "metadata", "distance", "db", "collection"}, ...]
    """
    if db_key not in SEARCHABLE_DBS:
        return [{"error": f"未知向量库: {db_key}，可用: {list(SEARCHABLE_DBS.keys())}"}]

    db_info = SEARCHABLE_DBS[db_key]
    client = _get_client(db_key)
    model = _get_model()
    query_emb = model.encode(query).tolist()

    results = []
    collections_to_search = [collection_name] if collection_name else db_info["collections"]

    for col_name in collections_to_search:
        try:
            col = client.get_collection(col_name)
        except Exception:
            continue

        try:
            resp = col.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                where=where,
            )
            for i in range(len(resp["ids"][0])):
                results.append({
                    "id": resp["ids"][0][i],
                    "document": resp["documents"][0][i],
                    "metadata": resp["metadatas"][0][i],
                    "distance": resp["distances"][0][i],
                    "db": db_key,
                    "collection": col_name,
                })
        except Exception as e:
            results.append({"error": f"{db_key}/{col_name}: {e}"})

    # 按距离排序
    results.sort(key=lambda x: x.get("distance", 1))
    return results[:top_k]


def search_all(query: str, top_k: int = 5) -> list[dict]:
    """跨所有库搜索"""
    all_results = []
    for db_key in SEARCHABLE_DBS:
        all_results.extend(search(db_key, query, top_k=top_k))
    all_results.sort(key=lambda x: x.get("distance", 1))
    return all_results[:top_k]


def search_writer(writer: str, query: str, top_k: int = 5) -> list[dict]:
    """
    按写手搜索参考素材

    writer: "maqianzu" | "jiubian" | "lukewen" | "natgeo"
    目前 maqianzu / lukewen / jiubian 均有本地向量库
    """
    writer_db_map = {
        "maqianzu": "maqianzu",
        "lukewen": "lukewen",
        "jiubian": "jiubian",
    }
    db_key = writer_db_map.get(writer)
    if not db_key:
        return [{"info": f"'{writer}' 暂无本地向量库，待补充语料"}]
    return search(db_key, query, top_k=top_k)


def search_literary(query: str, top_k: int = 5, type_filter: Optional[str] = None) -> list[dict]:
    """
    搜索文学引用库（成语/诗词）

    type_filter: "idioms" | "poem_sentences" | None (全部)
    """
    return search("literary_ref", query, collection_name=type_filter, top_k=top_k)


def list_dbs() -> list[dict]:
    """列出所有可用向量库"""
    info = []
    for key, cfg in SEARCHABLE_DBS.items():
        db_path = cfg["path"]
        sqlite = db_path / "chroma.sqlite3"
        size_mb = sqlite.stat().st_size // (1024 * 1024) if sqlite.exists() else 0
        
        client = _get_client(key)
        col_info = []
        for col_name in cfg["collections"]:
            try:
                col = client.get_collection(col_name)
                col_info.append(f"{col_name}({col.count()}条)")
            except:
                col_info.append(f"{col_name}(不可用)")

        info.append({
            "name": key,
            "size_mb": size_mb,
            "collections": col_info,
            "description": cfg["description"],
        })
    return info


if __name__ == "__main__":
    # 自测
    print("=== 向量库状态 ===")
    for db in list_dbs():
        print(f"  {db['name']}: {db['size_mb']}MB, {', '.join(db['collections'])}")
    print()

    test_queries = ["房价", "芯片", "坚持不懈"]

    for q in test_queries:
        print(f"\n=== 搜索: {q} ===")
        results = search_all(q, top_k=2)
        for r in results:
            if "error" in r:
                print(f"  [ERROR] {r['error']}")
                continue
            doc = r["document"][:60] + "..." if len(r["document"]) > 60 else r["document"]
            print(f"  [{r['db']}/{r['collection']}] {doc}")
            print(f"    dist={r['distance']:.4f}")
