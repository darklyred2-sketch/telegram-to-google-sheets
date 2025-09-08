# 🤖 Telegram → Google Sheets Автоматизация

Автоматически добавляет данные из Telegram-сообщений в Google Таблицу.

## 🚀 Как задеплоить на Render

1. **Создай Telegram-бота** через [@BotFather](https://t.me/BotFather) → получи `TELEGRAM_TOKEN`.
2. **Создай Google Apps Script** → разверни как веб-приложение → получи `APPS_SCRIPT_URL`.
3. **Зарегистрируйся на [Render.com](https://render.com)**.
4. Нажми кнопку **«New Web Service»**.
5. Подключи этот репозиторий.
6. В настройках добавь переменные окружения:
   - `8420537529:AAEPBPMlHAaBnIETk_EhypH44YAB5GviuxE` — токен бота
   - `[APPS_SCRIPT_URL](https://script.google.com/macros/s/AKfycbxxFZwKnusLlec8XJtKd68GjsTj4zk5KCEfpEkC78mMpS7LyvWgtLhXGhbt-1s3E_nloA/exec)` — URL из Google Apps Script
7. Нажми **«Create Web Service»** → жди ~1 минуту.
8. После деплоя открой в браузере:
