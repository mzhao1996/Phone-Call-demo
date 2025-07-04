import os
import json
import hmac
import hashlib
from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
WEBHOOK_DATA_FILE = 'webhook_data.json'

# 设置你的 ElevenLabs webhook secret
ELEVENLABS_WEBHOOK_SECRET = os.getenv('ELEVENLABS_WEBHOOK_SECRET', 'your-secret-here')

def verify_webhook_signature(payload, signature):
    """验证 webhook 签名"""
    expected_signature = hmac.new(
        ELEVENLABS_WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@app.route('/', methods=['GET'])
def show_webhook_data():
    if os.path.exists(WEBHOOK_DATA_FILE):
        with open(WEBHOOK_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = []
    return render_template('index.html', webhook_data=data)

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    try:
        # 获取原始请求数据
        payload = request.get_data()
        
        # 验证签名（如果提供了签名头）
        signature = request.headers.get('X-ElevenLabs-Signature')
        if signature and not verify_webhook_signature(payload, signature):
            return 'Invalid signature', 401
        
        # 解析 JSON 数据
        try:
            data = request.get_json(force=True)
        except:
            data = request.form.to_dict()  # 兼容 form-data
        
        if not data:
            return 'No data received', 400
            
        # 读取已有数据
        if os.path.exists(WEBHOOK_DATA_FILE):
            with open(WEBHOOK_DATA_FILE, 'r', encoding='utf-8') as f:
                webhook_data = json.load(f)
        else:
            webhook_data = []
        
        # 添加时间戳
        data['received_at'] = request.headers.get('X-Request-Timestamp', 'unknown')
        webhook_data.append(data)
        
        with open(WEBHOOK_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(webhook_data, f, ensure_ascii=False, indent=2)
            
        return 'Webhook received', 200
    except Exception as e:
        return f'Error: {e}', 500

if __name__ == '__main__':
    app.run(debug=True) 