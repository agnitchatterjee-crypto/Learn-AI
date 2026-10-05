import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr # oh yeah!
from langchain_ollama import ChatOllama

load_dotenv(override=True)


tell_a_joke = [
    {"role": "user", "content": "Tell a joke for a student on the journey to becoming an expert in LLM Engineering"},
]

model = ChatOllama(
    model="llama3.2:latest",
    temperature=0.7,
)
response = model.invoke(tell_a_joke)

print(response.content)

