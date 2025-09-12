#!/usr/bin/env python3
"""
Telegram Emoji Reactor → Google Sheets Updater by ID
Senior-level implementation with robust parsing, error handling, async, logging.
"""

import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from typing import Optional, Tuple

# --- Конфигурация ---
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
SHEET_NAME = os.getenv("SHEET_NAME", "Logs")

# Настройка логгера
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Google Sheets инициализация ---
def init_gspread() -> gspread.Worksheet:
    """Инициализирует подключение к Google Таблице."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sheet.worksheet(SHEET_NAME)
    return worksheet


def extract_id_from_text(text: str) -> Optional[str]:
    """
    Извлекает ID из текста сообщения.
    Поддерживает форматы:
      - "ID: 12345"
      - "ID=12345"
      - "12345"
    Возвращает строку ID или None, если не найден.
    """
    if not text:
        return None

    # Паттерны: "ID: 123", "ID=123", "123"
    patterns = [
        r'ID[:=]\s*(\d+)',   # ID: 123 или ID=123
        r'^\s*(\d+)\s*$',    # только цифры
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    logger.warning(f"Не удалось извлечь ID из сообщения: '{text}'")
    return None


def update_cell_by_id(worksheet: gspread.Worksheet, target_id: str, value: str) -> bool:
    """
    Находит строку по значению в столбце A (ID), обновляет ячейку в столбце H.
    Возвращает True, если обновление прошло успешно.
    """
    try:
        # Получаем все значения столбца A
        id_column = worksheet.col_values(1)  # Колонка A
        row_index = None

        for i, cell_value in enumerate(id_column, start=1):
            if cell_value.strip() == target_id:
                row_index = i
                break

        if not row_index:
            logger.warning(f"ID '{target_id}' не найден в столбце A.")
            return False

        # Обновляем ячейку H (8-й столбец) в найденной строке
        cell_h = f"H{row_index}"
        worksheet.update(cell_h, [[value]])
        logger.info(f"Обновлено: ID={target_id} → H{row_index}='{value}'")
        return True

    except Exception as e:
        logger.error(f"Ошибка при обновлении ячейки для ID {target_id}: {e}", exc_info=True)
        return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает сообщение и проверяет реакции 👍/👎."""
    if not update.message:
        return

    message = update.message
    chat_id = message.chat_id
    message_id = message.message_id
    text = message.text or ""
    user = message.from_user
    username = user.username or f"{user.first_name} {user.last_name}".strip()

    # Извлекаем ID из текста сообщения
    target_id = extract_id_from_text(text)
    if not target_id:
        logger.debug(f"Сообщение без распознанного ID: '{text}'")
        return

    # Получаем реакции на сообщение
    try:
        reactions = await context.bot.get_message_reactions(chat_id, message_id)
    except Exception as e:
        logger.error(f"Ошибка получения реакций: {e}")
        return

    # Логика реакций
    emoji_to_value = {
        "👍": "TEST",
        "👎": "LOW SKILL"
    }

    for reaction in reactions:
        emoji = reaction.emoji
        if emoji in emoji_to_value:
            value = emoji_to_value[emoji]
            logger.info(f"Поймана реакция '{emoji}' на сообщение с ID={target_id} от @{username}")

            success = update_cell_by_id(init_gspread(), target_id, value)
            if success:
                logger.info(f"Успешно обновлено: ID={target_id} → {value}")
            else:
                logger.warning(f"Не удалось обновить ID={target_id}")
            break  # Обрабатываем только первую подходящую реакцию


def main() -> None:
    """Запускает бота."""
    if not all([TELEGRAM_BOT_TOKEN, GOOGLE_SHEET_ID, CREDENTIALS_FILE]):
        logger.critical("Отсутствуют обязательные переменные окружения!")
        exit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчик всех сообщений (для получения реакций)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен. Ожидает сообщения с ID и реакций 👍/👎...")
    app.run_polling()


if __name__ == "__main__":
    main()
