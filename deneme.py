#!/usr/bin/env python3
"""
TÜBİTAK Dinamik Recursive Crawler (Playwright + Chrome)
- Chrome üzerinde açılır, gezinmeleri canlı görebilirsin
- Alt linkleri recursive tarar
- PDF/dokümanları indirir
- Metinleri .txt olarak kaydeder
"""

import os
import time
from urllib.parse import urljoin, urlparse, urldefrag
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

USER_AGENT = "Mozilla/5.0 (compatible; MyCrawler/1.0)"
HEADERS = {"User-Agent": USER_AGENT}
PDF_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip")

# ------------------- Helper Functions -------------------

def normalize_url(base, href):
    if not href:
        return None
    href = href.strip()
    href, _ = urldefrag(href)  # fragment kaldır
    return urljoin(base, href)

def same_domain(a, b):
    return urlparse(a).netloc == urlparse(b).netloc

def is_probably_file(url):
    return url.lower().endswith(PDF_EXTENSIONS)

def safe_filename(url):
    return urlparse(url).path.replace("/", "_").strip("_") or "downloaded_file"

def download_file(url, out_dir):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        if r.status_code == 200:
            filename = safe_filename(url)
            path = Path(out_dir) / filename
            i = 1
            while path.exists():
                path = Path(out_dir) / f"{path.stem}_{i}{path.suffix}"
                i += 1
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            print(f"[DOWNLOADED] {url} -> {path}")
    except Exception as e:
        print(f"[ERROR] downloading {url}: {e}")

def save_text(content, url, out_dir):
    try:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        filename = safe_filename(url) + ".txt"
        path = Path(out_dir) / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[TEXT SAVED] {url} -> {path}")
    except Exception as e:
        print(f"[ERROR] saving text from {url}: {e}")

def extract_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for tag in soup.find_all(["a", "link", "iframe", "area"]):
        href = tag.get("href") or tag.get("src")
        full = normalize_url(base_url, href)
        if full:
            links.add(full)
    for tag in soup.find_all(["embed", "object"]):
        src = tag.get("data") or tag.get("src")
        full = normalize_url(base_url, src)
        if full:
            links.add(full)
    return links

# ------------------- Crawler -------------------

class Crawler:
    def __init__(self, start_url, out_dir="tubitak_data", max_depth=3, rate_limit=1.0):
        self.start_url = start_url
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.max_depth = max_depth
        self.visited = set()
        self.rate_limit = rate_limit
        self.allowed_domain = urlparse(start_url).netloc

    def crawl(self, browser, url, depth=0):
        if depth > self.max_depth or url in self.visited:
            return
        self.visited.add(url)
        time.sleep(self.rate_limit)

        try:
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": USER_AGENT})
            print(f"[VISIT] {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            html = page.content()
            page.close()

            # Metni kaydet
            save_text(html, url, self.out_dir)

            # Linkleri çıkar
            links = extract_links(url, html)
            for link in links:
                if not same_domain(self.start_url, link):
                    continue
                if is_probably_file(link):
                    download_file(link, self.out_dir)
                else:
                    self.crawl(browser, link, depth + 1)

        except Exception as e:
            print(f"[ERROR] visiting {url}: {e}")

    def run(self):
        with sync_playwright() as p:
            # Chrome aç, canlı izleyebilirsin
            browser = p.chromium.launch(headless=False, channel="chrome", slow_mo=500)
            self.crawl(browser, self.start_url, 0)
            browser.close()

# ------------------- CLI -------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="Başlangıç URL")
    parser.add_argument("--out", default="tubitak_data", help="Çıktı klasörü")
    parser.add_argument("--depth", type=int, default=2, help="Maksimum derinlik")
    parser.add_argument("--rate", type=float, default=1.0, help="Bekleme (saniye)")
    args = parser.parse_args()

    crawler = Crawler(start_url=args.start, out_dir=args.out, max_depth=args.depth, rate_limit=args.rate)
    crawler.run()
    print("Tarama tamamlandı.")
