import gradio as gr
import os
from dotenv import load_dotenv
import requests
from IPython.display import Markdown, display
from openai import OpenAI

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

openai = OpenAI()


def topic_generator(topic):
    reponse = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that responds in markdown without code blocks"},
            {"role": "user", "content": topic}
        ]
    )
    return reponse.choices[0].message.content


message_input = gr.Textbox(label="Your topic", info="Enter a topic for the joke", lines=5)
message_output = gr.Markdown(label="Response")

demo = gr.Interface(
    fn=topic_generator,
    inputs=message_input,
    outputs=message_output,
    title="Topic Generator",
    description="Enter a topic and get a helpful response about it!",
    flagging_mode="never"
)

demo.launch(inbrowser=True)  # Opens the website in a new tab in your default browser.