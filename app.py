from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ➡️ ДОБАВЬ ЭТОТ БЛОК:
@app.route('/', methods=['GET'])
def health_check():
    return "OK", 200


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    if 'message' in update and 'text' in update['message']:
        text = update['message']['text']
        chat_id = update['message']['chat']['id']

        data = parse_message(text)

        if data:
            try:
                response = requests.post(APPS_SCRIPT_URL, json=data, timeout=10)
                if response.status_code == 200:
                    send_telegram_message(chat_id, "✅ Успешно добавлено в таблицу!")
                else:
                    send_telegram_message(chat_id, f"❌ Ошибка Google Apps Script: {response.text}")
            except Exception as e:
                send_telegram_message(chat_id, f"⚠️ Ошибка подключения: {str(e)}")
        else:
            send_telegram_message(chat_id, "⚠️ Неверный формат. Используй:\nПозиция: ...\nКоманда: ...\nСоискатель: ...\nКомпания: ...\nДата: ...")

    return jsonify({"status": "ok"})

def parse_message(text):
    lines = text.split('\n')
    parsed = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            parsed[key.strip()] = value.strip()

    required = ['Позиция', 'Команда', 'Соискатель', 'Компания', 'Дата']
    if all(key in parsed for key in required):
        return {
            "position": parsed['Позиция'],
            "team": parsed['Команда'],
            "applicant": parsed['Соискатель'],
            "company": parsed['Компания'],
            "date": parsed['Дата']
        }
    return None

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
