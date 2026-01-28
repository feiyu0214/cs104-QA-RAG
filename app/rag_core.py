# app/rag_core.py
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

# Load .env file if present (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding


INDEX_PATH = os.getenv("INDEX_PATH", "data/processed/index")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")


def _load_prompt_library():
    """
    可选：如果你有 prompt/prompt_lib.py，就用它。
    要求它提供：
      - get_prompt(name: str) -> str
      - (可选) list_prompts() -> list[str]
    没有的话就用默认 prompt。
    """
    try:
        from prompt.prompt_lib import get_prompt, list_prompts  # type: ignore
        return get_prompt, list_prompts
    except Exception:
        def get_prompt(name: str) -> str:
            return DEFAULT_PROMPTS.get(name, DEFAULT_PROMPTS["ta_friendly"])
        def list_prompts() -> List[str]:
            return sorted(DEFAULT_PROMPTS.keys())
        return get_prompt, list_prompts


DEFAULT_PROMPTS: Dict[str, str] = {
    "ta_friendly": (
        "You are a friendly, patient CS course TA. Speak naturally like in-office-hours.\n"
        "Use the provided course materials as the source of truth.\n"
        "If the materials don’t contain the answer, say you’re not sure and suggest where to check.\n"
        "Do NOT sound like a formal report. No section headings like 'Answer:' or 'Policy:'.\n"
        "Keep it concise but include the key details (deadlines, penalties, required actions).\n"
    ),
    "professor_brief": (
        "You are the course instructor. Speak briefly and directly.\n"
        "Use course materials as the source of truth. No fluff, no headings.\n"
    ),
}

get_prompt, list_prompts = _load_prompt_library()


@lru_cache(maxsize=1)
def get_query_engine(similarity_top_k: int = 10):
    """Load index once and construct query engine once."""
    storage_context = StorageContext.from_defaults(persist_dir=INDEX_PATH)
    index = load_index_from_storage(storage_context)

    llm = OpenAI(model=LLM_MODEL, temperature=0, seed=42)
    embed_model = OpenAIEmbedding(model=EMBED_MODEL)

    # 用 index.as_query_engine 走最简单的 RAG：retrieve + synthesize
    qe = index.as_query_engine(
        similarity_top_k=similarity_top_k,
        llm=llm,
        embed_model=embed_model,
    )
    return qe


def _pretty_source(md: Dict[str, Any]) -> str:
    """网页展示可点击链接；本地 PDF 只展示文件名。"""
    url = md.get("url")
    fp = md.get("file_path") or md.get("source") or ""

    # 本地 pdf：只显示文件名
    if isinstance(fp, str) and fp.lower().endswith(".pdf"):
        return os.path.basename(fp)

    # 如果 url 是 file://，也只显示 basename（更像 TA）
    if isinstance(url, str) and url.startswith("file://"):
        return os.path.basename(url)

    # 网页：显示真实链接
    if isinstance(url, str) and url:
        return url

    return "(unknown source)"


def answer_question(
    question: str,
    prompt_name: str = "ta_friendly",
    similarity_top_k: int = 10,
) -> Dict[str, Any]:
    qe = get_query_engine(similarity_top_k=similarity_top_k)

    # 关键点：把“system prompt”注入到 query engine 的 response synthesizer prompt
    # 最省事做法：直接在问题前拼一个指令（MVP 够用、效果稳定）

    system = get_prompt(prompt_name).strip()
    q = f"{system}\n\nStudent question: {question.strip()}"
    resp = qe.query(q)

    # sources 去重
    sources: List[str] = []
    seen = set()
    for sn in getattr(resp, "source_nodes", []) or []:
        s = _pretty_source(sn.metadata or {})
        if s not in seen:
            sources.append(s)
            seen.add(s)

    return {
        "answer": str(resp).strip(),
        "sources": sources,
        "prompt_name": prompt_name,
    }


def available_prompts() -> List[str]:
    return list_prompts()
