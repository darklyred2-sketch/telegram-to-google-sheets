@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()
        
        if 'message' not in update:
            app.logger.warning("⚠️ Нет ключа 'message' в update")
            return jsonify({"status": "no_message"}), 200

        message = update['message']
        chat_id = message.get('chat', {}).get('id')
        if not chat_id:
            app.logger.warning("⚠️ Нет chat_id")
            return jsonify({"status": "no_chat_id"}), 200

        # Получаем текст
        text = ""
        if 'text' in message:
            text = message['text']
        elif 'caption' in message:
            text = message['caption']
            app.logger.info(f"📎 Использую caption: {text}")
        else:
            app.logger.warning("⚠️ Ни text, ни caption не найдены")
            return jsonify({"status": "no_text"}), 200  # 👈 БЫЛО: не было return!

        app.logger.info(f"📩 Получен текст: {repr(text)}")

        # Проверяем, нужно ли отвечать
        should_respond = False

        if message['chat']['type'] == 'private':
            should_respond = True
            app.logger.info("👤 Личный чат — обрабатываем")

        elif message['chat']['type'] in ['group', 'supergroup']:
            bot_username = "@Outstaff_connect_bot"  # 🔥 ЗАМЕНИ НА СВОЁ ИМЯ БОТА
            entities = message.get('entities', []) + message.get('caption_entities', [])

            for entity in entities:
                if entity.get('type') == 'mention' and 'offset' in entity and 'length' in entity:
                    try:
                        mention = text[entity['offset']:entity['offset'] + entity['length']]
                        if mention.lower() == bot_username.lower():
                            should_respond = True
                            text = text.replace(mention, "").strip()
                            app.logger.info(f"📢 Бот упомянут: {text}")
                            break
                    except Exception as e:
                        app.logger.warning(f"⚠️ Ошибка при извлечении mention: {e}")
                        continue

        if not should_respond:
            app.logger.info("🔕 Игнорируем — бот не упомянут")
            return jsonify({"status": "ignored"}), 200  # 👈 БЫЛО: возможно, не было return

        # Обработка файла (если есть)
        file_data = None
        if 'document' in message:
            try:
                file_id = message['document']['file_id']
                file_name = message['document'].get('file_name', 'unknown_file')
                mime_type = message['document'].get('mime_type', 'application/octet-stream')
                
                file_path = get_telegram_file_path(file_id)
                if file_path:
                    file_content = download_file(file_path)
                    if file_content:
                        file_base64 = base64.b64encode(file_content).decode('utf-8')
                        file_data = {
                            "name": file_name,
                            "base64": file_base64,
                            "mimeType": mime_type
                        }
                        app.logger.info(f"📄 Файл получен: {file_name}")
            except Exception as e:
                app.logger.error(f"❌ Ошибка обработки файла: {str(e)}")

        # Парсим текст
        parsed_data = parse_message(text) if text else {}
        if not parsed_data:
            send_telegram_message(chat_id, "⚠️ Не удалось распознать данные. Формат:\nПозиция: ...\nКоманда: ...\nСоискатель: ...\nКомпания: ...")
            return jsonify({"status": "parse_failed"}), 200

        # Отправляем в Google Apps Script
        payload = {
            "data": parsed_data,
            "file": file_data
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

        return jsonify({"status": "ok"}), 200  # 👈 ГАРАНТИРОВАННЫЙ RETURN В КОНЦЕ

    except Exception as e:
        app.logger.error(f"💥 Необработанная ошибка: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
