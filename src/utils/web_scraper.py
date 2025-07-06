"""
Web Scraper for Odyssey Engine.

This module handles web scraping with depth limits and intelligent content extraction.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
import time
import logging
from dataclasses import dataclass


@dataclass
class ScrapedPage:
    """Container for scraped page data."""
    url: str
    title: str
    content: str
    links: List[str]
    metadata: Dict[str, Any]
    scrape_time: float
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ScrapedPage to JSON-serializable dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "links": self.links,
            "metadata": self.metadata,
            "scrape_time": self.scrape_time,
            "success": self.success,
            "error": self.error
        }


class WebScraper:
    """Intelligent web scraper with depth limits and content extraction."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the web scraper."""
        self.config = config
        self.user_agent = config.get("USER_AGENT", "Mozilla/5.0 (compatible; OdysseyEngine/1.0)")
        self.timeout = config.get("REQUEST_TIMEOUT", 30)
        self.max_concurrent = config.get("MAX_CONCURRENT_REQUESTS", 5)
        self.delay_between_requests = 1.0  # Be respectful to servers
        
        # Content filters
        self.min_content_length = 100
        self.max_content_length = 50000
        
        # Blocked domains/extensions
        self.blocked_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.tar', '.gz']
        self.blocked_domains = ['facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com']
        
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={'User-Agent': self.user_agent},
            connector=aiohttp.TCPConnector(limit=self.max_concurrent)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_page(self, url: str) -> Optional[ScrapedPage]:
        """
        Scrape a single page and extract content.
        
        Args:
            url: URL to scrape
            
        Returns:
            ScrapedPage object or None if scraping failed
        """
        if not self._is_scrapeable_url(url):
            return ScrapedPage(
                url=url,
                title="",
                content="",
                links=[],
                metadata={},
                scrape_time=0,
                success=False,
                error="URL blocked or invalid"
            )
        
        start_time = time.time()
        
        try:
            # Ensure session is available
            if not self.session:
                await self.__aenter__()
            
            # Respect rate limiting
            await asyncio.sleep(self.delay_between_requests)
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return ScrapedPage(
                        url=url,
                        title="",
                        content="",
                        links=[],
                        metadata={"status_code": response.status},
                        scrape_time=time.time() - start_time,
                        success=False,
                        error=f"HTTP {response.status}"
                    )
                
                html_content = await response.text()
                
                # Parse content
                parsed_data = self._parse_html_content(html_content, url)
                
                return ScrapedPage(
                    url=url,
                    title=parsed_data["title"],
                    content=parsed_data["content"],
                    links=parsed_data["links"],
                    metadata=parsed_data["metadata"],
                    scrape_time=time.time() - start_time,
                    success=True
                )
                
        except asyncio.TimeoutError:
            return ScrapedPage(
                url=url,
                title="",
                content="",
                links=[],
                metadata={},
                scrape_time=time.time() - start_time,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            return ScrapedPage(
                url=url,
                title="",
                content="",
                links=[],
                metadata={},
                scrape_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def _is_scrapeable_url(self, url: str) -> bool:
        """Check if URL is scrapeable."""
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check domain blocks
            domain = parsed.netloc.lower()
            for blocked_domain in self.blocked_domains:
                if blocked_domain in domain:
                    return False
            
            # Check file extension blocks
            path = parsed.path.lower()
            for blocked_ext in self.blocked_extensions:
                if path.endswith(blocked_ext):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _parse_html_content(self, html: str, base_url: str) -> Dict[str, Any]:
        """Parse HTML content and extract useful information."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Extract main content
        content = self._extract_main_content(soup)
        
        # Extract links
        links = self._extract_links(soup, base_url)
        
        # Extract metadata
        metadata = self._extract_metadata(soup)
        
        return {
            "title": title,
            "content": content,
            "links": links,
            "metadata": metadata
        }
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from parsed HTML."""
        # Try to find main content containers
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.content',
            '.main-content',
            '.article-content',
            '.post-content',
            '#content',
            '#main'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # Fallback to body if no main content found
        if not main_content:
            main_content = soup.find('body')
        
        if not main_content:
            return ""
        
        # Extract text content
        text_content = main_content.get_text(separator=' ', strip=True)
        
        # Clean up the text
        text_content = self._clean_text_content(text_content)
        
        return text_content
    
    def _clean_text_content(self, text: str) -> str:
        """Clean extracted text content."""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove very short lines (likely navigation elements)
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        
        text = '\n'.join(cleaned_lines)
        
        # Limit content length
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length] + "..."
        
        return text.strip()
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and normalize links from the page."""
        links = []
        
        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href']
            
            # Normalize relative URLs
            full_url = urljoin(base_url, href)
            
            # Filter out non-HTTP(S) links
            if not full_url.startswith(('http://', 'https://')):
                continue
            
            # Filter out anchor links to same page
            parsed_base = urlparse(base_url)
            parsed_link = urlparse(full_url)
            
            if (parsed_base.netloc == parsed_link.netloc and 
                parsed_base.path == parsed_link.path and 
                parsed_link.fragment):
                continue
            
            # Check if link is scrapeable
            if self._is_scrapeable_url(full_url):
                links.append(full_url)
        
        # Remove duplicates and limit count
        unique_links = list(set(links))
        return unique_links[:self.config.get("MAX_LINKS_PER_PAGE", 20)]  # Configurable limit to prevent explosion
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from the page."""
        metadata = {}
        
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content')
            
            if name and content:
                metadata[name] = content
        
        # Extract specific useful metadata
        useful_meta = {}
        
        # Description
        description = (metadata.get('description') or 
                      metadata.get('og:description') or 
                      metadata.get('twitter:description'))
        if description:
            useful_meta['description'] = description
        
        # Author
        author = (metadata.get('author') or 
                 metadata.get('article:author'))
        if author:
            useful_meta['author'] = author
        
        # Publication date
        pub_date = (metadata.get('article:published_time') or 
                   metadata.get('datePublished') or
                   metadata.get('date'))
        if pub_date:
            useful_meta['published_date'] = pub_date
        
        # Keywords
        keywords = metadata.get('keywords')
        if keywords:
            useful_meta['keywords'] = keywords
        
        return useful_meta
    
    async def scrape_multiple_urls(self, urls: List[str]) -> List[ScrapedPage]:
        """Scrape multiple URLs concurrently."""
        async with self:
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def scrape_with_semaphore(url):
                async with semaphore:
                    return await self.scrape_page(url)
            
            tasks = [scrape_with_semaphore(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and None results
            scraped_pages = []
            for result in results:
                if isinstance(result, ScrapedPage):
                    scraped_pages.append(result)
                elif isinstance(result, Exception):
                    logging.error(f"Scraping error: {result}")
            
            return scraped_pages
    
    def get_scraping_stats(self, scraped_pages: List[ScrapedPage]) -> Dict[str, Any]:
        """Get statistics about scraping results."""
        successful = [page for page in scraped_pages if page.success]
        failed = [page for page in scraped_pages if not page.success]
        
        total_content_length = sum(len(page.content) for page in successful)
        avg_scrape_time = sum(page.scrape_time for page in scraped_pages) / len(scraped_pages) if scraped_pages else 0
        
        return {
            "total_pages": len(scraped_pages),
            "successful_scrapes": len(successful),
            "failed_scrapes": len(failed),
            "success_rate": len(successful) / len(scraped_pages) if scraped_pages else 0,
            "total_content_length": total_content_length,
            "average_scrape_time": avg_scrape_time,
            "errors": [{"url": page.url, "error": page.error} for page in failed]
        }
