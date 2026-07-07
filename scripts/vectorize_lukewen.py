# -*- coding: utf-8 -*-
"""
vectorize_lukewen.py — 卢克文语料向量化脚本

用法:
    python scripts/vectorize_lukewen.py

输入: 桌面 lukewen_kb_complete/lukewen_md/ (444篇 .md)
输出: vector_db/lukewen/ (ChromaDB)
"""

import os, re, json, hashlib
from pathlib import Path

WORKSHOP = Path(__file__).resolve().parent.parent
SRC = Path(r"C:\Users\13918\Desktop\lukewen_kb_complete\lukewen_md")
DST = WORKSHOP / "vector_db" / "lukewen"

def main():
    if not SRC.exists():
        print(f"源目录不存在: {SRC}")
        return

    DST.mkdir(parents=True, exist_ok=True)
    files = sorted(SRC.glob("*.md"))
    print(f"找到 {len(files)} 篇卢克文文章")

    chunks = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        title_match = re.search(r"\[(.*?)\](.*?)\.md", f.name)
        title = title_match.group(2) if title_match else f.stem
        date = title_match.group(1) if title_match else ""
        paras = [p.strip() for p in re.split(r'\n\s*\n', text) if len(p.strip()) > 50]

        for i, para in enumerate(paras):
            doc_id = hashlib.md5(f"{f.name}_{i}".encode()).hexdigest()[:12]
            chunks.append({
                "id": doc_id,
                "document": para[:500],
                "metadata": {"title": title, "date": date, "source": f.name, "para_index": i},
            })

    print(f"生成 {len(chunks)} 个语义块")

    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    print("加载 embedding 模型...")
    model = SentenceTransformer("BAAI/bge-small-zh-v1.5", trust_remote_code=True)

    print("生成向量...")
    texts = [c["document"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)

    client = chromadb.PersistentClient(path=str(DST), settings=Settings(anonymized_telemetry=False))
    try: client.delete_collection("lukewen")
    except: pass
    col = client.create_collection(name="lukewen")

    BATCH = 500
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i+BATCH]
        col.add(ids=[c["id"] for c in batch],
                embeddings=embeddings[i:i+BATCH].tolist(),
                documents=[c["document"] for c in batch],
                metadatas=[c["metadata"] for c in batch])

    print(f"写入完成: {col.count()} 条")

    info = {
        "corpus_root": str(SRC),
        "model": "BAAI/bge-small-zh-v1.5",
        "total_files": len(files),
        "total_chunks": len(chunks),
        "created_at": __import__("datetime").datetime.now().isoformat(),
    }
    with open(DST / "info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"info.json 已写入\n完成!")

if __name__ == "__main__":
    main()
