import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('VOICE_ID')
AUDIO_DIR = 'public/audio'

def generate_tts(text, filename=None):
    if not filename:
        import uuid
        filename = f"tts_{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(AUDIO_DIR, filename)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        'text': text,
        'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5}
    }
    time.sleep(0.5)
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return output_path
    else:
        raise Exception(f"TTS failed: {response.text}") 