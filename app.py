import os
import json
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
WEBHOOK_DATA_FILE = 'webhook_data.json'

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
        payload = request.get_json(force=True, silent=True)
        if payload is None:
            payload = request.form.to_dict()  # 兼容 x-www-form-urlencoded
        if not payload:
            return 'No data received', 400
        # 读取已有数据
        if os.path.exists(WEBHOOK_DATA_FILE):
            with open(WEBHOOK_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []
        data.append(payload)
        with open(WEBHOOK_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return 'Webhook received', 200
    except Exception as e:
        return f'Error: {e}', 500

if __name__ == '__main__':
    app.run(debug=True) 