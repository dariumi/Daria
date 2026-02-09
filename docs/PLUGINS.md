# 🧩 Руководство по созданию плагинов DARIA

## Содержание

1. [Введение](#введение)
2. [Структура плагина](#структура-плагина)
3. [Манифест plugin.yaml](#манифест-pluginyaml)
4. [Plugin API](#plugin-api)
5. [Интеграция с интерфейсом](#интеграция-с-интерфейсом)
6. [Хуки и события](#хуки-и-события)
7. [WebRTC поддержка](#webrtc-поддержка)
8. [Примеры](#примеры)

---

## Введение

Плагины DARIA позволяют расширять функциональность без изменения ядра. Плагины могут:

- ✅ Добавлять иконки на рабочий стол
- ✅ Открывать собственные окна
- ✅ Перехватывать и модифицировать сообщения чата
- ✅ Получать доступ к памяти и LLM
- ✅ Использовать WebRTC для аудио/видео
- ✅ Хранить собственные данные

---

## Структура плагина

```
my-plugin/
├── plugin.yaml          # Манифест (обязательно)
├── main.py              # Точка входа (обязательно)
├── templates/           # HTML шаблоны
│   └── window.html      # Шаблон окна плагина
├── static/              # Статические файлы
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── plugin.js
│   └── img/
└── data/                # Данные плагина (создаётся автоматически)
```

---

## Манифест plugin.yaml

```yaml
# ═══════════════════════════════════════════════════════════════════
#  Идентификация
# ═══════════════════════════════════════════════════════════════════
id: my-plugin                    # Уникальный ID (латиница, дефисы)
name: Мой плагин                 # Отображаемое имя
description: Описание плагина    # Краткое описание
version: 1.0.0                   # Версия (semver)
author: Your Name                # Автор
license: MIT                     # Лицензия

# ═══════════════════════════════════════════════════════════════════
#  Внешний вид
# ═══════════════════════════════════════════════════════════════════
icon: 🔧                         # Иконка (emoji)
category: utilities              # Категория:
                                 #   - communication
                                 #   - creative
                                 #   - productivity
                                 #   - utilities
                                 #   - games
                                 #   - other

# ═══════════════════════════════════════════════════════════════════
#  Интеграция с рабочим столом
# ═══════════════════════════════════════════════════════════════════
has_desktop_icon: true           # Показывать иконку на рабочем столе
desktop_icon: 🔧                 # Иконка для рабочего стола
desktop_title: Мой плагин        # Название под иконкой

# ═══════════════════════════════════════════════════════════════════
#  Окно плагина
# ═══════════════════════════════════════════════════════════════════
has_window: true                 # Поддержка окна
window_title: Мой плагин         # Заголовок окна
window_size:
  width: 400
  height: 300
window_template: window.html     # Шаблон окна

# ═══════════════════════════════════════════════════════════════════
#  Точки входа
# ═══════════════════════════════════════════════════════════════════
entry_point: main.py             # Главный Python файл
main_class: Plugin               # Имя класса плагина

# ═══════════════════════════════════════════════════════════════════
#  Ресурсы
# ═══════════════════════════════════════════════════════════════════
static_dir: static               # Папка статических файлов
templates_dir: templates         # Папка шаблонов

# ═══════════════════════════════════════════════════════════════════
#  Зависимости
# ═══════════════════════════════════════════════════════════════════
dependencies: []                 # Зависимости от других плагинов
python_dependencies:             # Python пакеты
  - requests
  - pillow

# ═══════════════════════════════════════════════════════════════════
#  Возможности (capabilities)
# ═══════════════════════════════════════════════════════════════════
capabilities:
  - chat_hook        # Перехват сообщений чата
  - brain_hook       # Хук в мозг
  - memory_access    # Доступ к памяти
  - llm_access       # Прямой доступ к LLM
  - file_system      # Файловая система
  - network          # Сетевые запросы
  - notifications    # Системные уведомления
  - audio            # Аудио (запись/воспроизведение)
  - webrtc           # WebRTC поддержка

# ═══════════════════════════════════════════════════════════════════
#  Метаданные для магазина
# ═══════════════════════════════════════════════════════════════════
homepage: https://example.com
repository_url: https://github.com/user/plugin
preview_image: preview.png       # Превью в магазине
screenshots:                     # Скриншоты
  - screenshot1.png
  - screenshot2.png
```

---

## Plugin API

### Базовый класс плагина

```python
# main.py
from core.plugins import DariaPlugin, PluginAPI, PluginManifest

class Plugin(DariaPlugin):
    """Мой плагин для DARIA"""
    
    def on_load(self):
        """Вызывается при загрузке плагина"""
        self.api.log("Плагин загружен!")
        
        # Инициализация
        self.counter = self.api.load_data("counter", 0)
    
    def on_unload(self):
        """Вызывается при выгрузке"""
        self.api.save_data("counter", self.counter)
        self.api.log("Плагин выгружен")
    
    def on_enable(self):
        """Вызывается при включении"""
        pass
    
    def on_disable(self):
        """Вызывается при отключении"""
        pass
```

### PluginAPI - доступные методы

#### Доступ к ядру

```python
# Отправить сообщение Дарье
response = self.api.send_message("Привет!")
print(response["response"])  # Ответ Дарьи

# Добавить в историю разговора
self.api.add_to_conversation("Мой вопрос", "Ответ")
```

#### Работа с памятью

```python
# Запомнить что-то
memory_id = self.api.remember("Важная информация", importance=0.8)

# Вспомнить
memories = self.api.recall("информация", limit=5)
for mem in memories:
    print(mem["content"])

# Профиль пользователя
profile = self.api.get_user_profile()
name = profile.get("user_name", "Друг")

# Сохранить факт
self.api.store_fact("favorite_color", "синий")
```

#### Прямой доступ к LLM

```python
# Простая генерация
messages = [
    {"role": "system", "content": "Ты помощник"},
    {"role": "user", "content": "Расскажи анекдот"}
]
response = self.api.generate(messages, temperature=0.9)

# С контекстом разговора
response = self.api.generate_with_context(
    "Что мы обсуждали?", 
    include_history=True
)
```

#### Хранение данных плагина

```python
# Путь к папке данных плагина
data_path = self.api.get_data_path()

# Сохранить данные
self.api.save_data("settings", {"theme": "dark", "volume": 80})

# Загрузить данные
settings = self.api.load_data("settings", {"theme": "light"})
```

#### Логирование

```python
self.api.log("Информация", level="info")
self.api.log("Предупреждение", level="warning")
self.api.log("Ошибка", level="error")
```

#### URL для ресурсов

```python
# URL для статических файлов плагина
css_url = self.api.get_static_url("css/style.css")
# => /plugins/my-plugin/static/css/style.css

# Путь к шаблону
template = self.api.get_template_path("window.html")
```

---

## Интеграция с интерфейсом

### Окно плагина

```python
class Plugin(DariaPlugin):
    
    def on_window_open(self):
        """Вызывается при открытии окна плагина"""
        return {
            "title": "Добро пожаловать!",
            "user_name": self.api.get_user_profile().get("user_name", ""),
            "counter": self.counter,
        }
    
    def on_window_action(self, action: str, data: dict):
        """Обработка действий из окна"""
        
        if action == "increment":
            self.counter += 1
            return {"counter": self.counter}
        
        elif action == "send_message":
            text = data.get("text", "")
            response = self.api.send_message(text)
            return {"response": response["response"]}
        
        elif action == "get_status":
            return {"status": "active", "counter": self.counter}
        
        return {"error": "Unknown action"}
```

### HTML шаблон окна (templates/window.html)

```html
<div class="plugin-window" id="my-plugin">
    <div class="plugin-header">
        <h3>{{ title }}</h3>
    </div>
    
    <div class="plugin-content">
        <p>Привет, <span id="user-name">{{ user_name }}</span>!</p>
        <p>Счётчик: <span id="counter">{{ counter }}</span></p>
        
        <button onclick="pluginAction('increment')">+1</button>
        
        <div class="chat-section">
            <input type="text" id="message-input" placeholder="Сообщение...">
            <button onclick="sendMessage()">Отправить</button>
        </div>
        
        <div id="response"></div>
    </div>
</div>

<script>
// Глобальная функция для вызова действий плагина
async function pluginAction(action, data = {}) {
    const response = await fetch('/api/plugins/my-plugin/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action, data})
    });
    const result = await response.json();
    
    // Обновить UI
    if (result.counter !== undefined) {
        document.getElementById('counter').textContent = result.counter;
    }
    
    return result;
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text) return;
    
    input.value = '';
    const result = await pluginAction('send_message', {text});
    document.getElementById('response').textContent = result.response;
}
</script>

<style>
.plugin-window {
    padding: 16px;
}
.plugin-header h3 {
    margin: 0 0 16px;
    color: var(--primary);
}
.chat-section {
    display: flex;
    gap: 8px;
    margin-top: 16px;
}
.chat-section input {
    flex: 1;
    padding: 8px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background: var(--bg-input);
    color: var(--text-primary);
}
</style>
```

---

## Хуки и события

### Хук сообщений чата

```python
class Plugin(DariaPlugin):
    
    def on_chat_message(self, message: str) -> str | None:
        """
        Перехват входящего сообщения.
        Вернуть модифицированное сообщение или None.
        """
        # Пример: добавить контекст
        if "погода" in message.lower():
            return f"{message} (пользователь спрашивает о погоде)"
        return None
    
    def on_chat_response(self, message: str, response: str) -> str | None:
        """
        Перехват ответа Дарьи.
        Вернуть модифицированный ответ или None.
        """
        # Пример: добавить подпись
        if self.add_signature:
            return f"{response}\n\n— Отправлено через мой плагин"
        return None
```

### События

```python
# Отправить событие другим плагинам
self.api.emit_event("my_custom_event", {"data": "value"})

# Подписаться на событие (в PluginManager)
# plugins.subscribe_event("my_custom_event", handler)
```

---

## WebRTC поддержка

Для плагинов с аудио/видео связью:

```python
class VoicePlugin(DariaPlugin):
    
    def get_webrtc_config(self):
        """Конфигурация WebRTC"""
        return {
            "iceServers": [
                {"urls": "stun:stun.l.google.com:19302"}
            ],
            "audio": True,
            "video": False,
        }
    
    def on_webrtc_message(self, msg_type: str, data: dict):
        """Обработка WebRTC сигналов"""
        
        if msg_type == "offer":
            # Обработать SDP offer
            return self.create_answer(data["sdp"])
        
        elif msg_type == "ice-candidate":
            # Добавить ICE кандидата
            self.add_ice_candidate(data)
            return {"status": "ok"}
        
        elif msg_type == "audio-data":
            # Получены аудио данные
            text = self.speech_to_text(data["audio"])
            response = self.api.send_message(text)
            audio = self.text_to_speech(response["response"])
            return {"audio": audio, "text": response["response"]}
```

### JavaScript для WebRTC

```javascript
class PluginWebRTC {
    constructor(pluginId) {
        this.pluginId = pluginId;
        this.pc = null;
        this.localStream = null;
    }
    
    async init() {
        // Получить конфигурацию
        const config = await this.getConfig();
        
        // Создать RTCPeerConnection
        this.pc = new RTCPeerConnection(config);
        
        // Получить микрофон
        this.localStream = await navigator.mediaDevices.getUserMedia({
            audio: true,
            video: false
        });
        
        // Добавить трек
        this.localStream.getTracks().forEach(track => {
            this.pc.addTrack(track, this.localStream);
        });
        
        // Обработка ICE кандидатов
        this.pc.onicecandidate = e => {
            if (e.candidate) {
                this.signal("ice-candidate", e.candidate);
            }
        };
    }
    
    async signal(type, data) {
        const response = await fetch(`/api/webrtc/${this.pluginId}/signal`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({type, data})
        });
        return response.json();
    }
    
    async call() {
        const offer = await this.pc.createOffer();
        await this.pc.setLocalDescription(offer);
        
        const response = await this.signal("offer", {sdp: offer.sdp});
        
        await this.pc.setRemoteDescription(
            new RTCSessionDescription({type: "answer", sdp: response.data.sdp})
        );
    }
}
```

---

## Примеры

### Минимальный плагин

```python
# main.py
from core.plugins import DariaPlugin

class Plugin(DariaPlugin):
    def on_load(self):
        self.api.log("Hello from my plugin!")
```

```yaml
# plugin.yaml
id: hello-plugin
name: Hello Plugin
description: Простой пример плагина
version: 1.0.0
author: Me
icon: 👋
```

### Плагин с окном

См. пример в `plugins/voice-call/`

### Плагин-хук чата

```python
from core.plugins import DariaPlugin

class Plugin(DariaPlugin):
    def on_load(self):
        self.emoji_mode = True
    
    def on_chat_response(self, message, response):
        if self.emoji_mode:
            # Добавляем эмодзи в конец каждого ответа
            return f"{response} ✨"
        return None
```

---

## Публикация плагина

1. Создайте репозиторий для плагина
2. Добавьте плагин в каталог: https://github.com/dariumi/Daria-Plagins
3. Создайте PR с добавлением в `catalog.yaml`

### Формат catalog.yaml

```yaml
plugins:
  - id: my-plugin
    name: Мой плагин
    description: Описание
    version: 1.0.0
    author: Your Name
    icon: 🔧
    category: utilities
    has_desktop_icon: true
    has_window: true
    capabilities:
      - memory_access
    url: https://github.com/user/my-plugin
    preview_image: https://raw.githubusercontent.com/user/my-plugin/main/preview.png
```

---

## FAQ

**Q: Где хранятся данные плагина?**
A: В `~/.daria/plugins/<plugin-id>/data/`

**Q: Как отладить плагин?**
A: Запустите DARIA с `--debug` и используйте `self.api.log()`

**Q: Можно ли использовать внешние Python пакеты?**
A: Да, укажите их в `python_dependencies` в манифесте

**Q: Как обновить плагин?**
A: Удалите и установите заново, или замените файлы вручную

---

*Создано с 💕 для DARIA v0.6.2*
