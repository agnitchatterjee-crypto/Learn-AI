from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv('GOOGLE_API_KEY')

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")


messages = [
    {"role": "system", "content": "You are a snarky assistant"},
    {"role": "user", "content": "Give me a fun fact"}
]


openai = OpenAI(base_url=GEMINI_BASE_URL, api_key=api_key)

response = openai.chat.completions.create(
    model="gemini-3.8-flash",
    messages=messages
)

print(response.choices[0].message.content)


