from flask import Flask, request, jsonify
import requests
import os
import base64
import logging
import traceback

# 🚀 Создаём приложение
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 🧩 Получаем токен и URL из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
COMPANY_SCRIPT_URL = os.getenv("COMPANY_SCRIPT_URL")  # URL для получения компании

# ➡️ Обработчик для проверки здоровья сервиса
@app.route('/', methods=['GET'])
def health_check():
    return "OK", 200

# ➡️ Глобальный обработчик ошибок
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"💥 Необработанная ошибка:\n{traceback.format_exc()}")
    return jsonify({"status": "error", "message": str(e)}), 500

# ➡️ Обработчик вебхука от Telegram
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()
        
        # 🆕 Обработка нажатия inline-кнопок
        if 'callback_query' in update:
            callback = update['callback_query']
            chat_id = callback['message']['chat']['id']
            data = callback['data']

            # Отправляем шаблон в ответ на нажатие кнопки
            if data == "template_Тестировщик":
                template = (
                    "Позиция: SENIOR SDET\n"
                    "Команда: DATAHUB\n"
                    "Соискатель: \n"
                    "\n<a href="https://docs.google.com/document/d/1WD-X-jStPjSgJvs9428u-eHU7QTr6Almc0IgFq3limM/edit?tab=t.0">Описание вакансии</a>\n"
                    "\n!Прикрепите резюме, напиши ФИО соискателя и поставь @ перед именем бота ниже!"
                    "\nOutstaff_connect_bot"
                )
            elif data == "template_devops":
                template = (
                    "Позиция: SENIOR DEVOPS\n"
                    "Команда: DATAMASTERS\n"
                    "Соискатель: \n"
                    "\n!Прикрепите резюме, напиши ФИО соискателя и поставь @ перед именем бота ниже!"
                    "\nOutstaff_connect_bot"
                )
            elif data == "template_frontend":
                template = (
                    "Позиция: SENIOR FRONTEND\n"
                    "Команда: DATAHUB\n"
                    "Соискатель: \n"
                    "\n!Прикрепите резюме, напиши ФИО соискателя и поставь @ перед именем бота ниже!"
                    "\nOutstaff_connect_bot"
                )
            elif data == "template_Архитектор":
                template = (
                    "Позиция: MIDDLE DATA ARCHITECT\n"
                    "Команда: DATAPLATFORM\n"
                    "Соискатель: \n"
                    "\n!Прикрепите резюме, напиши ФИО соискателя и поставь @ перед именем бота ниже!"
                    "\nOutstaff_connect_bot"
                )
            elif data == "template_PYTHON":
                template = (
                    "Позиция: SENIOR DEV PYTHON\n"
                    "Команда: DBAAS\n"
                    "Соискатель: \n"
                    "\n!Прикрепите резюме, напиши ФИО соискателя и поставь @ перед именем бота ниже!"
                    "\nOutstaff_connect_bot"
                )
            elif data == "template_Инструкция":
                template = (
                    "Ссылка на инструкцию: https://docs.google.com/document/d/11PR2EbZZVRao9ypcnoBzjYjRYNCI34a15rvYa0uIsdc/edit?tab=t.0\n"
                )
            else:
                template = "Шаблон не найден."

            # Отправляем шаблон пользователю
            send_telegram_message(chat_id, template)

            # Отвечаем на callback, чтобы убрать "часики" у пользователя
            callback_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
            requests.post(callback_url, json={"callback_query_id": callback['id']})

            return jsonify({"status": "callback_handled"}), 200

        # Проверяем, есть ли сообщение
        if 'message' not in update:
            app.logger.warning("⚠️ Нет ключа 'message' в update")
            return jsonify({"status": "no_message"}), 200

        message = update['message']
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        if not chat_id:
            app.logger.warning("⚠️ Нет chat_id")
            return jsonify({"status": "no_chat_id"}), 200

        # 📝 Получаем текст
        text = ""
        if 'text' in message:
            text = message['text']
        elif 'caption' in message:
            text = message['caption']
            app.logger.info(f"📎 Использую caption: {text}")
        else:
            app.logger.warning("⚠️ Ни text, ни caption не найдены")
            return jsonify({"status": "no_text"}), 200

        app.logger.info(f"📩 Получен текст: {repr(text)}")

        # 🆕 Обработка команды /start
        if text.startswith('/start'):
            help_text = "👋 Привет! Я помогу тебе быстро отправить резюме.\n\nНажми /template@Outstaff_connect_bot, чтобы выбрать шаблон."
            send_telegram_message(chat_id, help_text)
            return jsonify({"status": "start_sent"}), 200

        # 🆕 Обработка команды /template@Outstaff_connect_bot
        if text == "/template@Outstaff_connect_bot":
            inline_keyboard = [
                [{"text": "Тестировщик", "callback_data": "template_Тестировщик"}],
                [{"text": "DEVOPS", "callback_data": "template_devops"}],
                [{"text": "FRONTEND", "callback_data": "template_frontend"}],
                [{"text": "Архитектор", "callback_data": "template_Архитектор"}],
                [{"text": "PYTHON", "callback_data": "template_PYTHON"}]
            ]
            send_telegram_inline_keyboard(chat_id, "Выберите шаблон:", inline_keyboard)
            return jsonify({"status": "inline_template_sent"}), 200
            

        # 🆕 Проверяем, нужно ли боту реагировать
        should_respond = False
        chat_type = chat.get('type', '')

        if chat_type == 'private':
            should_respond = True
            app.logger.info("👤 Личный чат — обрабатываем сообщение")

        elif chat_type in ['group', 'supergroup']:
            bot_username = "@Outstaff_connect_bot"
            entities = message.get('entities', []) + message.get('caption_entities', [])

            for entity in entities:
                if entity.get('type') == 'mention' and 'offset' in entity and 'length' in entity:
                    try:
                        mention = text[entity['offset']:entity['offset'] + entity['length']]
                        if mention.lower() == bot_username.lower():
                            should_respond = True
                            text = text.replace(mention, "").strip()
                            app.logger.info(f"📢 Бот упомянут в группе — обрабатываем: {text}")
                            break
                    except Exception as e:
                        app.logger.warning(f"⚠️ Ошибка при извлечении mention: {e}")
                        continue

        if not should_respond:
            app.logger.info("🔕 Бот не упомянут — игнорируем сообщение")
            return jsonify({"status": "ignored"}), 200

        # 🔍 Парсим текст
        parsed_data = parse_message(text) if text else {}
        if not parsed_data:
            send_telegram_message(chat_id, "⚠️ Не удалось распознать данные. Отправьте в формате:\nПозиция: ...\nКоманда: ...\nСоискатель: ...\nКомпания: ...")
            return jsonify({"status": "parse_failed"}), 200

        # 🆕 Получаем название компании из базы по chat_id
        company_name = get_company_by_chat_id(chat_id)
        if company_name:
            parsed_data['Компания'] = company_name
            app.logger.info(f"🏢 Компания определена по chat_id {chat_id}: {company_name}")
        else:
            app.logger.info(f"ℹ️ Компания не найдена для chat_id {chat_id}, используем из сообщения")

        # 📄 Проверяем наличие файла в сообщении
        has_document = 'document' in message
        has_photo = 'photo' in message and len(message['photo']) > 0
        
        if not has_document and not has_photo:
            error_message = (
                "❌ Файл не найден в сообщении.\n\n"
                "Пожалуйста, прикрепите файл резюме к сообщению с данными.\n\n"
            )
            send_telegram_message(chat_id, error_message)
            app.logger.warning("⚠️ Сообщение не содержит файла - остановка обработки")
            return jsonify({"status": "no_file"}), 200

        # 📄 Обработка файла (документа)
        file_data = None
        if has_document:
            try:
                file_id = message['document']['file_id']
                original_file_name = message['document'].get('file_name', 'unknown_file')
                mime_type = message['document'].get('mime_type', 'application/octet-stream')
                
                applicant_name = parsed_data.get('Соискатель', 'unknown')
                position_name = parsed_data.get('Позиция', 'unknown')
                
                if '.' in original_file_name:
                    ext = original_file_name.rsplit('.', 1)[1]
                else:
                    ext = 'pdf'
                
                new_file_name = f"{applicant_name} - {position_name}.{ext}"
                
                file_path = get_telegram_file_path(file_id)
                if file_path:
                    file_content = download_file(file_path)
                    if file_content:
                        file_base64 = base64.b64encode(file_content).decode('utf-8')
                        file_data = {
                            "name": new_file_name,
                            "base64": file_base64,
                            "mimeType": mime_type
                        }
                        app.logger.info(f"📄 Файл переименован: {new_file_name}")
            except Exception as e:
                app.logger.error(f"❌ Ошибка обработки файла: {str(e)}")
                send_telegram_message(chat_id, "❌ Ошибка обработки файла. Попробуйте отправить снова.")
                return jsonify({"status": "file_processing_error"}), 200

        # 📄 Обработка фото (если отправлено как фото вместо документа)
        elif has_photo:
            try:
                # Берем фото наибольшего размера (последнее в массиве)
                photo = message['photo'][-1]
                file_id = photo['file_id']
                
                applicant_name = parsed_data.get('Соискатель', 'unknown')
                position_name = parsed_data.get('Позиция', 'unknown')
                new_file_name = f"{applicant_name} - {position_name}.jpg"
                
                file_path = get_telegram_file_path(file_id)
                if file_path:
                    file_content = download_file(file_path)
                    if file_content:
                        file_base64 = base64.b64encode(file_content).decode('utf-8')
                        file_data = {
                            "name": new_file_name,
                            "base64": file_base64,
                            "mimeType": "image/jpeg"
                        }
                        app.logger.info(f"📸 Фото обработано: {new_file_name}")
            except Exception as e:
                app.logger.error(f"❌ Ошибка обработки фото: {str(e)}")
                send_telegram_message(chat_id, "❌ Ошибка обработки фото. Попробуйте отправить файл как документ.")
                return jsonify({"status": "photo_processing_error"}), 200

        # 📤 Отправляем в Google Apps Script
        payload = {
            "data": parsed_data,
            "file": file_data,
            "chatId": chat_id  # Добавляем chatId в payload
        }

        try:
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

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        app.logger.error(f"💥 Ошибка в telegram_webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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
        lines = text.strip().split('\n')
        parsed = {}
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                parsed[key.strip()] = value.strip()
        
        required = ['Позиция', 'Команда', 'Соискатель']
        if all(key in parsed for key in required):
            return parsed
        else:
            app.logger.warning(f"❌ Не хватает полей. Распарсено: {parsed}")
            return None
    except Exception as e:
        app.logger.error(f"❌ Ошибка парсинга: {str(e)}")
        return None

# 🏢 Получает название компании по chat_id из Google Таблицы
def get_company_by_chat_id(chat_id):
    """Получает название компании из Google Таблицы по chat_id"""
    try:
        # Если URL для получения компании не настроен, возвращаем None
        if not COMPANY_SCRIPT_URL:
            app.logger.warning("⚠️ COMPANY_SCRIPT_URL не настроен, пропускаем определение компании")
            return None
            
        payload = {
            "action": "get_company",
            "chatId": str(chat_id)
        }
        
        response = requests.post(COMPANY_SCRIPT_URL, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success' and result.get('company'):
                return result.get('company')
            else:
                app.logger.warning(f"⚠️ Компания не найдена для chat_id {chat_id}: {result.get('message', 'Unknown error')}")
        
        return None
        
    except Exception as e:
        app.logger.error(f"❌ Ошибка получения компании по chat_id {chat_id}: {str(e)}")
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

# 📨 Отправляет сообщение с inline-клавиатурой
def send_telegram_inline_keyboard(chat_id, text, inline_keyboard):
    """Отправляет сообщение с inline-клавиатурой"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': {
            'inline_keyboard': inline_keyboard
        }
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        app.logger.error(f"❌ Не удалось отправить inline клавиатуру: {str(e)}")

# 🚀 Запуск сервера
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
