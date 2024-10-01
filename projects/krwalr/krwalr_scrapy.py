import os
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from urllib.parse import urljoin
import textwrap
from bs4 import BeautifulSoup

class MainContentSpider(scrapy.Spider):
    name = "main_content_spider"
    
    def __init__(self, base_url: str, max_pages: int, output_folder: str, *args, **kwargs):
        super(MainContentSpider, self).__init__(*args, **kwargs)
        self.start_urls = [base_url]
        self.max_pages = max_pages
        self.output_folder = output_folder
        self.visited = set()
        self.extracted_text = []

    def parse(self, response):
        if len(self.extracted_text) >= self.max_pages:
            return
        
        main_content = self.extract_main_content(response)
        formatted_text = self.format_text(main_content)
        page_path = response.url.split("/")[-1] or "index"
        self.extracted_text.append((page_path, formatted_text))
        
        self.visited.add(response.url)
        self.log(f"Fetched: {response.url}")

        # Save the extracted text immediately
        self.save_text_file(page_path, formatted_text)

        # Follow links only under the base URL
        base_url = self.start_urls[0]
        for href in response.xpath('//a/@href').getall():
            absolute_link = urljoin(response.url, href)
            if absolute_link.startswith(base_url) and absolute_link not in self.visited:
                yield scrapy.Request(absolute_link, callback=self.parse)

    def extract_main_content(self, response):
        soup = BeautifulSoup(response.body, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to find main content containers
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        
        if main_content:
            return main_content.get_text(separator=' ', strip=True)
        else:
            # If no main content container is found, use the body
            return soup.body.get_text(separator=' ', strip=True)

    def format_text(self, text):
        # Remove extra whitespace and newlines
        cleaned_text = ' '.join(text.split())
        return textwrap.fill(cleaned_text, width=80)

    def save_text_file(self, path, text):
        os.makedirs(self.output_folder, exist_ok=True)
        filename = f"{path or f'page_{len(self.extracted_text)}'}.txt"
        with open(os.path.join(self.output_folder, filename), 'w', encoding='utf-8') as f:
            f.write(text)

def run_spider(base_url: str, max_pages: int, output_folder: str):
    process = CrawlerProcess(get_project_settings())
    process.crawl(MainContentSpider, base_url=base_url, max_pages=max_pages, output_folder=output_folder)
    process.start()

if __name__ == "__main__":
    base_url = "https://python.langchain.com/docs/integrations/platforms/"
    max_pages = 120
    output_folder = "output/langchain_docs/integrations"
    run_spider(base_url, max_pages, output_folder)