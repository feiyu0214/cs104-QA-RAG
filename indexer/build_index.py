# indexer/build_index.py
import json
import os

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.readers.web import SimpleWebPageReader
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from urllib.parse import urlparse, urlunparse

# ---------- 基础配置 ----------
Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# ---------- 路径 ----------
URL_PATH = "data/raw/site_urls.json"
PDF_PATH = "docs"
INDEX_PATH = "data/processed/index"

os.makedirs("data/processed", exist_ok=True)

# ---------- 1️⃣ 读网页 URL ----------
with open(URL_PATH) as f:
    urls = json.load(f)

def normalize_url(u):
    p = urlparse(u)
    return urlunparse((
        p.scheme,
        p.netloc,
        p.path.rstrip("/"),
        "", "", ""
    ))

urls = sorted(set(normalize_url(u) for u in urls))

print(f"Loading {len(urls)} web pages...")

# ---------- 2️⃣ 加载网页 ----------
web_docs = SimpleWebPageReader(
    html_to_text=True
).load_data(urls)

# ⭐ 把 URL 存进 metadata
for doc in web_docs:
    # SimpleWebPageReader 默认会把 url 放在 metadata 里
    # 但我们显式确保一下
    if "url" not in doc.metadata and "source" in doc.metadata:
        doc.metadata["url"] = doc.metadata["source"]

for d in web_docs:
    d.metadata["source_type"] = "course_website"

# ---------- 3️⃣ 加载 PDF ----------
PDF_MAP_PATH = "data/processed/pdf_map.json"
pdf_map = {}
if os.path.exists(PDF_MAP_PATH):
    with open(PDF_MAP_PATH, "r") as f:
        pdf_map = json.load(f)
else:
    print(f"[warn] {PDF_MAP_PATH} not found. PDF citations will not have URLs.")

# 只读 docs 下的 pdf（包括 docs/website_pdfs 和你手动放的 CS104Syllabus.pdf）
pdf_docs = SimpleDirectoryReader(
    PDF_PATH,
    required_exts=[".pdf"],   # ⭐ 关键：只读 PDF，避免污染索引
).load_data()

mapped = 0
unmapped = 0

for d in pdf_docs:
    d.metadata["source_type"] = "course_pdf"

    fp = d.metadata.get("file_path") or d.metadata.get("source") or ""

    # 情况 A：下载的 pdf（在 docs/website_pdfs/）
    if "website_pdfs/" in fp:
        rel = "website_pdfs/" + fp.split("website_pdfs/")[-1]  # website_pdfs/<filename>.pdf
        if rel in pdf_map:
            d.metadata["url"] = pdf_map[rel]
            mapped += 1
        else:
            unmapped += 1

    # 情况 B：你手动放在 docs 根目录的 pdf（比如 CS104Syllabus.pdf）
    # 这类通常没有线上链接，就保留 file:// 形式，至少可点击/可定位
    else:
        # 给一个本地可追溯的“链接”
        if fp:
            # d.metadata["url"] = f"file://{fp}"
            d.metadata["url"] = os.path.basename(fp)

print(f"[PDF] total={len(pdf_docs)} mapped_to_web={mapped} unmapped_website_pdfs={unmapped}")


# ---------- 4️⃣ 合并 ----------
all_docs = web_docs + pdf_docs
print(f"Total documents: {len(all_docs)}")

# ---------- 5️⃣ 建索引 ----------
index = VectorStoreIndex.from_documents(all_docs)

# ---------- 6️⃣ 持久化 ----------
index.storage_context.persist(persist_dir=INDEX_PATH)
print(f"Index saved to {INDEX_PATH}")
