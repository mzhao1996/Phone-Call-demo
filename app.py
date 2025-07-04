import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Play, Record
from twilio.rest import Client
from dotenv import load_dotenv
from services.tts import generate_tts
from services.stt import transcribe_from_url
from services.chat import get_gpt_response, limit_sentences
from datetime import datetime
import time
from threading import Thread

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
    # 清除所有 transcript 文件
    transcript_folder = app.config['TRANSCRIPT_FOLDER']
    for filename in os.listdir(transcript_folder):
        if filename.endswith('.json'):
            os.remove(os.path.join(transcript_folder, filename))
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
    phone_number = data['phone_number']
    prompt = data['prompt']
    # 异步后台生成AI第一句话和TTS
    def generate_ai_first_sentence():
        gpt_reply = get_gpt_response(prompt, [])
        gpt_reply = limit_sentences(gpt_reply, max_sentences=3)
        transcript_path = os.path.join(app.config['TRANSCRIPT_FOLDER'], f"{phone_number}.json")
        transcript = [{'role': 'assistant', 'text': gpt_reply}]
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        generate_tts(gpt_reply)
    Thread(target=generate_ai_first_sentence).start()
    # 先播放本地mp3，播放完后跳转到/voice_next
    response = VoiceResponse()
    response.play(f"{SERVER_URL}/audio/ElevenLabs_2025-07-03T17_27_31_british%20woman_gen_sp100_s50_sb75_v3.mp3")
    response.redirect(f"{SERVER_URL}/voice_next")
    return str(response)

@app.route('/voice_next', methods=['POST'])
def voice_next():
    # 读取表单数据
    with open('client_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    phone_number = data['phone_number']
    # 读取AI第一句话的TTS音频
    transcript_path = os.path.join(app.config['TRANSCRIPT_FOLDER'], f"{phone_number}.json")
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)
    gpt_reply = transcript[0]['text']
    audio_path = generate_tts(gpt_reply)  # 如果已生成会直接返回路径
    response = VoiceResponse()
    response.play(f"{SERVER_URL}/audio/{os.path.basename(audio_path)}")
    response.record(
        action=f"{SERVER_URL}/process_recording",
        maxLength=30,
        playBeep=False
    )
    return str(response)

@app.route('/process_recording', methods=['POST'])
def process_recording():
    recording_url = request.form['RecordingUrl']
    recording_sid = request.form.get('RecordingSid', datetime.now().strftime('%Y%m%d%H%M%S'))
    # 下载录音（加认证）
    audio_file = os.path.join(app.config['UPLOAD_FOLDER'], f"recording_{recording_sid}.mp3")
    import requests
    time.sleep(0.5)
    r = requests.get(recording_url + '.mp3', auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    if r.status_code != 200:
        print(f"Failed to download recording: {r.status_code} {r.text}")
        return "<Response><Say>Recording download failed.</Say></Response>", 500
    with open(audio_file, 'wb') as f:
        f.write(r.content)
    # STT 转写
    customer_text = transcribe_from_url(recording_url)
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
    gpt_reply = limit_sentences(gpt_reply, max_sentences=3)
    transcript.append({'role': 'assistant', 'text': gpt_reply})
    # 保存 transcript
    with open(transcript_path, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    # TTS 合成
    audio_path = generate_tts(gpt_reply)
    # 确保音频文件已生成
    if not os.path.exists(audio_path):
        return "<Response><Say>AI audio not ready.</Say></Response>", 500
    response = VoiceResponse()
    response.play(f"{SERVER_URL}/audio/{os.path.basename(audio_path)}")
    response.record(
        action=f"{SERVER_URL}/process_recording",
        maxLength=30,
        playBeep=False
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

@app.route('/twilio/recording', methods=['POST'])
def twilio_recording():
    """
    Handle Twilio webhook for recording. Extract RecordingUrl and From, transcribe audio, print result.
    Return 200 OK on success, 400/500 on error.
    """
    try:
        recording_url = request.form.get('RecordingUrl')
        from_number = request.form.get('From')
        if not recording_url or not from_number:
            return jsonify({'error': 'Missing RecordingUrl or From'}), 400
        text = transcribe_from_url(recording_url)
        print(f"Transcription from {from_number}: {text}")
        return jsonify({'text': text}), 200
    except Exception as e:
        print(f"Error in /twilio/recording: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 