import os
from dotenv import load_dotenv
import gradio as gr
from openai import OpenAI

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")

#ollama = OpenAI(base_url="http://localhost:11434/v1", api_key="OLLAMA")
openai = OpenAI()



def chat(message, history):
    #print(history) -- [{'role': 'user', 'metadata': None, 'content': [{'text': 'Hello', 'type': 'text'}], 'options': None}, {'role': 'assistant', 'metadata': None, 'content': [{'text': 'Hello! How can I assist you today?', 'type': 'text'}], 'options': None}] (output of the history variable)
    system_message = "You are a helpful assistant."
    
    if "lonely" in message.lower():
        system_message += "If the user feels lonely offer his jokes to lighten up his/her mood"
    history = [{"role":h["role"], "content":h["content"]} for h in history]
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    
    stream = openai.chat.completions.create(
    model="gpt-4.1-mini", 
    messages=messages,
    response_format={"type": "text"},
    stream=True
    )
    response = ""

    for chunk in stream:
        response += chunk.choices[0].delta.content or ""
        yield response


gr.ChatInterface(fn=chat).launch()
