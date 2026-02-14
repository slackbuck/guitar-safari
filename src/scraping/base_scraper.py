import logging

import requests
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

class BaseScraper():
    """Base class for web scrapers."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.cache = dict()

    def parse_html(self, html_content) -> BeautifulSoup:
        """Parses HTML content and returns a BeautifulSoup object."""
        return BeautifulSoup(html_content, "lxml")
    
    def get_base_url(self, html_content) -> str | None:
        """Extracts the base URL from the HTML content if a <base> tag is present."""
        soup = self.parse_html(html_content)
        base_tag = soup.find('base')
        if base_tag and base_tag.get('href'):
            return base_tag['href']
        return None

    def fetch_page(
            self,
            url,
            base_url=None,
            cache_content=True, 
            use_cached=True
        ) -> BeautifulSoup | None:
        """Fetches a webpage and returns its HTML content as a BeautifulSoup object."""
        if base_url is None:
            base_url = self.base_url
        full_url = urljoin(base_url, url)
        if use_cached and self.cache.get(full_url):
            logging.info(
                "Using cached page from %s",
                full_url
            )
            return self.cache[full_url]
        try:
            response = requests.get(full_url)
            response.raise_for_status()
            parsed_html = self.parse_html(response.text)
            if cache_content:
                self.cache[full_url] = parsed_html
            return parsed_html
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_links(
            self,
            soup: BeautifulSoup,
            check_func: callable,
            base_url: str | None = None,
        ) -> list[str]:
        """
        Extracts full URLs from <a> tags in a BeautifulSoup object where check_func(href) is True.

        Args:
            soup: BeautifulSoup object of the HTML.
            base_url: Base URL string.
            check_func: Callable that takes href (str) and returns bool.

        Returns:
            List of full URLs.

        Example Usage:
            check_func = lambda href: href.startswith("match_pattern")
            links = extract_links(soup, base_url, check_func)

        """
        if base_url is None:
            base_url = self.base_url
        links = []
        for a in soup.find_all('a', href=True):
            if check_func(a['href']):
                full_url = urljoin(base_url, a['href'])
                links.append(full_url)
        return links
        """
        Extracts full URLs from <a> tags in soup where check_func(href) is True.
        
        Args:
            soup: BeautifulSoup object of the HTML.
            base_url: Base URL string.
            check_func: Callable that takes href (str) and returns bool.
        
        Returns:
            List of full URLs.
        
        Example Usage:
            check_func = lambda href: href.startswith("match_pattern")
            links = extract_links(soup, base_url, check_func)

        """
        links = []
        for a in soup.find_all('a', href=True):
            if check_func(a['href']):
                full_url = urljoin(base_url, a['href'])
                links.append(full_url)
        return links