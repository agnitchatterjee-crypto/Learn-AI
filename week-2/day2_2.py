import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr # oh yeah!

load_dotenv(override=True)

openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
openrouter_url = "https://openrouter.ai/api/v1"
openrouter = OpenAI(base_url=openrouter_url, api_key=openrouter_api_key)

tell_a_joke = [
    {"role": "user", "content": "Tell a joke for a student on the journey to becoming an expert in LLM Engineering"},
]

response = openrouter.chat.completions.create(model="qwen/qwen3.8-27b:free", messages=tell_a_joke, extra_body={"usage": {"include": True}})
print(response.choices[0].message.content)

print(f"Input tokens: {response.usage.prompt_tokens}")
print(f"Output tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")
cost = getattr(response.usage, "cost", None) or 0  # USD, returned by OpenRouter
print(f"Total cost: {cost*100:.4f} cents")

