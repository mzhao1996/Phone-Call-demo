import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def transcribe_from_url(recording_url: str):
    """
    Download Twilio recording from the given URL, save to /tmp/twilio_recording.mp3,
    then transcribe it using OpenAI Whisper API.
    Returns the transcribed text. Raises Exception on failure.
    """
    tmp_path = '/tmp/twilio_recording.mp3'
    # Download the recording
    r = requests.get(recording_url + '.mp3')
    if r.status_code != 200:
        raise Exception(f"Failed to download recording: {r.status_code} {r.text}")
    with open(tmp_path, 'wb') as f:
        f.write(r.content)
    # Transcribe with Whisper
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }
    with open(tmp_path, 'rb') as f:
        files = {
            'file': f,
            'model': (None, 'whisper-1')
        }
        response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        return response.json().get('text', '')
    else:
        raise Exception(f"STT failed: {response.text}") 