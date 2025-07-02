import os
import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_STT_API_KEY = os.getenv('ELEVENLABS_STT_API_KEY')

def transcribe_audio(audio_path):
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {
        'xi-api-key': ELEVENLABS_STT_API_KEY
    }
    with open(audio_path, 'rb') as f:
        files = {'audio': f}
        response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        return response.json().get('text', '')
    else:
        raise Exception(f"STT failed: {response.text}") 