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

            # Find and queue subpages
            links = soup.find_all('a', href=True)
            for link in links:
                absolute_link = urljoin(url, link['href'])
                parsed_link = urlparse(absolute_link)
                
                # Check if the link is a valid subpage of the base URL
                if (parsed_link.netloc == urlparse(base_url).netloc and
                    absolute_link not in visited and
                    absolute_link not in queue and
                    not parsed_link.fragment):  # Exclude links with fragment identifiers
                    # Ensure the path starts with the base URL's path
                    if parsed_link.path.startswith(urlparse(base_url).path):
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
    base_url = "https://legacydocs.hubspot.com/docs/methods/forms/v2/get_forms"  # Replace with your base URL
    max_pages = 120  # Total number of pages to crawl
    output_folder = "../../output/hubspot_api/forms/"
    extracted_text = crawl_website(base_url, max_pages)
    print(f"Total pages crawled: {len(extracted_text)}")
    save_text_files(extracted_text, output_folder)