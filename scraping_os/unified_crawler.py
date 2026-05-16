#!/usr/bin/env python3
"""
scraping_os/unified_crawler.py — Single API for Crawlee and Scrapling.

Automatically selects the best engine based on requirements:
  - Need queues + storage? → Crawlee
  - Need stealth + adaptive? → Scrapling
  - Not sure? → Auto-select

Usage:
    from scraping_os import UnifiedCrawler, ProxyManager

    crawler = UnifiedCrawler(engine="auto", headless=True)
    results = crawler.run("https://example.com", selector=".product")
    crawler.export("products.json")
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Callable

from .proxy_manager import ProxyManager


class UnifiedCrawler:
    """
    Unified crawler that wraps both Crawlee and Scrapling.

    Args:
        engine: "crawlee", "scrapling", or "auto"
        proxy_manager: ProxyManager instance for rotation
        headless: Run browser in headless mode
        max_requests: Maximum requests per crawl
        output_dir: Where to save results
    """

    def __init__(
        self,
        engine: str = "auto",
        proxy_manager: ProxyManager | None = None,
        headless: bool = True,
        max_requests: int = 50,
        output_dir: str = "data/scraped",
    ):
        self.engine = engine
        self.proxy_manager = proxy_manager
        self.headless = headless
        self.max_requests = max_requests
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._data: list[dict] = []
        self._handlers: list[Callable] = []

    def on_data(self, handler: Callable[[dict], None]) -> "UnifiedCrawler":
        """Register a callback for each scraped item."""
        self._handlers.append(handler)
        return self

    def _emit(self, item: dict):
        self._data.append(item)
        for h in self._handlers:
            h(item)

    def run(self, url: str, selector: str | None = None, **kwargs) -> list[dict]:
        """
        Run a crawl.

        Returns list of scraped items. Actual execution depends on installed libraries.
        """
        selected_engine = self._select_engine(url, kwargs)
        print(f"[ScrapingOS] Engine: {selected_engine} | URL: {url}")

        if selected_engine == "scrapling":
            return self._run_scrapling(url, selector, **kwargs)
        else:
            return self._run_crawlee(url, selector, **kwargs)

    def _select_engine(self, url: str, kwargs: dict) -> str:
        if self.engine != "auto":
            return self.engine
        # Auto-select logic
        if kwargs.get("stealth") or kwargs.get("cloudflare"):
            return "scrapling"
        if kwargs.get("adaptive"):
            return "scrapling"
        if kwargs.get("queue") or kwargs.get("enqueue_links"):
            return "crawlee"
        return "scrapling"  # Default to scrapling for simplicity

    def _run_scrapling(self, url: str, selector: str | None, **kwargs) -> list[dict]:
        """Execute via Scrapling if available."""
        try:
            from scrapling.fetchers import StealthyFetcher

            proxy_url = self.proxy_manager.next_url() if self.proxy_manager else None

            fetch_kwargs = {"headless": self.headless}
            if proxy_url:
                fetch_kwargs["proxy"] = proxy_url

            page = StealthyFetcher.fetch(url, **fetch_kwargs)

            if selector:
                items = page.css(selector, auto_save=kwargs.get("auto_save", True))
                for item in items:
                    data = {"_source": url, "_timestamp": time.time()}
                    # Try common extraction patterns
                    for field in ["title", "name", "price", "url", "image"]:
                        val = item.css(f".{field}::text").get() or item.css(f"[class*='{field}']::text").get()
                        if val:
                            data[field] = val.strip()
                    # Get href if anchor
                    href = item.css("a::attr(href)").get()
                    if href:
                        data["link"] = href
                    self._emit(data)
            else:
                # Full page scrape
                self._emit({
                    "_source": url,
                    "_timestamp": time.time(),
                    "title": page.css("title::text").get(),
                    "html_length": len(page.text),
                })

            return self._data

        except ImportError:
            print("[ScrapingOS] Scrapling not installed. Install: pip install scrapling")
            return []
        except Exception as e:
            print(f"[ScrapingOS] Scrapling error: {e}")
            return []

    def _run_crawlee(self, url: str, selector: str | None, **kwargs) -> list[dict]:
        """Execute via Crawlee if available."""
        try:
            import asyncio
            from crawlee.beautifulsoup_crawler import BeautifulSoupCrawler, BeautifulSoupCrawlingContext

            results: list[dict] = []

            async def _crawl():
                crawler = BeautifulSoupCrawler(max_requests_per_crawl=self.max_requests)

                @crawler.router.default_handler
                async def handler(context: BeautifulSoupCrawlingContext) -> None:
                    context.log.info(f"Processing {context.request.url}")
                    if selector:
                        for item in context.soup.select(selector):
                            data = {
                                "_source": context.request.url,
                                "_timestamp": time.time(),
                                "text": item.get_text(strip=True),
                            }
                            results.append(data)
                            self._emit(data)
                    else:
                        data = {
                            "_source": context.request.url,
                            "_timestamp": time.time(),
                            "title": context.soup.title.string if context.soup.title else None,
                        }
                        results.append(data)
                        self._emit(data)
                    await context.enqueue_links()

                await crawler.run([url])

            asyncio.run(_crawl())
            return results

        except ImportError:
            print("[ScrapingOS] Crawlee not installed. Install: pip install crawlee")
            return []
        except Exception as e:
            print(f"[ScrapingOS] Crawlee error: {e}")
            return []

    def export(self, filename: str = "results.json") -> Path:
        """Export scraped data to JSON."""
        path = self.output_dir / filename
        path.write_text(json.dumps(self._data, indent=2, default=str), encoding="utf-8")
        print(f"[ScrapingOS] Exported {len(self._data)} items to {path}")
        return path

    def preview(self, limit: int = 5) -> list[dict]:
        """Preview first N items."""
        return self._data[:limit]

    def stats(self) -> dict[str, Any]:
        """Crawl statistics."""
        return {
            "items_scraped": len(self._data),
            "engine_used": self.engine,
            "output_dir": str(self.output_dir),
        }
