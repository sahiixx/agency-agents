"""
Crawler Tool for Agency OS
Executes crawls via the unified_crawler module and reports results back.
"""
import os
import sys
import json
import argparse
from pathlib import Path

# Add scraping_os to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scraping_os"))

from unified_crawler import UnifiedCrawler
from proxy_manager import ProxyManager


def run_crawl(url: str, engine: str = "auto", selector: str = None, proxy: dict = None):
    crawler = UnifiedCrawler(engine=engine)
    if proxy:
        crawler.set_proxy(proxy)
    
    print(f"[CRAWLER] Starting crawl: {url} (engine={engine})", flush=True)
    result = crawler.run(url, selector=selector)
    print(f"[CRAWLER] Extracted {len(result)} items", flush=True)
    
    return {
        "url": url,
        "engine": engine,
        "count": len(result),
        "items": result[:50],  # Limit output
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agency OS Crawler Tool")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--engine", default="auto", help="Crawl engine")
    parser.add_argument("--selector", default=None, help="CSS selector")
    parser.add_argument("--proxy", default=None, help="Proxy JSON")
    args = parser.parse_args()
    
    proxy = json.loads(args.proxy) if args.proxy else None
    result = run_crawl(args.url, args.engine, args.selector, proxy)
    print(json.dumps(result, indent=2, default=str))
