from docx import Document
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import gradio as gr
import docx
from pathlib import Path
from bundle_source_code import build_markdown



def generate_markdown_from_source(source_path):
    source = Path(source_path)
    md = build_markdown(source)          # returns the Markdown as a string
    Path("bundle.md").write_text(md, encoding="utf-8")
    return md


load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")


message_input = gr.Textbox(label="Base source code folder", info="Enter the path to your source code folder", lines=5)
message_output = gr.Markdown(label="Response")


demo = gr.Interface(
    fn=generate_markdown_from_source,
    inputs=message_input,
    outputs=message_output,
    title="Source Code Markdown Generator",
    description="Enter the path to your source code folder and get a Markdown representation of the code structure.",
    flagging_mode="never"
)

demo.launch(inbrowser=True)  # Opens the website in a new tab in your default browser.
