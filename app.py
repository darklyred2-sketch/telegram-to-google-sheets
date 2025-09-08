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

    # Проверяем, есть ли сообщение
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        
        # 🆕 Получаем текст: из 'text' или из 'caption' (если файл прикреплён)
        if 'text' in message:
            text = message['text']
        elif 'caption' in message:
            text = message['caption']
            app.logger.info(f"📎 Использую caption: {text}")
        else:
            app.logger.warning("⚠️ Ни text, ни caption не найдены")

        # 📝 Логируем полученный текст для отладки (repr покажет скрытые символы)
        app.logger.info(f"📩 Получен текст: {repr(text)}")

        # 📄 Если есть документ (файл)
        if 'document' in message:
            try:
                file_id = message['document']['file_id']
                file_name = message['document'].get('file_name', 'unknown_file')
                mime_type = message['document'].get('mime_type', 'application/octet-stream')
                
                # Получаем путь к файлу
                file_path = get_telegram_file_path(file_id)
                if file_path:
                    # Скачиваем файл
                    file_content = download_file(file_path)
                    if file_content:
                        # Конвертируем в base64
                        file_base64 = base64.b64encode(file_content).decode('utf-8')
                        file_data = {
                            "name": file_name,
                            "base64": file_base64,
                            "mimeType": mime_type
                        }
                        app.logger.info(f"📄 Файл получен: {file_name}")
            except Exception as e:
                app.logger.error(f"❌ Ошибка обработки файла: {str(e)}")

        # 🔍 Парсим текстовое сообщение
        parsed_data = parse_message(text) if text else {}
        
        # 📤 Отправляем данные, если есть текст или файл
        if parsed_data or file_data:
            payload = {
                "data": parsed_data or {},
                "file": file_data  # Может быть None — если файла нет
            }
            
            try:
                # Отправляем в Google Apps Script
                response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
                
                if response.status_code == 200:
                    send_telegram_message(chat_id, "✅ Данные и файл добавлены в таблицу!")
                    app.logger.info(f"📤 Успешно отправлено: {parsed_data}, файл: {'да' if file_data else 'нет'}")
                else:
                    error_msg = f"❌ Ошибка сервера таблицы: {response.status_code}"
                    send_telegram_message(chat_id, error_msg)
                    app.logger.error(error_msg)
                    
            except Exception as e:
                error_msg = "❌ Не удалось отправить данные."
                send_telegram_message(chat_id, error_msg)
                app.logger.error(f"❌ Исключение при отправке: {str(e)}")
        else:
            send_telegram_message(chat_id, "⚠️ Не удалось распознать данные. Отправьте текст в формате:\nПозиция: ...\nКоманда: ...\nСоискатель: ...\nКомпания: ...")
    
    return jsonify({"status": "ok"})

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
