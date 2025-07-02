import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

def get_gpt_response(prompt, history):
    messages = []
    if prompt:
        messages.append({"role": "system", "content": prompt})
    for turn in history:
        if turn['role'] == 'customer':
            messages.append({"role": "user", "content": turn['text']})
        else:
            messages.append({"role": "assistant", "content": turn['text']})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    return response.choices[0].message['content'] 