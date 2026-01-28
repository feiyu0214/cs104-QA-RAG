# crawler/crawl_utils.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

ALLOWED_PREFIXES = [
    "/cs104/syllabus",
    "/cs104/schedule",
    "/cs104/homework",
    "/cs104/labs",
    "/cs104/wiki",
    "/cs104/resources",
    "/cs104/staff",
    "/cs104/help",
]

def crawl_course_site(seed_url, max_pages=120):
    domain = urlparse(seed_url).netloc
    seen, queue = set(), [seed_url]
    urls = []

    while queue and len(urls) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            if "text/html" not in r.headers.get("Content-Type", ""):
                continue
        except Exception:
            continue

        urls.append(url)

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href]"):
            nxt = urljoin(url, a["href"])
            p = urlparse(nxt)

            if p.netloc != domain:
                continue
            if not any(p.path.startswith(pref) for pref in ALLOWED_PREFIXES):
                continue

            nxt = nxt.split("#")[0]
            if nxt not in seen:
                queue.append(nxt)

    return urls
