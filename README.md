# CS104 QA RAG

A local RAG (Retrieval-Augmented Generation) system for CS104 course Q&A.

## Requirements

- Python 3.10+
- OpenAI API Key

```bash
pip install llama-index llama-index-llms-openai llama-index-embeddings-openai \
            llama-index-readers-web requests beautifulsoup4 fastapi uvicorn
```

Set your API key:
```bash
export OPENAI_API_KEY="sk-..."
```

## Usage

### 1. Crawl Website

Crawl CS104 course website to get all page URLs:

```bash
cd crawler
python crawl_site.py
```

Output: `data/raw/site_urls.json`

### 2. Download PDFs

Download all PDFs linked from the course website:

```bash
cd indexer
python download_site_pdfs.py
```

Output: `docs/website_pdfs/` and `data/processed/pdf_map.json`

### 3. Build Index

Build vector index from web pages and PDFs:

```bash
cd indexer
python build_index.py
```

Output: `data/processed/index/`

### 4. Run

#### Terminal Mode

```bash
cd app
python rag_query.py
```

Type your question and press Enter. Type `quit` to exit.

#### Web Mode

Start server:
```bash
uvicorn app.api:app --reload --port 8000
```

Open browser: http://localhost:8000

Stop server: `kill $(lsof -t -i :8000)`

## Project Structure

```
cs104-QA-RAG/
├── crawler/          # Web crawling
├── indexer/          # PDF download & index building
├── app/              # RAG query & API server
├── prompt/           # Prompt templates
├── web/              # Web UI
├── docs/             # PDF documents
└── data/             # Crawled URLs & vector index
```
