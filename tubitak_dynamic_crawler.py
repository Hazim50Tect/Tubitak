#!/usr/bin/env python3
"""
TÜBİTAK Çağrı Crawler (Filtreli)
- Ana sayfa: sadece 'block-feza-gursey-views-block-cagrilar-block-2' altındaki linkleri alır
- Alt sayfalar: sadece <article> içindeki
  class='field field--name-field-bilesenler ... field__items' div altındaki linkleri takip eder
- PDF/Word/Excel gibi dosyaları indirir
- mailto: linkleri atlar
- Recursive çalışır
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
DOC_EXTENSIONS = (".pdf") # , ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".jpg"

# ------------------- Log Helper -------------------

def log(message, logfile="crawler.log"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ------------------- File Helpers -------------------

def normalize_url(base, href):
    if not href:
        return None
    href = href.strip()
    if href.startswith("mailto:"):
        return None
    href, _ = urldefrag(href)
    return urljoin(base, href)

def is_document(url):
    return url.lower().endswith(DOC_EXTENSIONS)

def url_to_path(url, base_dir):
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path.strip("/")
    if not path:
        path = "root"
    folder = Path(base_dir) / domain / path
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def download_file(url, folder):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        if r.status_code == 200:
            filename = os.path.basename(urlparse(url).path) or "downloaded_file"
            path = folder / filename
            i = 1
            while path.exists():
                path = folder / f"{path.stem}_{i}{path.suffix}"
                i += 1
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            log(f"[DOWNLOAD] {url} -> {path}")
    except Exception as e:
        log(f"[ERROR] downloading {url}: {e}")

def save_text(content, url, folder):
    try:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        path = folder / "index.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        log(f"[TEXT] {url} -> {path}")
    except Exception as e:
        log(f"[ERROR] saving text from {url}: {e}")

# ------------------- Crawler -------------------

class Crawler:
    def __init__(self, start_url, out_dir="tubitak_data", max_depth=3, rate_limit=1.0):
        self.start_url = start_url
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.max_depth = max_depth
        self.visited = set()
        self.rate_limit = rate_limit
        open("crawler.log", "w").close()

    def extract_links_from_article(self, base_url, html):
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article")
        if not article:
            return []
        div = article.find(
            "div",
            class_="field field--name-field-bilesenler field--type-entity-reference-revisions field--label-hidden field__items"
        )
        if not div:
            return []
        links = set()
        for tag in div.find_all("a", href=True):
            full = normalize_url(base_url, tag["href"])
            if full:
                links.add(full)
        return links

    def crawl_page(self, browser, url, depth=0):
        if depth > self.max_depth or url in self.visited:
            return
        self.visited.add(url)
        time.sleep(self.rate_limit)

        try:
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": USER_AGENT})
            log(f"[VISIT] {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            html = page.content()
            page.close()

            folder = url_to_path(url, self.out_dir)
            save_text(html, url, folder)

            links = self.extract_links_from_article(url, html)
            for link in links:
                if is_document(link):
                    download_file(link, folder)
                else:
                    self.crawl_page(browser, link, depth + 1)

        except Exception as e:
            log(f"[ERROR] visiting {url}: {e}")

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, channel="chrome", slow_mo=500)

            # 1) Ana sayfadan sadece ilgili DIV'deki linkleri topla
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": USER_AGENT})
            page.goto(self.start_url, wait_until="networkidle", timeout=60000)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            div = soup.find("div", id="block-feza-gursey-views-block-cagrilar-block-2")
            if not div:
                log("[ERROR] İlgili div bulunamadı!")
                return
            links = [normalize_url(self.start_url, a.get("href")) for a in div.find_all("a") if a.get("href")]
            page.close()

            # 2) Bu linkleri gez
            for link in links:
                self.crawl_page(browser, link, depth=0)

            browser.close()

# ------------------- CLI -------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="Başlangıç URL")
    parser.add_argument("--out", default="tubitak_data", help="Çıktı klasörü")
    parser.add_argument("--depth", type=int, default=3, help="Maksimum derinlik")
    parser.add_argument("--rate", type=float, default=1.0, help="Bekleme (saniye)")
    args = parser.parse_args()

    crawler = Crawler(
        start_url=args.start,
        out_dir=args.out,
        max_depth=args.depth,
        rate_limit=args.rate,
    )
    crawler.run()
    log("Tarama tamamlandı.")
