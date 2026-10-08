from docx import Document
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import gradio as gr
import docx

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")



with open('course_contents.txt', 'r', encoding='utf-8') as file:
    # Read the entire content into a string variable
    file_contents = file.read()

def professional_builder(cv_link, model):

    openai = OpenAI()
    ollama = OpenAI(base_url="http://localhost:11434/v1", api_key="OLLAMA")

    doc = docx.Document(cv_link.name)
        
    # Extract text from each paragraph and join them with newlines
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
            
    text = "\n".join(full_text)

    user_content = "I want you to \
    1) Look at my profile and generate a one year plan for me in details so as to either 2x my salary or get a better job in the next 12 months. \
    2) Please consider my current skills, experience, and the latest trends in the industry. \
    3) Provide a month-by-month breakdown of actionable steps, including learning resources, networking strategies, and any certifications that would be beneficial. \
    4) Also, suggest ways to measure progress and adjust the plan as needed. My CV is as follows (in text format) \n" + text + " \
    5) Provide the output in a clear and business-like format, suitable for presentation to a mentor or career coach in .md format. The .md file should be without code blocks.\
    6) Help with deatiled links to study guides to udemy/youtube or other stydy resources and clarly articulate whihc course is best for which skill. \
    7) If within the markdowns, you are having wide tables, switch the bullet lines instead of tables. \
    8) Please provide a list of relevant links to study guides, courses, and resources"

    messages = [
    {"role": "system", "content": "You are a professional CV reviewer and career guide, expert at helping data engineers and solutions architect to grow their careers. You are an expert in career planning, skill development, and industry trends."},
    {"role": "user", "content": user_content}
    ]

    if model == "Ollama Small":
        stream = ollama.chat.completions.create(
            model="gemma3:270m", 
            messages=messages,
            response_format={"type": "text"},
            stream=True
        )
    elif model == "Ollama Large":
        stream = ollama.chat.completions.create(
            model="qwen3:8b",
            messages=messages,
            response_format={"type": "text"},
            stream=True
        )
    else:
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


message_output = gr.Markdown(label="Response")

input_uploader = gr.File(file_types=[".docx"], label="Upload your Word (.docx) document")
model_selector = gr.Dropdown(choices=["Ollama Small", "OpenAI", "Ollama Large"], label="Select Model", value="Ollama Small", info="Choose the model to use for generating the career plan.")

demo = gr.Interface(
    fn=professional_builder,
    inputs=[input_uploader, model_selector],
    outputs=message_output,
    title="Professional Builder",
    description="Upload your CV and get a personalized career plan!",
    flagging_mode="never"
)

demo.launch(inbrowser=True)  # Opens the website in a new tab in your default browser.
