"""
Web Scraper Tool for ADK Agents.

Wraps the WebScraper utility as an ADK FunctionTool for use by agents.
"""

from src.utils.web_scraper import WebScraper
import asyncio
import sys
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path for imports BEFORE importing src modules
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Now we can import from src


def _run_async_in_thread(coro):
    """Run an async coroutine in a separate thread with its own event loop."""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run)
        return future.result()


def scrape_urls(urls: List[str], max_content_length: int = 5000) -> Dict[str, Any]:
    """
    Scrape content from one or more URLs.

    This tool fetches and extracts the main content from web pages.
    Use this when you need to gather detailed information from specific URLs
    that were found through search or provided by the user.

    Args:
        urls: List of URLs to scrape (max 5 URLs per call)
        max_content_length: Maximum characters of content to return per URL (default 5000)

    Returns:
        Dictionary containing:
        - results: List of scraped page data with url, title, content, success status
        - stats: Summary statistics (successful/failed counts, total content)
        - errors: List of any errors encountered
    """
    # Limit URLs to prevent excessive scraping
    urls = urls[:5]

    config = {
        "REQUEST_TIMEOUT": 30,
        "MAX_CONCURRENT_REQUESTS": 3,
        "USER_AGENT": "Mozilla/5.0 (compatible; OdysseyEngine/1.0; Research Bot)",
        "MAX_LINKS_PER_PAGE": 10,
    }

    scraper = WebScraper(config)

    try:
        # Run async scraping in a separate thread to avoid event loop conflicts
        scraped_pages = _run_async_in_thread(
            scraper.scrape_multiple_urls(urls))
    except Exception as e:
        return {
            "results": [],
            "stats": {"total_pages": 0, "successful_scrapes": 0, "failed_scrapes": len(urls)},
            "errors": [{"url": url, "error": str(e)} for url in urls]
        }

    # Format results
    results = []
    errors = []

    for page in scraped_pages:
        if page.success:
            # Truncate content to max length
            content = page.content[:max_content_length]
            if len(page.content) > max_content_length:
                content += f"\n... [truncated, {len(page.content) - max_content_length} more chars]"

            results.append({
                "url": page.url,
                "title": page.title,
                "content": content,
                "metadata": page.metadata,
                "success": True
            })
        else:
            errors.append({
                "url": page.url,
                "error": page.error
            })

    stats = scraper.get_scraping_stats(scraped_pages)

    return {
        "results": results,
        "stats": {
            "total_pages": stats["total_pages"],
            "successful_scrapes": stats["successful_scrapes"],
            "failed_scrapes": stats["failed_scrapes"],
            "success_rate": stats["success_rate"]
        },
        "errors": errors
    }


def scrape_single_url(url: str, max_content_length: int = 10000) -> Dict[str, Any]:
    """
    Scrape content from a single URL with more detail.

    Use this for deep scraping of a single important page where you need
    more content than the multi-URL scraper provides.

    Args:
        url: The URL to scrape
        max_content_length: Maximum characters of content to return (default 10000)

    Returns:
        Dictionary containing:
        - url: The scraped URL
        - title: Page title
        - content: Extracted main content
        - links: Relevant links found on the page
        - metadata: Page metadata (description, author, date, etc.)
        - success: Whether scraping succeeded
        - error: Error message if failed
    """
    config = {
        "REQUEST_TIMEOUT": 45,
        "MAX_CONCURRENT_REQUESTS": 1,
        "USER_AGENT": "Mozilla/5.0 (compatible; OdysseyEngine/1.0; Research Bot)",
        "MAX_LINKS_PER_PAGE": 20,
    }

    scraper = WebScraper(config)

    try:
        # Run async scraping in a separate thread to avoid event loop conflicts
        page = _run_async_in_thread(scraper.scrape_page(url))
    except Exception as e:
        return {
            "url": url,
            "title": "",
            "content": "",
            "links": [],
            "metadata": {},
            "success": False,
            "error": str(e)
        }

    if page is None:
        return {
            "url": url,
            "title": "",
            "content": "",
            "links": [],
            "metadata": {},
            "success": False,
            "error": "Failed to scrape page"
        }

    # Truncate content
    content = page.content[:max_content_length]
    if len(page.content) > max_content_length:
        content += f"\n... [truncated, {len(page.content) - max_content_length} more chars]"

    return {
        "url": page.url,
        "title": page.title,
        "content": content,
        "links": page.links[:10],  # Limit links returned
        "metadata": page.metadata,
        "success": page.success,
        "error": page.error
    }
