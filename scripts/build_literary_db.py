# -*- coding: utf-8 -*-
"""
文学向量库构建脚本
从工作区主 ChromaDB 复制 idioms 和 poem_sentences 集合

用法:
    python scripts/build_literary_db.py

前置条件:
    1. 工作区 ChromaDB 位于 .qclaw/workspace-agent-7d834448/chroma_db
    2. 已安装 chromadb 和 sentence-transformers

输出:
    vector_db/literary_ref/ (ChromaDB 目录)
      - idioms: 30,310 条成语
      - poem_sentences: 10,000 条诗词名句
"""

import chromadb
from chromadb.config import Settings
import os, sys

QCLAW_DB = os.path.expanduser("~/.qclaw/workspace-agent-7d834448/chroma_db")
DST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vector_db", "literary_ref")
COLLECTIONS = ["idioms", "poem_sentences"]

def main():
    if not os.path.exists(QCLAW_DB):
        print(f"源 ChromaDB 不存在: {QCLAW_DB}")
        print("请确认工作区 ChromaDB 位置，或手动配置 QCLAW_DB 路径")
        sys.exit(1)

    os.makedirs(DST, exist_ok=True)
    sc = chromadb.PersistentClient(path=QCLAW_DB, settings=Settings(anonymized_telemetry=False))
    dc = chromadb.PersistentClient(path=DST, settings=Settings(anonymized_telemetry=False))

    for name in COLLECTIONS:
        print(f"复制 {name}...")
        src_col = sc.get_collection(name)
        total = src_col.count()
        print(f"  读取 {total} 条...")
        data = src_col.get()
        try:
            dc.delete_collection(name)
        except:
            pass
        dst_col = dc.create_collection(name=name)
        dst_col.add(ids=data["ids"], embeddings=data["embeddings"],
                    metadatas=data["metadatas"], documents=data["documents"])
        print(f"  完成: {total} 条")

    print("\n验证:")
    for name in COLLECTIONS:
        cnt = dc.get_collection(name).count()
        print(f"  {name}: {cnt} 条")
    print(f"\n位置: {DST}")

if __name__ == "__main__":
    main()
