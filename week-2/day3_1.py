import gradio as gr
import os
from dotenv import load_dotenv
import requests
from IPython.display import Markdown, display
from openai import OpenAI

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

OLLAMA_BASE_URL = "http://localhost:11434/v1"

# ollama_model = "gemma3:270m"
# ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="OLLAMA")

openai = OpenAI()


def joke_generator(topic):
    reponse = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a snarky assistant."},
            {"role": "user", "content": f"Tell a joke about {topic}."}
        ]
    )
    return reponse.choices[0].message.content

#demo = gr.Interface(fn=joke_generator, inputs="textbox", outputs="textbox", flagging_mode="never")
#demo.launch()
#demo.launch(share=True) -- Makes the website public, but it is not needed for this demo. If someones types in the input iot still calls the function on this compouter. 
#demo.launch(inbrowser=True, auth={"bob", "sjdjksdkj"}) -- Opens the website in a new tab in your default browser. Also adds in authentications


message_input = gr.Textbox(label="Your topic", info="Enter a topic for the joke", lines=5)
message_output = gr.Textbox(label="Joke", info="Here's your joke!", lines=5)

demo = gr.Interface(
    fn=joke_generator,
    inputs=message_input,
    outputs=message_output,
    title="Joke Generator",
    description="Enter a topic and get a snarky joke about it!",
    flagging_mode="never"
)

demo.launch(inbrowser=True)  # Opens the website in a new tab in your default browser.