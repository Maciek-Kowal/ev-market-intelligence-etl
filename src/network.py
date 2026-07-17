import logging
import asyncio
import httpx

class OtomotoNetwork:
    def __init__(self, max_concurrent: int = 3):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    async def fetch_page(self, client: httpx.AsyncClient, url: str):
        async with self.semaphore:
            try:
                response = await client.get(url, timeout=15.0)
                response.raise_for_status()
                self.logger.info(f"Pobrano HTML z: {url}")
                return response.text
            except Exception as e:
                self.logger.error(f"Błąd łączenia z {url}: {e}")
                return None

    async def fetch_all(self, urls: list[str]):
        self.logger.info("Uruchamianie HTTP/2")
        async with httpx.AsyncClient(http2=True, headers=self.headers) as client:
            tasks = [self.fetch_page(client, url) for url in urls]
            results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]