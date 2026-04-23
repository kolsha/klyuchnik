# klyuchnik

Telegram-бот (aiogram 3.x), который:

- приветствует нового участника одного конкретного чата или ответ на `/start`;
- отправляет текст (Markdown) + до 10 фото из папки `content/`;
- открепляет старое своё приветствие и закрепляет новое (чтобы в закрепе всегда была актуальная «доска»);
- показывает две inline-кнопки, каждая из которых открывает свой HTTP-замок;
- пропускает нажатия только от участников чата (`getChatMember` + TTL-кэш).

## Архитектура

```
Lock (Protocol)
  └─ HttpLock     ← один класс, два инстанса из конфига (разные url/headers/body/method)
LockRegistry      ← id → Lock
PinStateStore     ← JSON-файл, прячется за Protocol
MembershipChecker ← TTL-кэш поверх bot.get_chat_member
handlers/
  welcome         ← /start + new_chat_members → send + unpin + pin + save
  callbacks       ← callback_query → membership → lock.open → answer
```

Каждый модуль покрыт unit-тестами (TDD: сначала тест, затем код).

## Быстрый старт

```bash
# 1. Python 3.11+, создать venv
python -m venv .venv && source .venv/bin/activate

# 2. Установить в dev-режиме
pip install -e ".[dev]"

# 3. Настроить .env
cp .env.example .env
$EDITOR .env

# 4. Положить фото в content/photos/ (до 10 штук, .jpg/.png/.webp),
#    и отредактировать content/welcome.md (синтаксис: Telegram MarkdownV2!)

# 5. Запустить
python -m klyuchnik
```

## Настройка бота в Telegram

1. Создайте бота у [@BotFather](https://t.me/BotFather), получите `BOT_TOKEN`.
2. Отключите Privacy Mode: `/setprivacy` → Disable (чтобы бот видел новых участников).
3. Добавьте бота в ваш групповой чат и выдайте админ-права с правами «Pin messages» и «Delete messages».
4. Узнайте `CHAT_ID` (отрицательный для супергрупп) — например, через [@userinfobot](https://t.me/userinfobot) или `getUpdates`.
5. Заполните `.env` и запустите `python -m klyuchnik`.

## Тесты

```bash
pytest        # все юнит-тесты
pytest -v     # подробный вывод
ruff check .  # линт
mypy          # типы (strict)
```

## Содержимое

- `content/welcome.md` — текст приветствия, **MarkdownV2** (экранируйте `_*[]()~\`>#+-=|{}.!`).
- `content/photos/*.{jpg,png,webp}` — до 10 файлов, сортируются по имени. Первое фото несёт caption-текстом из welcome.md, если тот короче 1024 символов; иначе текст уходит отдельным сообщением.

## Добавить новый замок

1. Добавьте ещё один префикс (`LOCK_C_*`) в `.env`, класс `LockCSettings` в `config.py`, и инстанс `HttpLock(settings.lock_c.to_http_config())` в `bot.build_bot_and_dispatcher`.
2. Если замок не HTTP — реализуйте класс, удовлетворяющий `Lock` Protocol в `locks/base.py` (async `open() -> LockResult`). `LockRegistry` и `handlers/callbacks.py` не меняются.

## Замечания по безопасности

- `BOT_TOKEN` и `LOCK_*_HEADERS` — секреты; не коммитьте `.env`.
- Проверка членства — единственный барьер; если замки критичные, сделайте доп. whitelist по user_id.
- Опционально: rate-limit на кнопках (не в скоупе MVP).
