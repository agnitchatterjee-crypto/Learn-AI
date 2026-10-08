import os
from dotenv import load_dotenv
import requests
from IPython.display import Markdown, display
from openai import OpenAI
import time

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

OLLAMA_BASE_URL = "http://localhost:11434/v1"

gpt_model = "gpt-4.1-mini"
ollama_model = "gemma3:270m"

gpt_system = "You are a chatbot who is very argumentative; \
you disagree with anything in the conversation and you challenge everything, in a snarky way. The chat history contains reposnes from both the user and the usassistant which is you in this case"

ollama_system = "You are a very polite, courteous chatbot. You try to agree with \
everything the other person says, or find common ground. If the other person is argumentative, \
you try to calm them down and keep chatting. The chat history contains reposnes from both the assistant and the user which is you in this case"

ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="OLLAMA")
openai = OpenAI()

history = [("ollama", "Hi")]   # gemma opens the conversation

def build_messages(system, me):
    messages = [{"role": "system", "content": system}]
    for speaker, text in history:
        role = "assistant" if speaker == me else "user"
        messages.append({"role": role, "content": text})
    return messages


for i in range(5):
    r = openai.chat.completions.create(model=gpt_model, messages=build_messages(gpt_system, "gpt"))
    gpt_reply = r.choices[0].message.content
    history.append(("gpt", gpt_reply))
    print("gpt:", gpt_reply)

    r = ollama.chat.completions.create(
        model=ollama_model, messages=build_messages(ollama_system, "ollama"))
    ollama_reply = r.choices[0].message.content
    history.append(("ollama", ollama_reply))
    print("ollama:", ollama_reply)

    time.sleep(5)