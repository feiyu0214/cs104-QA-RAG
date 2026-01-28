# app/api.py
import os
import time

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """自定义限流错误响应"""
    return JSONResponse(
        status_code=429,
        content={
            "answer": "You've sent too many requests. Please wait a minute before trying again. (Limit: 10 requests per minute)",
            "sources": [],
            "prompt_name": "error",
        },
    )

from app.rag_core import answer_question, available_prompts, INDEX_PATH

# ─────────────────────────────────────────────────────────────────────────────
# Sentry 错误追踪
# ─────────────────────────────────────────────────────────────────────────────
SENTRY_DSN = os.getenv("SENTRY_DSN")
# Only init if DSN is set and not a placeholder
if SENTRY_DSN and "xxx" not in SENTRY_DSN:
    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=0.1,  # 10% 请求追踪
            environment=os.getenv("ENVIRONMENT", "production"),
        )
        logger.info("Sentry initialized")
    except Exception as e:
        logger.warning(f"Sentry initialization failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Loguru 配置
# ─────────────────────────────────────────────────────────────────────────────
# 移除默认 handler，使用自定义格式输出到 stdout（Railway 自动收集）
logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
)

# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="CS104 QA RAG")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 静态网页
app.mount("/static", StaticFiles(directory="web/static"), name="static")


class QueryReq(BaseModel):
    question: str
    prompt_name: str = "ta_friendly"
    top_k: int = 10


@app.get("/")
def home():
    return FileResponse("web/index.html")


@app.get("/prompts")
def prompts():
    return {"prompts": available_prompts()}


# ─────────────────────────────────────────────────────────────────────────────
# 健康检查
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    index_exists = os.path.isdir(INDEX_PATH)
    return {
        "status": "ok",
        "index_loaded": index_exists,
        "index_path": INDEX_PATH,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 查询端点（带限流）
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/query")
@limiter.limit("10/minute")
def query(request: Request, req: QueryReq):
    start_time = time.time()
    client_ip = get_remote_address(request)

    logger.info(f"Query from {client_ip}: {req.question[:50]}...")

    try:
        result = answer_question(
            question=req.question,
            prompt_name=req.prompt_name,
            similarity_top_k=req.top_k,
        )
        elapsed = time.time() - start_time
        logger.info(f"Query completed in {elapsed:.2f}s for {client_ip}")
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Query failed after {elapsed:.2f}s for {client_ip}: {e}")

        # Sentry 自动捕获异常
        if SENTRY_DSN:
            sentry_sdk.capture_exception(e)

        return JSONResponse(
            status_code=500,
            content={
                "answer": "Internal server error. Please try again later.",
                "sources": [],
                "prompt_name": req.prompt_name,
            },
        )
