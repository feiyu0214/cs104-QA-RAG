# CS104 QA RAG 项目记忆文档

## 项目概述

这是一个为 USC CS104 课程构建的 RAG（检索增强生成）问答系统，帮助学生查询课程相关问题。

- **GitHub 仓库**: https://github.com/feiyu0214/cs104-QA-RAG
- **部署平台**: Railway
- **技术栈**: FastAPI + LlamaIndex + OpenAI

## 架构

```
用户 → Web UI → FastAPI API → LlamaIndex RAG → OpenAI GPT-4o-mini
                                    ↓
                            本地向量索引 (data/processed/index/)
```

## 目录结构

```
cs104-QA-RAG/
├── app/
│   ├── api.py          # FastAPI 主应用（限流、日志、健康检查）
│   ├── rag_core.py     # RAG 核心逻辑（加载索引、查询）
│   └── rag_query.py    # 查询辅助工具
├── web/
│   ├── index.html      # 前端页面
│   └── static/
│       ├── app.js      # 前端逻辑
│       └── style.css   # 样式
├── data/
│   ├── processed/
│   │   └── index/      # 预构建的向量索引（~4.3MB，已提交到 Git）
│   └── raw/
│       └── site_urls.json
├── docs/               # 课程文档（PDF）
├── crawler/            # 网站爬虫
├── indexer/            # 索引构建工具
├── prompt/
│   └── prompt_lib.py   # Prompt 模板库
├── requirements.txt    # Python 依赖
├── Procfile           # Railway 启动命令
├── .env.example       # 环境变量示例
└── .gitignore
```

## 关键文件说明

### app/api.py
- FastAPI 应用入口
- **限流**: 10 次/分钟/IP（使用 slowapi）
- **日志**: 使用 loguru，输出到 stdout
- **错误追踪**: 可选 Sentry 集成
- **端点**:
  - `GET /` - 前端页面
  - `GET /health` - 健康检查
  - `GET /prompts` - 可用 prompt 列表
  - `POST /query` - 主查询接口（带限流）

### app/rag_core.py
- 加载预构建的向量索引
- 使用 LlamaIndex 进行 RAG 查询
- 支持多种 prompt 风格（ta_friendly, professor_brief）

## 环境变量

| 变量 | 必须 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 是 | OpenAI API 密钥 |
| `SENTRY_DSN` | 否 | Sentry 错误追踪 DSN |
| `INDEX_PATH` | 否 | 索引路径，默认 `data/processed/index` |
| `LLM_MODEL` | 否 | LLM 模型，默认 `gpt-4o-mini` |
| `EMBED_MODEL` | 否 | 嵌入模型，默认 `text-embedding-3-small` |

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 添加 OPENAI_API_KEY

# 启动开发服务器
uvicorn app.api:app --reload

# 访问
open http://localhost:8000
```

## 部署

- **平台**: Railway（自动从 GitHub 部署）
- **启动命令**: `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
- **环境变量**: 在 Railway Variables 中配置 `OPENAI_API_KEY`

## API 使用示例

```bash
# 健康检查
curl https://your-app.railway.app/health

# 查询
curl -X POST https://your-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the late policy?", "prompt_name": "ta_friendly"}'
```

## 限流策略

- `/query` 端点: 10 次/分钟/IP
- 超限返回 429 状态码和友好提示信息

## 已知问题和注意事项

1. **索引文件**: 约 4.3MB，直接提交到 Git 仓库
2. **Sentry DSN**: 如果包含 "xxx" 会跳过初始化（避免占位符报错）
3. **API Key 安全**: 永远不要提交真实 API Key 到代码仓库

## 更新索引

如需更新课程内容索引：
```bash
# 1. 爬取网站
python crawler/crawl_site.py

# 2. 重建索引
python indexer/build_index.py
```

## 维护者

- 项目创建于 2025-01-28
- 使用 Claude Code 辅助开发
