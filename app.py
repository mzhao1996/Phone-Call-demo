import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Play, Record
from twilio.rest import Client
from dotenv import load_dotenv
from services.tts import generate_tts
from services.stt import transcribe_audio
from services.chat import get_gpt_response
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'public/audio'
app.config['TRANSCRIPT_FOLDER'] = 'transcripts'

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRANSCRIPT_FOLDER'], exist_ok=True)

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
SERVER_URL = os.getenv('SERVER_URL')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_call', methods=['POST'])
def start_call():
    data = request.json
    customer_name = data['customer_name']
    phone_number = data['phone_number']
    prompt = data['prompt']
    # 保存表单数据
    with open('client_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
    # 发起呼叫
    call = client.calls.create(
        to=phone_number,
        from_=TWILIO_PHONE_NUMBER,
        url=f"{SERVER_URL}/voice"
    )
    return jsonify({'status': 'calling', 'call_sid': call.sid})

@app.route('/voice', methods=['POST'])
def voice():
    # 读取表单数据
    with open('client_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    prompt = data['prompt']
    # 用 GPT 生成第一句
    gpt_reply = get_gpt_response(prompt, [])
    # TTS 合成
    audio_path = generate_tts(gpt_reply)
    response = VoiceResponse()
    response.play(f"{SERVER_URL}/audio/{os.path.basename(audio_path)}")
    response.record(
        action=f"{SERVER_URL}/process_recording",
        maxLength=30,
        playBeep=True
    )
    return str(response)

@app.route('/process_recording', methods=['POST'])
def process_recording():
    recording_url = request.form['RecordingUrl']
    # 下载录音
    audio_file = os.path.join(app.config['UPLOAD_FOLDER'], f"recording_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
    import requests
    r = requests.get(recording_url + '.wav')
    with open(audio_file, 'wb') as f:
        f.write(r.content)
    # 用ffmpeg转码为标准wav（16kHz, 单声道）
    converted_file = audio_file.replace('.wav', '_converted.wav')
    import subprocess
    subprocess.run([
        'ffmpeg', '-y', '-i', audio_file, '-ar', '16000', '-ac', '1', converted_file
    ], check=True)
    # STT 转写
    customer_text = transcribe_audio(converted_file)
    # 读取 prompt
    with open('client_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    prompt = data['prompt']
    # 读取历史对话
    transcript_path = os.path.join(app.config['TRANSCRIPT_FOLDER'], f"{data['phone_number']}.json")
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = json.load(f)
    else:
        transcript = []
    transcript.append({'role': 'customer', 'text': customer_text})
    # GPT 回复
    gpt_reply = get_gpt_response(prompt, transcript)
    transcript.append({'role': 'assistant', 'text': gpt_reply})
    # 保存 transcript
    with open(transcript_path, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    # TTS 合成
    audio_path = generate_tts(gpt_reply)
    response = VoiceResponse()
    response.play(f"{SERVER_URL}/audio/{os.path.basename(audio_path)}")
    response.record(
        action=f"{SERVER_URL}/process_recording",
        maxLength=30,
        playBeep=True
    )
    return str(response)

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/get_transcript', methods=['GET'])
def get_transcript():
    phone_number = request.args.get('phone_number')
    transcript_path = os.path.join(app.config['TRANSCRIPT_FOLDER'], f"{phone_number}.json")
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = json.load(f)
        return jsonify({'transcript': transcript})
    else:
        return jsonify({'transcript': []})

if __name__ == '__main__':
    app.run(debug=True) 