import asyncio
import os
import pytest
from web_crawler import WebCrawler, setup_ai_agent
from playwright.async_api import async_playwright

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser
        await browser.close()

@pytest.mark.asyncio
async def test_crawl_page(browser):
    test_url = "https://python.langchain.com/docs/how_to/"
    max_pages = 1
    crawler = WebCrawler(test_url, max_pages)

    page = await browser.new_page()
    await crawler.crawl_page(page, test_url)

    assert len(crawler.visited_urls) == 1
    assert test_url in crawler.visited_urls

    # Check if the output file was created
    output_file = os.path.join(crawler.output_folder, "example.com.txt")
    assert os.path.exists(output_file)

    # Check if the file contains some text
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert len(content) > 0

@pytest.mark.asyncio
async def test_max_pages_limit():
    test_url = "https://python.langchain.com/docs/how_to/"
    max_pages = 2
    crawler = WebCrawler(test_url, max_pages)

    await crawler.crawl()

    assert len(crawler.visited_urls) <= max_pages

@pytest.mark.asyncio
async def test_ai_agent():
    agent_chain = await setup_ai_agent()
    result = await agent_chain.arun("What is the title of the webpage at https://python.langchain.com/docs/how_to/#tools")
    assert "Example Domain" in result

if __name__ == "__main__":
    pytest.main([__file__])