"""Proxy rotation service for web scraping."""
import random
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class ProxyRotator:
    def __init__(self, proxies: Optional[List[str]] = None):
        self._proxies = list(proxies) if proxies else []
        self._index = 0

    def add_proxy(self, proxy_url: str):
        self._proxies.append(proxy_url)

    def get_next(self) -> Optional[str]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy

    def get_random(self) -> Optional[str]:
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def mark_bad(self, proxy_url: str):
        if proxy_url in self._proxies:
            self._proxies.remove(proxy_url)
            logger.warning(f"Removed bad proxy: {proxy_url}")

    @property
    def available_count(self) -> int:
        return len(self._proxies)


proxy_rotator = ProxyRotator()
