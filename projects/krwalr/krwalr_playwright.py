import os
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin
from typing import List, Tuple
import textwrap

class PlaywrightCrawler:
    def __init__(self, base_url: str, max_pages: int):
        self.base_url = base_url
        self.max_pages = max_pages
        self.visited = set()
        self.extracted_text = []

    async def crawl(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await self._crawl_page(page, self.base_url)
            await browser.close()
            self.save_text_files()

    async def _crawl_page(self, page, url: str):
        if len(self.extracted_text) >= self.max_pages or url in self.visited:
            return

        self.visited.add(url)
        print(f"Fetching: {url}")
        await page.goto(url)
        page_content = await page.content()
        formatted_text = self.format_text(page_content)
        page_path = url.split("/")[-1] or "index"
        self.extracted_text.append((page_path, formatted_text))

        # Extract links and follow them
        links = await page.query_selector_all('a[href]')
        for link in links:
            href = await link.get_attribute('href')
            absolute_link = urljoin(url, href)
            if self.base_url in absolute_link and absolute_link not in self.visited:
                await self._crawl_page(page, absolute_link)

    def format_text(self, html_content: str) -> str:
        # Simple text extraction from HTML content
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        raw_text = soup.get_text()
        return textwrap.fill(raw_text.strip(), width=80)

    def save_text_files(self):
        output_folder = "output/playwright_crawl"
        os.makedirs(output_folder, exist_ok=True)
        for i, (path, text) in enumerate(self.extracted_text):
            filename = f"{path or f'page_{i}'}.txt"
            with open(os.path.join(output_folder, filename), 'w', encoding='utf-8') as f:
                f.write(text)

if __name__ == "__main__":
    base_url = "https://legacydocs.hubspot.com/docs/methods/forms/"  # Replace with your base URL
    max_pages = 120  # Total number of pages to crawl
    crawler = PlaywrightCrawler(base_url, max_pages)
    asyncio.run(crawler.crawl())