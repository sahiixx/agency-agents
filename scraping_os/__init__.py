"""
scraping_os — Unified Web Scraping Operating System for The Agency.

Wraps Crawlee (Apify) and Scrapling (D4Vinci) with a single API,
proxy rotation, and job queue management.

Usage:
    from scraping_os import UnifiedCrawler, ProxyManager, JobQueue

    proxies = ProxyManager()
    proxies.load_from_file("proxies.txt")

    crawler = UnifiedCrawler(engine="auto", proxy_manager=proxies)
    crawler.run("https://example.com", selector=".product")
    crawler.export("results.json")
"""

from .proxy_manager import ProxyManager
from .job_queue import JobQueue
from .unified_crawler import UnifiedCrawler

__all__ = ["ProxyManager", "JobQueue", "UnifiedCrawler"]
__version__ = "1.0.0"
