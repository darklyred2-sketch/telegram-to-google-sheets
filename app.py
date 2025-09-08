from flask import Flask, request, jsonify
import requests
import os
import base64
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
    
    chat_id = None
    text = ""
    file_data = None

    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        
        # Получаем текст из 'text' или 'caption'
        if 'text' in message:
            text = message['text']
        elif 'caption' in message:
            text = message['caption']
            app.logger.info(f"📎 Использую caption: {text}")
        else:
            app.logger.warning("⚠️ Ни text, ни caption не найдены")
            return jsonify({"status": "no_text"})

        app.logger.info(f"📩 Получен текст: {repr(text)}")

        # 🆕 Проверяем, нужно ли боту реагировать
        should_respond = False

        # Сценарий 1: личный чат — всегда отвечаем
        if message['chat']['type'] == 'private':
            should_respond = True
            app.logger.info("👤 Личный чат — обрабатываем сообщение")

        # Сценарий 2: группа — проверяем упоминание бота
        elif message['chat']['type'] in ['group', 'supergroup']:
            bot_username = "@MyResumeBot"  # 🔥 ЗАМЕНИ НА СВОЁ ИМЯ БОТА, например @HR_Bot
            entities = message.get('entities', []) + message.get('caption_entities', [])

            for entity in entities:
                if entity['type'] == 'mention':
                    mention = text[entity['offset']:entity['offset'] + entity['length']]
                    if mention.lower() == bot_username.lower():
                        should_respond = True
                        # Удаляем упоминание из текста, чтобы не мешало парсингу
                        text = text.replace(mention, "").strip()
                        app.logger.info(f"📢 Бот упомянут в группе — обрабатываем: {text}")
                        break

        if not should_respond:
            app.logger.info("🔕 Бот не упомянут — игнорируем сообщение")
            return jsonify({"status": "ignored"})

        # ... остальной код (парсинг, файлы, отправка в Google Apps Script) ...

# 🔗 Получает путь к файлу от Telegram API
def get_telegram_file_path(file_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return result['result']['file_path']
    except Exception as e:
        app.logger.error(f"❌ Ошибка получения пути файла: {str(e)}")
    return None

# 📥 Скачивает файл с серверов Telegram
def download_file(file_path):
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
    try:
        response = requests.get(file_url, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        app.logger.error(f"❌ Ошибка скачивания файла: {str(e)}")
    return None

# 🔍 Парсит текст сообщения вида "Ключ: Значение"
def parse_message(text):
    try:
        lines = text.strip().split('\n')  # Убираем лишние переносы по краям
        parsed = {}
        for line in lines:
            line = line.strip()  # Убираем пробелы в начале/конце строки
            if ':' in line:
                key, value = line.split(':', 1)  # Делим только по первому двоеточию
                parsed[key.strip()] = value.strip()
        
        # Проверяем наличие всех обязательных полей
        required = ['Позиция', 'Команда', 'Соискатель', 'Компания']
        if all(key in parsed for key in required):
            return parsed
        else:
            app.logger.warning(f"❌ Не хватает полей. Распарсено: {parsed}")
            return None
    except Exception as e:
        app.logger.error(f"❌ Ошибка парсинга: {str(e)}")
        return None

# 📨 Отправляет сообщение обратно в Telegram
def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        app.logger.error(f"❌ Не удалось отправить сообщение в Telegram: {str(e)}")

# 🚀 Запуск сервера
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
