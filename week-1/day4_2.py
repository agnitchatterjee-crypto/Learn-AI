import os
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")


from openai import OpenAI

openai = OpenAI()


messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hi! I'm Ed!"}
    ]

response = openai.chat.completions.create(model="gpt-4.1-mini", messages=messages)
#print(response.choices[0].message.content)


messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "What's my name?"}
    ]

response = openai.chat.completions.create(model="gpt-4.1-mini", messages=messages)
#print(response.choices[0].message.content)

#Hi Ed! Nice to meet you. How can I assist you today?
#I’m not sure what your name is. Could you please tell me?

#So it is only an illusion that the llm has memory.

#print("-"*1000)

messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hi! I'm Ed!"},
    {"role": "assistant", "content": "Hi Ed! How can I assist you today?"},
    {"role": "user", "content": "What's my name?"}
    ]

response = openai.chat.completions.create(model="gpt-4.1-mini", messages=messages)
#print(response.choices[0].message.content)


print("-"*1000)
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hi! I'm Ed!"}
    ]

response = openai.chat.completions.create(model="gpt-4.1-mini", messages=messages)
messages.append({"role": "assistant", "content": response.choices[0].message.content})
messages.append({"role": "user", "content": "What's my name?"})

response = openai.chat.completions.create(model="gpt-4.1-mini", messages=messages)
print(response.choices[0].message.content)