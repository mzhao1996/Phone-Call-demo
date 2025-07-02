import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def transcribe_audio(audio_path):
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }
    with open(audio_path, 'rb') as f:
        files = {
            'file': f,
            'model': (None, 'whisper-1')
        }
        response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        return response.json().get('text', '')
    else:
        raise Exception(f"STT failed: {response.text}") 
    

