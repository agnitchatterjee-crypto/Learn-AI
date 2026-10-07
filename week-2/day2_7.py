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

chat_history = "user: Hi"

#response = openai.chat.completions.create(model=gpt_model, messages=[{"role": "system", "content": gpt_system},{"role": "assistant", "content": chat_history}])

#print(response.choices[0].message.content)

#chat_history = chat_history + "\nassistant: " + response.choices[0].message.content

#print(chat_history)

#response = ollama.chat.completions.create(model=ollama_model, messages=[{"role": "system", "content": ollama_system},{"role": "user", "content": chat_history}])

#print(response.choices[0].message.content)

#chat_history = chat_history + "\nuser: " + response.choices[0].message.content

#print(chat_history)

for i in range(5):
    response_assistant = openai.chat.completions.create(model=gpt_model, messages=[{"role": "system", "content": gpt_system},{"role": "assistant", "content": chat_history}])

    print("assistant: " + response_assistant.choices[0].message.content)
    chat_history = chat_history + "\nassistant: " + response_assistant.choices[0].message.content

    response_user = ollama.chat.completions.create(model=ollama_model, messages=[{"role": "system", "content": ollama_system},{"role": "user", "content": chat_history}])

    print("user: " + response_user.choices[0].message.content)
    chat_history = chat_history + "\nuser: " + response_user.choices[0].message.content

    #print(chat_history)

    time.sleep(5)