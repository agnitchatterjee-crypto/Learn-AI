import os
from dotenv import load_dotenv
import requests
from IPython.display import Markdown, display
from openai import OpenAI


load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')


gpt_model = "gpt-4.1-mini"
ollama_model = "qwen3:8b"

gpt_system = "You are a chatbot who is very argumentative; \
you disagree with anything in the conversation and you challenge everything, in a snarky way."

ollama_system = "You are a very polite, courteous chatbot. You try to agree with \
everything the other person says, or find common ground. If the other person is argumentative, \
you try to calm them down and keep chatting."


OLLAMA_BASE_URL = "http://localhost:11434/v1"

ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="OLLAMA")
openai = OpenAI()

gpt_messages = ["Hi there"]
ollama_messages = ["Hi"]

def call_gpt():
    messages = [{"role": "system", "content": gpt_system}]
    for gpt, ollama in zip(gpt_messages, ollama_messages):
        messages.append({"role": "assistant", "content": gpt})
        messages.append({"role": "user", "content": ollama})
    response = openai.chat.completions.create(model=gpt_model, messages=messages)
    return response.choices[0].message.content



def call_ollama():
    messages = [{"role": "system", "content": ollama_system}]
    for gpt, ollama_message in zip(gpt_messages, ollama_messages):
        messages.append({"role": "user", "content": gpt})
        messages.append({"role": "assistant", "content": ollama_message})
    messages.append({"role": "user", "content": gpt_messages[-1]})
    response = ollama.chat.completions.create(model=ollama_model, messages=messages)
    return response.choices[0].message.content




print(f"### GPT:\n{gpt_messages[0]}\n")
print(f"### Ollama:\n{ollama_messages[0]}\n")

for i in range(5):
    gpt_next = call_gpt()
    print(f"### GPT:\n{gpt_next}\n")
    gpt_messages.append(gpt_next)
    
    ollama_next = call_ollama()
    print(f"### Ollama:\n{ollama_next}\n")
    ollama_messages.append(ollama_next)