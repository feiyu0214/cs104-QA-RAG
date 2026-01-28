# indexer/download_site_pdfs.py
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

URL_PATH = "data/raw/site_urls.json"
OUT_DIR = "docs/website_pdfs"

# 可选：只允许同一站点域名（推荐，避免误抓外链）
ALLOWED_NETLOCS = {"bytes.usc.edu"}

# 超时与重试参数
TIMEOUT = 25
SLEEP = 0.2  # polite crawl


def normalize_url(u: str) -> str:
    """Remove fragments, normalize trailing slash for paths, keep query (some sites use it)."""
    u, _ = urldefrag(u)
    return u.strip()


def is_probably_pdf_url(u: str) -> bool:
    path = urlparse(u).path.lower()
    return path.endswith(".pdf")


def head_says_pdf(u: str, session: requests.Session) -> bool:
    """Fallback: check Content-Type via HEAD (some pdf links don't end with .pdf)."""
    try:
        r = session.head(u, allow_redirects=True, timeout=TIMEOUT)
        ctype = (r.headers.get("Content-Type") or "").lower()
        return "application/pdf" in ctype
    except Exception:
        return False


def safe_filename_from_url(u: str) -> str:
    """Create a stable filename, avoid collisions."""
    p = urlparse(u)
    base = os.path.basename(p.path)
    if not base:
        base = "download.pdf"
    # If missing .pdf but is pdf content, append
    if not base.lower().endswith(".pdf"):
        base += ".pdf"

    # Add a short hash-ish suffix from path/query to avoid collisions
    suffix_src = (p.path + ("?" + p.query if p.query else "")).encode("utf-8", errors="ignore")
    suffix = str(abs(hash(suffix_src)) % (10**8))
    name, ext = os.path.splitext(base)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80]
    return f"{name}__{suffix}{ext}"


def extract_pdf_links_from_page(page_url: str, html: str, session: requests.Session) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    pdfs: set[str] = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue

        abs_url = normalize_url(urljoin(page_url, href))
        netloc = urlparse(abs_url).netloc

        # optional domain filter
        if ALLOWED_NETLOCS and netloc and netloc not in ALLOWED_NETLOCS:
            continue

        if is_probably_pdf_url(abs_url) or head_says_pdf(abs_url, session):
            pdfs.add(abs_url)

    return pdfs


def download_pdf(url: str, out_dir: str, session: requests.Session) -> str | None:
    os.makedirs(out_dir, exist_ok=True)
    filename = safe_filename_from_url(url)
    out_path = os.path.join(out_dir, filename)

    # 用于写 pdf_map.json 的“相对 key”
    # out_dir = "docs/website_pdfs" -> key = "website_pdfs/<filename>"
    rel_key = os.path.join(os.path.basename(out_dir), filename)

    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return rel_key

    try:
        r = session.get(url, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type") or "").lower()
        # 防止下载到 html 错页
        if ("application/pdf" not in ctype) and (not is_probably_pdf_url(url)):
            return None

        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        return rel_key
    except Exception as e:
        print(f"[warn] failed to download {url}: {e}")
        return None


def main():
    with open(URL_PATH, "r") as f:
        page_urls = json.load(f)

    page_urls = list(dict.fromkeys(normalize_url(u) for u in page_urls))  # keep order, dedupe
    print(f"Scanning {len(page_urls)} pages for PDF links...")

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "CS104-QA-RAG/1.0 (pdf collector; contact course staff if needed)"}
    )

    all_pdfs: set[str] = set()
    for i, page_url in enumerate(page_urls, 1):
        try:
            r = session.get(page_url, timeout=TIMEOUT)
            r.raise_for_status()
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "text/html" not in ctype:
                continue
            pdfs = extract_pdf_links_from_page(page_url, r.text, session)
            if pdfs:
                print(f"[{i}/{len(page_urls)}] {page_url} -> {len(pdfs)} pdf links")
                all_pdfs |= pdfs
        except Exception as e:
            print(f"[warn] failed to fetch {page_url}: {e}")
        time.sleep(SLEEP)

    print(f"Found {len(all_pdfs)} unique PDF URLs. Downloading to {OUT_DIR} ...")

    ok = 0
    pdf_map = {}  # ⭐ local_rel_key -> original_pdf_url

    for url in sorted(all_pdfs):
        rel_key = download_pdf(url, OUT_DIR, session)  # ⭐ 现在 download_pdf 返回 website_pdfs/<filename>.pdf
        if rel_key:
            ok += 1
            pdf_map[rel_key] = url  # ⭐ 记录映射
            print("  saved:", rel_key)
        time.sleep(SLEEP)

    # ⭐ 写出映射表
    os.makedirs("data/processed", exist_ok=True)
    pdf_map_path = "data/processed/pdf_map.json"
    with open(pdf_map_path, "w") as f:
        json.dump(pdf_map, f, indent=2)

    print(f"Done. Downloaded {ok}/{len(all_pdfs)} PDFs.")
    print(f"Wrote mapping to {pdf_map_path} ({len(pdf_map)} entries).")



if __name__ == "__main__":
    main()
