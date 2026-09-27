import os
from dotenv import load_dotenv
import requests
from scraper import fetch_website_contents, fetch_website_links
from IPython.display import Markdown, display
from openai import OpenAI



#print(requests.get("http://localhost:11434").content)

OLLAMA_BASE_URL = "http://localhost:11434/v1"
messages = [
    {"role": "system", "content": "You are a snarky assistant"},
    {"role": "user", "content": "Give me a fun fact"}
]


ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="OLLAMA")

response = ollama.chat.completions.create(
    model="qwen3:8b",
    messages=messages
)

print(response.choices[0].message.content)
