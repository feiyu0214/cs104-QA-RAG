# crawler/crawl_site.py
import json
from crawl_utils import crawl_course_site
import os

seed = "https://bytes.usc.edu/cs104/"
urls = crawl_course_site(seed)

os.makedirs("data/raw", exist_ok=True)
with open("data/raw/site_urls.json", "w") as f:
    json.dump(urls, f, indent=2)

print(f"Crawled {len(urls)} pages.")
