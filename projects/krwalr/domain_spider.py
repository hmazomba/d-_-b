import os
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from urllib.parse import urljoin, urlparse
import textwrap
from bs4 import BeautifulSoup

class DomainSpider(scrapy.Spider):
    name = "domain_spider"
    
    def __init__(self, base_url: str, max_pages: int, output_folder: str, *args, **kwargs):
        super(DomainSpider, self).__init__(*args, **kwargs)
        self.start_urls = [base_url]
        self.max_pages = max_pages
        self.output_folder = output_folder
        self.visited = set()
        self.extracted_text = []
        
        # Parse the base_url to get the domain and path
        parsed_url = urlparse(base_url)
        self.domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.base_path = parsed_url.path.rstrip('/')

    def parse(self, response):
        if len(self.extracted_text) >= self.max_pages:
            return
        
        main_content = self.extract_main_content(response)
        formatted_text = self.format_text(main_content)
        page_path = self.get_page_path(response.url)
        self.extracted_text.append((page_path, formatted_text))
        
        self.visited.add(response.url)
        self.log(f"Fetched: {response.url}")

        # Save the extracted text immediately
        self.save_text_file(page_path, formatted_text)

        # Follow links within the domain and under the base path
        for href in response.xpath('//a/@href').getall():
            absolute_link = urljoin(response.url, href)
            if self.should_follow(absolute_link):
                yield scrapy.Request(absolute_link, callback=self.parse)

    def should_follow(self, url):
        if url in self.visited:
            return False
        
        parsed_url = urlparse(url)
        full_path = parsed_url.path
        
        # Check if the URL is within the same domain and starts with the base path
        return (parsed_url.netloc == urlparse(self.domain).netloc and
                full_path.startswith(self.base_path))

    def get_page_path(self, url):
        path = urlparse(url).path
        if path == self.base_path or path == f"{self.base_path}/":
            return "index"
        return path.replace(self.base_path, '').strip('/')

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
        output_path = os.path.join(self.output_folder, path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        filename = f"{os.path.basename(path) or 'index'}.txt"
        full_path = os.path.join(output_path, filename)
        
        # Debugging statement to check the full path
        self.log(f"Saving file to: {full_path}")
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(text)

def run_spider(base_url: str, max_pages: int, output_folder: str):
    process = CrawlerProcess(get_project_settings())
    process.crawl(DomainSpider, base_url=base_url, max_pages=max_pages, output_folder=output_folder)
    process.start()

if __name__ == "__main__":
    base_url = "https://legacydocs.hubspot.com/docs/methods/forms/forms_overview"
    max_pages = 120
    output_folder = "../../output/hubspot_api/methods"
    run_spider(base_url, max_pages, output_folder)