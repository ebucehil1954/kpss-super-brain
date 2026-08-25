"""
KPSS Super-Brain: Ücretsiz Proxy Havuzu ve User-Agent Rotasyon Yöneticisi (Proxy Pool Engine v3)
YouTube IP engellerini (429 Too Many Requests), bot korumalarını ve hız limitlerini aşmak için
ücretsiz proxy havuzlarından dinamik proxy toplar, test eder ve rotasyonla istekleri dağıtır.
"""
import httpx
import random
import time
import asyncio
from typing import List, Dict, Any, Optional
from config import super_brain_config

class ProxyPoolManager:
    # 50+ Modern User-Agent Listesi (Mobil, Masaüstü, Safari, Chrome, Edge, Firefox)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.62 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0"
    ]

    # Ücretsiz Proxy Toplama Kaynakları
    PUBLIC_PROXY_SOURCES = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
    ]

    def __init__(self):
        self.proxies: List[str] = []
        self.working_proxies: List[str] = []
        self.last_fetch_time: float = 0.0
        self.current_index: int = 0
        self._lock = asyncio.Lock()
        self.failed_counts: Dict[str, int] = {}

    def get_random_user_agent(self) -> str:
        """Rastgele modern bir User-Agent döner."""
        return random.choice(self.USER_AGENTS)

    def get_headers(self) -> Dict[str, str]:
        """Anti-bot korumalarını atlatmak için doğal tarayıcı başlıkları oluşturur."""
        return {
            "User-Agent": self.get_random_user_agent(),
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com.tr/",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Upgrade-Insecure-Requests": "1"
        }

    async def fetch_public_proxies(self) -> int:
        """Açık proxy kaynaklarından HTTP/HTTPS proxy listesini günceller."""
        now = time.time()
        # 30 dakikada bir yenile
        if now - self.last_fetch_time < 1800 and len(self.proxies) > 10:
            return len(self.proxies)

        collected = set()
        async with httpx.AsyncClient(timeout=8.0) as client:
            for url in self.PUBLIC_PROXY_SOURCES:
                try:
                    res = await client.get(url, headers={"User-Agent": self.get_random_user_agent()})
                    if res.status_code == 200:
                        lines = res.text.strip().splitlines()
                        for line in lines:
                            line = line.strip()
                            if line and ":" in line and not line.startswith("#"):
                                if not line.startswith("http"):
                                    line = f"http://{line}"
                                collected.add(line)
                except Exception:
                    continue

        self.proxies = list(collected)
        self.last_fetch_time = now
        return len(self.proxies)

    async def test_proxy(self, proxy_url: str) -> bool:
        """Bir proxy'nin YouTube / Google erişimini test eder."""
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=4.0,
                headers={"User-Agent": self.get_random_user_agent()}
            ) as client:
                res = await client.get("https://www.google.com/generate_204")
                return res.status_code in [200, 204]
        except Exception:
            return False

    async def get_next_proxy(self) -> Optional[str]:
        """Sıradaki geçerli proxy'yi döner."""
        if not self.proxies:
            await self.fetch_public_proxies()

        if not self.proxies:
            return None

        async with self._lock:
            self.current_index = (self.current_index + 1) % len(self.proxies)
            proxy = self.proxies[self.current_index]
            return proxy

    def report_proxy_failure(self, proxy_url: str):
        """Hata veren proxy'nin ceza puanını artırır ve gereğinde havuzdan atar."""
        if not proxy_url:
            return
        self.failed_counts[proxy_url] = self.failed_counts.get(proxy_url, 0) + 1
        if self.failed_counts[proxy_url] >= 3:
            if proxy_url in self.proxies:
                self.proxies.remove(proxy_url)

proxy_pool = ProxyPoolManager()
