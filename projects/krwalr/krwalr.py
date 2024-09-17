import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Tuple

def fetch_page_content(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()

def crawl_website(base_url: str, num_child_links: int, num_pages: int) -> List[Tuple[str, str]]:
    visited = set()
    queue = [base_url]
    extracted_text = []

    while queue and len(extracted_text) < num_pages:
        url = queue.pop(0)
        if url in visited or len(extracted_text) >= num_pages:
            continue
        
        visited.add(url)
        print(f"Fetching: {url}")
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            page_path = urlparse(url).path.strip('/').replace('/', '_')
            extracted_text.append((page_path, page_text))

            # Find and queue subpages
            links = soup.find_all('a', href=True)
            subpages = []
            for link in links:
                absolute_link = urljoin(url, link['href'])
                parsed_link = urlparse(absolute_link)
                if (parsed_link.netloc == urlparse(base_url).netloc and
                    parsed_link.path.startswith(urlparse(url).path) and
                    parsed_link.path != urlparse(url).path):
                    subpages.append(absolute_link)
            
            # Add subpages to queue, then other links if needed
            for subpage in subpages[:num_child_links]:
                if subpage not in visited and subpage not in queue:
                    queue.append(subpage)
            
            # If we haven't reached num_child_links, add other links
            if len(subpages) < num_child_links:
                for link in links:
                    absolute_link = urljoin(url, link['href'])
                    if (urlparse(absolute_link).netloc == urlparse(base_url).netloc and
                        absolute_link not in visited and
                        absolute_link not in queue and
                        len(queue) < num_child_links):
                        queue.append(absolute_link)

        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
    
    return extracted_text

def save_text_files(texts: List[Tuple[str, str]], folder: str):
    os.makedirs(folder, exist_ok=True)
    for i, (path, text) in enumerate(texts):
        filename = f"{path or f'page_{i}'}.txt"
        with open(os.path.join(folder, filename), 'w', encoding='utf-8') as f:
            f.write(text)

if __name__ == "__main__":
    base_url = "https://python.langchain.com/docs/"  # Replace with your base URL
    num_child_links = 10 # Increased from 5 to ensure more links are queued
    num_pages =50
    extracted_text = crawl_website(base_url, num_child_links, num_pages)
    print(f"Total pages crawled: {len(extracted_text)}")
    save_text_files(extracted_text, 'resources\langchain\docs')
