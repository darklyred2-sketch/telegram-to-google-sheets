from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Получаем токен и URL из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

# ➡️ Обработчик для проверки здоровья сервиса
@app.route('/', methods=['GET'])
def health_check():
    return "OK", 200

# ➡️ Обработчик вебхука от Telegram
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    
    # Проверяем, есть ли текст в сообщении
    if 'message' in update and 'text' in update['message']:
        text = update['message']['text']
        chat_id = update['message']['chat']['id']
        
        # Парсим сообщение (формат "Ключ: Значение")
        data = parse_message(text)
        
        if data:
            # ➡️ ОТПРАВЛЯЕМ ТОЛЬКО НУЖНЫЕ ПОЛЯ — БЕЗ "date"
            payload = {
                "position": data['Позиция'],
                "team": data['Команда'],
                "applicant": data['Соискатель'],
                "company": data['Компания']
                # Поле "date" НЕ отправляем — оно будет сгенерировано в Google Apps Script
            }
            
            try:
                # Отправляем данные в Google Apps Script
                response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
                
                if response.status_code == 200:
                    send_telegram_message(chat_id, "✅ Данные добавлены в таблицу!")
                    app.logger.info(f"✅ Успешно отправлено: {payload}")
                else:
                    send_telegram_message(chat_id, f"❌ Ошибка сервера таблицы: {response.status_code}")
                    app.logger.error(f"❌ Ошибка Google Apps Script: {response.text}")
                    
            except Exception as e:
                send_telegram_message(chat_id, "❌ Не удалось отправить данные.")
                app.logger.error(f"❌ Исключение при отправке: {str(e)}")
                
        else:
            send_telegram_message(chat_id, "⚠️ Неверный формат сообщения. Используй:\nПозиция: ...\nКоманда: ...\nСоискатель: ...\nКомпания: ...")
            app.logger.warning(f"⚠️ Неверный формат: {text}")
    
    return jsonify({"status": "ok"})

def parse_message(text):
    """Парсит текст сообщения вида 'Ключ: Значение'"""
    lines = text.split('\n')
    parsed = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            parsed[key.strip()] = value.strip()
    
    # Проверяем, что все нужные поля есть (БЕЗ "Дата")
    required = ['Позиция', 'Команда', 'Соискатель', 'Компания']
    if all(key in parsed for key in required):
        return parsed
    else:
        return None

def send_telegram_message(chat_id, text):
    """Отправляет сообщение обратно в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        app.logger.error(f"❌ Не удалось отправить сообщение в Telegram: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
