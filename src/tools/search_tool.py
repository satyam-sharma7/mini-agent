import os
import requests
from bs4 import BeautifulSoup
from typing import Annotated, Optional
from langchain_core.tools import tool


@tool
def web_search(
    query: Annotated[str, "Provide query to search about your topic."]
) -> list:
    """Searches the web for a given query."""
    print(f"   Calling Web_serch...: {query}  ")
    url = "https://api.tavily.com/search"
    headers = {"Authorization": os.getenv("TAVILY_API")}
    json_body = {
    "query": query,
    "search_depth": "advanced"
    }
    response = requests.post(url, json=json_body, headers=headers)

    search = [] 
    for i, r in enumerate(response.json()['results']):
        search.append({
            "index": i + 1,
            "title": r['title'],
            "url": r['url']
        })

    return search

@tool
def fetch_page(
    url: Annotated[str, "Url of the page"]
)-> str:
    """Scrapes and extracts the full text content of a specific webpage."""

    print(f"   Calling fetch_page...:  {url}")

    full_text = ""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        full_text += soup.find('h1').text
        full_text += "\n"
        full_text += soup.find('h2').text
        full_text += "\n"
    except Exception as e:
        print(e)

    paragraphs = [x.text for x in soup.find_all('p')]

    full_text += f'<untrusted_external_content source="{url}">'
    full_text += " ".join(paragraphs)

    return full_text[:3000] + "</untrusted_external_content>"
