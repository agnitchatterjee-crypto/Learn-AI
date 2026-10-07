import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr # oh yeah!
from litellm import completion

load_dotenv(override=True)


response1 = completion(
    model="gpt-4o", 
    messages=[{"role": "user", "content": "Tell a joke for a student on the journey to becoming an expert in LLM Engineering"}]
)
print(response1.choices[0].message.content)