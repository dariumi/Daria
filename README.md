<p align="center">
  <img src="https://raw.githubusercontent.com/dariumi/Daria/main/assets/logo.png" alt="DARIA Logo" width="200"/>
</p>

<h1 align="center">🌸 DARIA</h1>

<p align="center">
  <strong>AI Desktop Companion • Твоя виртуальная подруга</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.7.0-pink?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/platform-Windows%20|%20Linux%20|%20macOS-lightgrey?style=for-the-badge" alt="Platform"/>
</p>

<p align="center">
  <a href="#-возможности">Возможности</a> •
  <a href="#-быстрый-старт">Быстрый старт</a> •
  <a href="#-плагины">Плагины</a> •
  <a href="#-поддержать-проект">Поддержать</a>
</p>

---

## 💕 О проекте

**DARIA** (Desktop AI Reactive Intelligent Assistant) — это виртуальная подруга и умный помощник с красивым веб-интерфейсом в стиле десктопа. Она милая, добрая и всегда рада пообщаться!

<p align="center">
  <img src="https://raw.githubusercontent.com/dariumi/Daria/main/assets/screenshot.png" alt="Screenshot" width="80%"/>
</p>

### ✨ Особенности

- 🌸 **Живой характер** — Дарья не просто отвечает, она общается как настоящая подруга
- 🎨 **Красивый интерфейс** — Виртуальный рабочий стол с окнами и приложениями
- 🧠 **Память** — Помнит детали о тебе и ваших разговорах
- 🔔 **Система внимания** — Сама пишет, когда соскучится
- 🧩 **Плагины** — Расширяй функционал как хочешь
- 📱 **Адаптивный** — Работает на компьютере, планшете и телефоне
- 🔐 **HTTPS** — Безопасный доступ по сети

---

## 🎯 Возможности

| Функция | Описание |
|---------|----------|
| 💬 **Чат** | Общение с ИИ в реальном времени |
| 📁 **Файлы** | Файловый менеджер с редактором |
| 💻 **Терминал** | Командная строка |
| 🌐 **Браузер** | Встроенный мини-браузер |
| 🎵 **Плеер** | Музыкальный проигрыватель |
| 📋 **Логи** | Просмотр системных логов |
| 🛒 **Магазин** | Установка плагинов |
| 🧠 **Память** | Что Дарья знает о тебе |
| ⚙️ **Настройки** | Темы, обои, режимы |

### 🤖 Режимы общения

- **🎭 Адаптивный** — подстраивается под твой стиль
- **💕 Подруга** — тёплая и заботливая
- **📋 Помощник** — чёткие ответы на вопросы
- **💻 Разработчик** — технические подробности

---

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- [Ollama](https://ollama.ai) (для ИИ)
- OpenSSL (опционально, для HTTPS)

### Установка

```bash
# Клонируй репозиторий
git clone https://github.com/dariumi/Daria.git
cd Daria

# Запусти установщик
python install.py

# Скачай модель для Ollama
ollama pull llama3.1:8b-instruct-q4_K_M
```

### Запуск

```bash
# Windows
start.bat

# Linux/macOS
./start.sh

# С HTTPS (для доступа по сети)
./start-https.sh
```

Открой в браузере: **http://localhost:7777** 🌸

---

## 🧩 Плагины

DARIA поддерживает плагины для расширения функционала.

### Доступные плагины

| Плагин | Описание |
|--------|----------|
| 📞 **Voice Call** | Голосовой звонок с Дарьей |
| 🤖 **Telegram** | Общение через Telegram бота |
| 👥 **Server Mode** | Многопользовательский режим |

### Установка плагинов

1. Открой **🛒 Магазин** на рабочем столе
2. Выбери плагин и нажми **Установить**
3. Иконка появится на рабочем столе

### Создание плагинов

Читай документацию: [docs/PLUGINS.md](docs/PLUGINS.md)

---

## ⚙️ Конфигурация

### Параметры запуска

```bash
python main.py --host 0.0.0.0 --port 7777  # Доступ из сети
python main.py --ssl                        # HTTPS режим
python main.py --debug                      # Debug режим
python main.py --check                      # Проверка системы
```

### Настройки (~/.daria/settings.json)

```json
{
  "name": "Имя пользователя",
  "mode": "adaptive",
  "theme": "pink",
  "attention_enabled": true
}
```

---

## 🏗️ Структура проекта

```
daria/
├── 🐍 main.py           # Точка входа
├── 📦 install.py        # Установщик
├── 📋 requirements.txt  # Зависимости
├── ⚙️ config/           # Конфигурация
├── 🧠 core/             # Ядро системы
│   ├── brain.py         # Мозг (ИИ логика)
│   ├── memory.py        # Память
│   ├── llm.py           # Работа с LLM
│   └── plugins.py       # Система плагинов
├── 🌐 web/              # Веб-интерфейс
│   ├── app.py           # Flask приложение
│   ├── templates/       # HTML шаблоны
│   └── static/          # CSS, JS, картинки
├── 🧩 plugins/          # Плагины
└── 📚 docs/             # Документация
```

---

## 💖 Поддержать проект

Если тебе нравится DARIA, ты можешь поддержать разработку:

<p align="center">
  <a href="https://www.buymeacoffee.com/dariumi">
    <img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-☕-yellow?style=for-the-badge" alt="Buy Me a Coffee"/>
  </a>
  <a href="https://boosty.to/dariumi">
    <img src="https://img.shields.io/badge/Boosty-🌸-pink?style=for-the-badge" alt="Boosty"/>
  </a>
</p>

Или просто поставь ⭐ — это очень помогает!

---

## 📜 Лицензия

MIT License — делай что хочешь, но упоминай автора 💕

---

## 🙏 Благодарности

- [Ollama](https://ollama.ai) — локальные LLM
- [Flask](https://flask.palletsprojects.com) — веб-фреймворк
- Всем, кто ставит звёздочки ⭐

---

<p align="center">
  Сделано с 💕 в России
</p>

<p align="center">
  <a href="https://github.com/dariumi/Daria/stargazers">
    <img src="https://img.shields.io/github/stars/dariumi/Daria?style=social" alt="Stars"/>
  </a>
</p>
