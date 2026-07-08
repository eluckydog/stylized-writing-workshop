# -*- coding: utf-8 -*-
"""
向量化马前卒（马督公）语料库 -> ChromaDB （单库构建 + 目录复制版）

为什么这样最稳：
  之前 36k 块的双副本构建多次出现「向量 parquet 在、但 collections 注册表 0 行、
  跨进程重开即丢失」。对照实验确认：唯一 100% 跨进程存活的配置是
  「单 chroma 客户端 + 真实 36k + torch 同进程后台」（repro4）；而失败的构建全部是
  「同一进程内连续写两个 chroma collection」。

  因此本版只建【一个】collection（复刻 repro4），跨进程校验落盘后，
  再用操作系统目录复制把整库拷贝到第二处——复制是纯文件系统操作，
  不涉及 chroma，绝不会丢 collection 注册。

语料在 D:\向量库\睡前消息文稿的存档仓库\docs\睡前消息 下递归分布
  （opinion 高见 / refnews 参考信息 / slang 黑话 / 睡前消息 四类区间子目录）
每个 .md 带 YAML frontmatter、正文含开场白/失效微信链接/图片引用等噪声，已专用清洗。
collection 名固定为 "maqianzu"，与 vector_search.py / distill.py 对齐。
主库写入【工作区版】，再用目录复制得到【插件版】。

用法：
  python scripts/build_maqianzu_db.py                 # 完整构建
  python scripts/build_maqianzu_db.py --dry          # 只切分统计，不加载模型/不入库
"""
import os, re, json, hashlib, glob, argparse, shutil, sys, subprocess
from pathlib import Path

# ---- 强制离线：模型已缓存在本地，绝不联网（GFW 环境）----
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
_CACHE_ROOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots")
_SNAPS = sorted(glob.glob(os.path.join(_CACHE_ROOT, "*")))
LOCAL_MODEL_DIR = _SNAPS[-1] if _SNAPS else "BAAI/bge-small-zh-v1.5"

SRC = Path(r"D:\向量库\睡前消息文稿的存档仓库\docs\睡前消息")
WORKSHOP_DST = Path(r"C:\Users\13918\Workspace\stylized-writing-workshop\vector_db\maqianzu")
PLUGIN_DST = Path(r"C:\Users\13918\.workbuddy\plugins\marketplaces\my-experts\plugins\stylized-writing-workshop\vector_db\maqianzu")

MAX_CHARS = 500          # 单个合并段超过此值再按句切分
MERGE_TARGET = 300        # 短段落向上合并的目标长度（对齐九边 ~270 字/块粒度）
COLLECTION = "maqianzu"

# ---------- 清洗 ----------
_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")                 # 图片引用
_WX_RE = re.compile(r">\s*\[[^\]]*\]\([^)]*\)")               # 失效微信/外链引用块
_URL_RE = re.compile(r"https?://\S+")                         # 裸 URL
_BOILER_RE = re.compile(r"(欢迎观看|马前卒工作室|点击下文观看视频|点击下图观看视频|下面请\S*同学帮我介绍)")

def clean_para(p: str) -> str:
    p = _IMG_RE.sub("", p)
    p = _WX_RE.sub("", p)
    p = _URL_RE.sub("", p)
    p = re.sub(r'^#+\s*', '', p)                              # 去 markdown 标题符
    p = re.sub(r'^\s*>\s*', '', p)                           # 去引用符残留
    p = re.sub(r'\.pdf$', '', p, flags=re.I)                  # 去标题 .pdf 噪声
    p = p.strip()
    if _BOILER_RE.search(p):
        return ""                                             # 整行是开场白噪声，丢弃
    return p

def split_sentences(text: str):
    parts = re.split(r'(?<=[。！？；\n])', text)
    return [x.strip() for x in parts if x.strip()]

def chunk_text(text: str):
    # 1. 按空行切段 + 清洗 + 丢弃过短噪声段
    paras = [clean_para(p) for p in re.split(r'\n\s*\n', text)]
    paras = [p for p in paras if len(p) > 30]

    # 2. 短段落向上合并到 MERGE_TARGET，避免口语转录体被切得太碎
    merged = []
    buf = ""
    for p in paras:
        if buf and len(buf) + len(p) <= MERGE_TARGET:
            buf += "\n" + p
        else:
            if buf:
                merged.append(buf)
            buf = p
    if buf:
        merged.append(buf)

    # 3. 合并段超 MAX_CHARS 再按句细切
    chunks = []
    for m in merged:
        if len(m) <= MAX_CHARS:
            chunks.append(m)
        else:
            b = ""
            for s in split_sentences(m):
                if len(b) + len(s) <= MAX_CHARS:
                    b += s
                else:
                    if b:
                        chunks.append(b)
                    b = s
            if b:
                chunks.append(b)
    return chunks

def parse_frontmatter(text: str):
    title, date = "", ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            m_t = re.search(r"title:\s*(.+)", fm)
            m_d = re.search(r"date:\s*(\d{4}-\d{2}-\d{2})", fm)
            if m_t:
                title = m_t.group(1).strip().strip('"').strip("'")
            if m_d:
                date = m_d.group(1)
            text = text[end + 4:]
    return text, title, date

# ---------- 读取语料 ----------
def collect_files():
    files = []
    for f in sorted(SRC.rglob("*.md")):
        if f.name.lower() == "index.md":
            continue
        files.append(f)
    return files

def build_chunks(files):
    chunks = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        text, fm_title, fm_date = parse_frontmatter(text)
        try:
            rel = f.relative_to(SRC)
            category = rel.parts[0] if rel.parts else ""
        except Exception:
            category = ""
        base_title = fm_title or f.stem
        title = re.sub(r"^(btnews|opinion|refnews|slang)_", "", base_title)
        date = fm_date
        for i, c in enumerate(chunk_text(text)):
            chunks.append({
                "id": hashlib.md5(f"{f.name}_{i}".encode()).hexdigest()[:12],
                "document": c,
                "metadata": {
                    "title": title, "date": date,
                    "source": f.name, "category": category,
                    "para_index": i,
                },
            })
    return chunks

# ---------- 跨进程校验：独立子进程打开 DB，确认 collection 可见 ----------
def _verify_cross_process(dst: str, expected: int) -> bool:
    code = (
        "import sys, chromadb\n"
        "from chromadb.config import Settings\n"
        f"c = chromadb.PersistentClient(path={dst!r}, settings=Settings(anonymized_telemetry=False))\n"
        "try:\n"
        f"    n = c.get_collection({COLLECTION!r}).count()\n"
        f"    sys.exit(0 if n == {expected} else 2)\n"
        "except Exception:\n"
        "    sys.exit(3)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return r.returncode == 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只切分统计，不加载模型/不入库")
    args = ap.parse_args()

    files = collect_files()
    print(f"[1/4] 找到 {len(files)} 篇文章（已排除 index.md）")

    chunks = build_chunks(files)
    print(f"[2/4] 分块完成: {len(chunks)} 个语义块（平均 {sum(len(c['document']) for c in chunks)//max(len(chunks),1)} 字/块）")

    if args.dry:
        print("\n--- 示例前 3 块 ---")
        for c in chunks[:3]:
            print(f"[{c['metadata']['category']}/{c['metadata']['title'][:20]}] {c['document'][:120]}")
        print("\n[DRY] 结束，未加载模型、未入库。")
        return

    # ---------- [3/4] 编码（加载 torch）----------
    import numpy as np
    from sentence_transformers import SentenceTransformer
    print(f"[3/4] 加载模型 (离线本地路径): {LOCAL_MODEL_DIR}")
    model = SentenceTransformer(LOCAL_MODEL_DIR)
    print(f"      生成向量 ({len(chunks)} 条) ...")
    texts = [c["document"] for c in chunks]
    embs = model.encode(texts, show_progress_bar=True, batch_size=128)

    # ---------- [4/4] 建【一个】collection（复刻 repro4 已验证存活的配置）----------
    import chromadb
    from chromadb.config import Settings
    N = len(chunks)
    if WORKSHOP_DST.exists():
        shutil.rmtree(WORKSHOP_DST)
    WORKSHOP_DST.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(WORKSHOP_DST), settings=Settings(anonymized_telemetry=False))
    col = client.create_collection(name=COLLECTION)
    for i in range(0, N, 500):
        b = chunks[i:i + 500]
        col.add(ids=[c["id"] for c in b],
                embeddings=embs[i:i + 500].tolist(),
                documents=[c["document"] for c in b],
                metadatas=[c["metadata"] for c in b])
    n = col.count()
    client.close()
    ok = _verify_cross_process(str(WORKSHOP_DST), n)
    print(f"      [主库] 写入 {n} 条 | 跨进程验证 {'OK ✓' if ok else 'FAIL ✗ 落盘失败!'}")

    # 目录复制得到插件版（纯文件系统，不碰 chroma）
    if PLUGIN_DST.exists():
        shutil.rmtree(PLUGIN_DST)
    shutil.copytree(WORKSHOP_DST, PLUGIN_DST)
    ok2 = _verify_cross_process(str(PLUGIN_DST), n)
    print(f"      [副本] 目录复制 -> {PLUGIN_DST} | 跨进程验证 {'OK ✓' if ok2 else 'FAIL ✗'}")

    info = {
        "corpus_root": str(SRC),
        "chroma_dir": str(WORKSHOP_DST),
        "model": "BAAI/bge-small-zh-v1.5",
        "total_files": len(files),
        "total_chunks": N,
        "collection": COLLECTION,
        "chunk_strategy": "hybrid(blank-line + sentence<=500) + 马督公格式清洗",
        "created_at": __import__("datetime").datetime.now().isoformat(),
    }
    for D in [PLUGIN_DST, WORKSHOP_DST]:
        with open(D / "info.json", "w", encoding="utf-8") as fp:
            json.dump(info, fp, ensure_ascii=False, indent=2)

    print(f"\n[完成] {N} 条向量已写入两处 vector_db/{COLLECTION}/"
          f"（{'全部落盘 ✓' if (ok and ok2) else '存在失败项 ✗，需排查'}）")

if __name__ == "__main__":
    main()
