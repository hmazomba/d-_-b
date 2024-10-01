import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Tuple

def fetch_page_content(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def crawl_website(base_url: str, max_pages: int) -> List[Tuple[str, str]]:
    visited = set()
    queue = [base_url]
    extracted_text = []
    base_netloc = urlparse(base_url).netloc  # Get the base domain

    while queue and len(extracted_text) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        
        visited.add(url)
        print(f"Fetching: {url}")
        try:
            page_content = fetch_page_content(url)
            soup = BeautifulSoup(page_content, 'html.parser')
            page_text = soup.get_text()
            page_path = urlparse(url).path.strip('/').replace('/', '_')
            extracted_text.append((page_path, page_text))
            print(f"Extracted text from: {url}")  # Debugging statement

            # Find and queue subpages
            links = soup.find_all('a', href=True)
            for link in links:
                absolute_link = urljoin(url, link['href'])
                parsed_link = urlparse(absolute_link)
                # Allow crawling of all subdomains
                if (parsed_link.netloc.endswith(base_netloc) and
                    absolute_link not in visited and
                    absolute_link not in queue):
                    queue.append(absolute_link)

        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
    
    print(f"Total pages extracted: {len(extracted_text)}")  # Debugging statement
    return extracted_text

def save_text_files(texts: List[Tuple[str, str]], folder: str):
    os.makedirs(folder, exist_ok=True)  # Ensure the output directory exists
    print(f"Saving files to: {folder}")  # Debugging statement
    for i, (path, text) in enumerate(texts):
        filename = f"{path or f'page_{i}'}.txt"
        file_path = os.path.join(folder, filename)
        print(f"Writing to file: {file_path}")  # Debugging statement
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)

if __name__ == "__main__":
    base_url = "https://legacydocs.hubspot.com/docs/overview"  # Replace with your desired URL
    max_pages = 1250  # Adjust this value to control the number of pages to crawl
    output_folder = "output/hubspot_api/methods"  # Specify your desired output folder

    extracted_text = crawl_website(base_url, max_pages)
    if extracted_text:  # Check if extracted_text is not empty
        print(f"Total pages crawled: {len(extracted_text)}")
        save_text_files(extracted_text, output_folder)
    else:
        print("No pages were crawled.")