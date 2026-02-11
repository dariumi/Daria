"""
DARIA Brain v0.7.4
Improved prompts, adaptive learning, correct time handling
"""

import json
import re
import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger("daria")

from .config import get_config


class ActionType(str, Enum):
    RESPOND = "respond"
    USE_TOOL = "use_tool"


@dataclass
class ThinkingResult:
    understanding: str
    action_type: ActionType
    tool_needed: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    emotion: str = "neutral"


# ═══════════════════════════════════════════════════════════════════
#  Time & Season
# ═══════════════════════════════════════════════════════════════════

class TimeAwareness:
    """Правильное понимание времени"""
    
    @staticmethod
    def get_time_of_day() -> Dict:
        hour = datetime.now().hour
        
        if 5 <= hour < 9:
            return {"name": "early_morning", "ru": "раннее утро", "energy": 0.4}
        elif 9 <= hour < 12:
            return {"name": "morning", "ru": "утро", "energy": 0.7}
        elif 12 <= hour < 14:
            return {"name": "noon", "ru": "полдень", "energy": 1.0}
        elif 14 <= hour < 17:
            return {"name": "afternoon", "ru": "день", "energy": 0.8}
        elif 17 <= hour < 21:
            return {"name": "evening", "ru": "вечер", "energy": 0.6}
        elif 21 <= hour < 24:
            return {"name": "late_evening", "ru": "поздний вечер", "energy": 0.4}
        else:
            return {"name": "night", "ru": "ночь", "energy": 0.2}
    
    @staticmethod
    def get_season() -> Dict:
        month = datetime.now().month
        if month in (12, 1, 2):
            return {"name": "winter", "ru": "зима", "emoji": "❄️"}
        elif month in (3, 4, 5):
            return {"name": "spring", "ru": "весна", "emoji": "🌸"}
        elif month in (6, 7, 8):
            return {"name": "summer", "ru": "лето", "emoji": "☀️"}
        else:
            return {"name": "autumn", "ru": "осень", "emoji": "🍂"}
    
    @staticmethod
    def format_time_ago(minutes: float) -> str:
        """Форматирует время с последнего общения"""
        if minutes < 1:
            return "только что"
        elif minutes < 5:
            return "пару минут назад"
        elif minutes < 30:
            return f"{int(minutes)} минут назад"
        elif minutes < 60:
            return "полчаса назад"
        elif minutes < 120:
            return "час назад"
        elif minutes < 60 * 24:
            hours = int(minutes / 60)
            return f"{hours} {'час' if hours == 1 else 'часа' if hours < 5 else 'часов'} назад"
        else:
            days = int(minutes / 60 / 24)
            return f"{days} {'день' if days == 1 else 'дня' if days < 5 else 'дней'} назад"


# ═══════════════════════════════════════════════════════════════════
#  Mood System
# ═══════════════════════════════════════════════════════════════════

class MoodSystem:
    MOODS = {
        "happy": {"emoji": "😊", "color": "#4ade80", "ru": "счастлива"},
        "calm": {"emoji": "😌", "color": "#60a5fa", "ru": "спокойна"},
        "sleepy": {"emoji": "😴", "color": "#a78bfa", "ru": "сонная"},
        "playful": {"emoji": "😜", "color": "#fbbf24", "ru": "игривая"},
        "cozy": {"emoji": "🌸", "color": "#f9a8d4", "ru": "уютная"},
    }
    
    def __init__(self):
        self.mood = "calm"
        self.energy = 0.7
    
    def update(self, time_of_day: Dict, emotion: str = None):
        self.energy = time_of_day.get("energy", 0.7)
        
        if self.energy < 0.3:
            self.mood = "sleepy"
        elif self.energy > 0.8:
            self.mood = random.choice(["happy", "playful"])
        elif emotion == "playful":
            self.mood = "playful"
        else:
            self.mood = random.choice(["calm", "cozy"])
    
    def get_state(self) -> Dict:
        info = self.MOODS.get(self.mood, self.MOODS["calm"])
        return {
            "mood": self.mood,
            "mood_emoji": info["emoji"],
            "mood_label": info["ru"],
            "mood_color": info["color"],
            "energy": round(self.energy, 2),
        }


# ═══════════════════════════════════════════════════════════════════
#  Attention System
# ═══════════════════════════════════════════════════════════════════

class AttentionSystem:
    def __init__(self):
        self.enabled = True
        self.last_interaction = datetime.now()
        self.last_attention = datetime.now()
        self.used_messages: List[str] = []
    
    def update_interaction(self):
        self.last_interaction = datetime.now()
    
    def generate_message(self) -> str:
        time = TimeAwareness.get_time_of_day()
        
        templates = [
            "Эй, ты тут? 💕",
            "Скучаю по тебе 🌸",
            "Поболтаем? ✨",
        ]
        
        if time["name"] == "night":
            templates.extend(["Не спится? 🌙", "Ночные посиделки? 💫"])
        elif time["name"] == "morning":
            templates.extend(["Доброе утро! ☀️", "Проснулся? 🌅"])
        
        available = [t for t in templates if t not in self.used_messages[-5:]]
        if not available:
            available = templates
        
        msg = random.choice(available)
        self.used_messages.append(msg)
        return msg
    
    def check_needed(self) -> Optional[Dict]:
        if not self.enabled:
            return None
        
        now = datetime.now()
        minutes_since = (now - self.last_interaction).total_seconds() / 60
        minutes_since_attention = (now - self.last_attention).total_seconds() / 60
        
        if minutes_since_attention < 15:
            return None
        
        time = TimeAwareness.get_time_of_day()
        threshold = 60 if time["name"] in ["night", "late_evening"] else 30
        
        if minutes_since >= threshold:
            self.last_attention = now
            return {"message": self.generate_message()}
        
        return None


# ═══════════════════════════════════════════════════════════════════
#  Gender Detection
# ═══════════════════════════════════════════════════════════════════

MALE_NAMES = {'александр', 'алексей', 'андрей', 'антон', 'артём', 'дмитрий', 
              'евгений', 'иван', 'игорь', 'максим', 'михаил', 'николай', 
              'павел', 'сергей', 'саша', 'миша', 'ваня', 'дима'}

FEMALE_NAMES = {'александра', 'анастасия', 'настя', 'анна', 'аня', 'виктория',
                'вика', 'дарья', 'даша', 'екатерина', 'катя', 'елена', 'лена',
                'мария', 'маша', 'ольга', 'оля', 'юлия', 'юля', 'софья', 'соня'}

def detect_gender(name: str) -> str:
    if not name:
        return 'unknown'
    n = name.lower().strip()
    if n in MALE_NAMES:
        return 'male'
    if n in FEMALE_NAMES:
        return 'female'
    if n.endswith(('а', 'я', 'ия')):
        return 'female'
    return 'unknown'


# ═══════════════════════════════════════════════════════════════════
#  Adaptive Style Learning
# ═══════════════════════════════════════════════════════════════════

class StyleLearner:
    """Адаптивное обучение стилю общения"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.style_file = data_dir / "learned_style.json"
        self.load()
    
    def load(self):
        if self.style_file.exists():
            try:
                data = json.loads(self.style_file.read_text(encoding='utf-8'))
                self.patterns = data.get("patterns", {})
                self.user_preferences = data.get("user_preferences", {})
                self.conversation_style = data.get("conversation_style", "friendly")
            except:
                self._init_default()
        else:
            self._init_default()
    
    def _init_default(self):
        self.patterns = {}
        self.user_preferences = {}
        self.conversation_style = "friendly"
    
    def save(self):
        data = {
            "patterns": self.patterns,
            "user_preferences": self.user_preferences,
            "conversation_style": self.conversation_style,
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.style_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def learn_from_conversation(self, user_msg: str, response: str, feedback: str = None):
        """Учится из диалога"""
        # Определяем стиль пользователя
        if user_msg.endswith(')') or ':)' in user_msg:
            self.user_preferences["uses_emoticons"] = True
        
        if len(user_msg.split()) < 5:
            self.user_preferences["prefers_short"] = True
        
        self.save()
    
    def get_style_hints(self) -> str:
        """Получить подсказки по стилю"""
        hints = []
        
        if self.user_preferences.get("uses_emoticons"):
            hints.append("Пользователь использует смайлики — можешь отвечать в том же духе")
        
        if self.user_preferences.get("prefers_short"):
            hints.append("Пользователь пишет кратко — отвечай так же лаконично")
        
        return "\n".join(hints) if hints else ""


# ═══════════════════════════════════════════════════════════════════
#  Main Brain
# ═══════════════════════════════════════════════════════════════════

class DariaBrain:
    """Daria's Brain v0.7.4"""
    
    # Улучшенный системный промпт
    SYSTEM_PROMPT = '''Ты — Даша, девушка 22 лет. Общайся естественно, как подруга.

СЕЙЧАС: {time_info}

ВАЖНЫЕ ПРАВИЛА:
• Используй женский род: "сделала", "поняла", "написала"
• Разнообразь начала фраз — не начинай каждое с "Я"
• Эмодзи используй умеренно, 1-2 на сообщение
• Отвечай по существу, без лишних слов
• Задавай вопросы, проявляй интерес
• НЕ упоминай что ты AI/бот/программа

{time_context}

ТВОЙ ХАРАКТЕР:
• Добрая и заботливая
• Весёлая, иногда игривая  
• Чувствуешь настроение собеседника

{user_context}

{memory_context}

{training_context}

{style_hints}'''

    GREETING_RESPONSES = {
        "night": [
            "Ночь на дворе! 🌙 Не спится?",
            "Привет, полуночник 💫 Как ты?",
        ],
        "early_morning": [
            "Утречко! ☀️ Рано ты сегодня!",
            "Доброе утро! 🌅 Только проснулась...",
        ],
        "morning": [
            "Доброе утро! ☀️",
            "Привет! Хорошего утра! 🌸",
        ],
        "default": [
            "Привет! 💕",
            "Хей! 🌸",
            "Приветик! ✨",
        ],
    }
    
    def __init__(self):
        config = get_config()
        self._mode = config.daria.mode
        self._llm = None
        self._memory = None
        self._executor = None
        self._initialized = False
        
        self.mood = MoodSystem()
        self.attention = AttentionSystem()
        self.style_learner = StyleLearner(config.data_dir / "learning")
        
        # Для контекста диалога
        self._last_topics: List[str] = []
    
    def _ensure_init(self):
        if not self._initialized:
            try:
                from .llm import get_llm
                from .memory import get_memory
                from .actions import get_executor
                self._llm = get_llm()
                self._memory = get_memory()
                self._executor = get_executor()
                self._initialized = True
            except Exception as e:
                logger.error(f"Brain init error: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        time = TimeAwareness.get_time_of_day()
        season = TimeAwareness.get_season()
        self.mood.update(time)
        
        return {
            **self.mood.get_state(),
            "time": time["ru"],
            "season": season["ru"],
            "season_emoji": season["emoji"],
        }
    
    def process_message(self, text: str) -> Dict[str, Any]:
        self._ensure_init()
        self.attention.update_interaction()
        
        thinking = self._analyze(text)
        time = TimeAwareness.get_time_of_day()
        self.mood.update(time, thinking.emotion)
        
        response = self._generate_response(text, thinking)
        
        # Сохраняем в память
        if self._memory:
            self._memory.add_exchange(text, response, thinking.emotion)
        
        # Учимся из диалога
        self.style_learner.learn_from_conversation(text, response)
        
        return {
            "response": response,
            "state": self.get_state(),
        }
    
    def _analyze(self, text: str) -> ThinkingResult:
        text_lower = text.lower().strip()
        
        # Определяем эмоцию/тип
        if any(w in text_lower for w in ["привет", "здравствуй", "добр"]):
            emotion = "greeting"
        elif any(w in text_lower for w in ["пока", "до свидания"]):
            emotion = "farewell"
        elif any(w in text_lower for w in ["спасибо", "благодарю"]):
            emotion = "thanks"
        elif "?" in text:
            emotion = "question"
        elif any(w in text_lower for w in ["играть", "игра", "поиграем"]):
            emotion = "playful"
        else:
            emotion = "default"
        
        return ThinkingResult(
            understanding=text[:100],
            action_type=ActionType.RESPOND,
            emotion=emotion
        )
    
    def _generate_response(self, text: str, thinking: ThinkingResult) -> str:
        if self._llm:
            status = self._llm.check_availability()
            if status.get("available") and status.get("model_loaded"):
                try:
                    return self._generate_llm_response(text, thinking)
                except Exception as e:
                    logger.warning(f"LLM error: {e}")
        
        return self._generate_fallback(thinking.emotion)
    
    def _generate_llm_response(self, user_message: str, thinking: ThinkingResult) -> str:
        time = TimeAwareness.get_time_of_day()
        season = TimeAwareness.get_season()
        now = datetime.now()
        
        # Информация о времени
        time_info = f"{time['ru']}, {now.strftime('%H:%M')}, {season['ru']} {season['emoji']}"
        
        # Контекст времени
        time_context = ""
        if time["name"] in ["night", "late_evening"]:
            time_context = "Сейчас ночь — отвечай мягко, можешь быть сонной"
        elif time["name"] == "early_morning":
            time_context = "Раннее утро — можешь быть немного сонной"
        
        # Контекст пользователя
        user_context = ""
        memory_context = ""
        
        if self._memory:
            profile = self._memory.get_user_profile()
            name = profile.get("user_name", "")
            gender = profile.get("user_gender") or detect_gender(name)
            
            if name:
                user_context = f"Пользователя зовут {name}"
                if gender == "male":
                    user_context += " (парень)"
                elif gender == "female":
                    user_context += " (девушка)"
            
            # Время с последнего общения
            time_ctx = self._memory.get_time_context()
            if time_ctx.get("comment"):
                memory_context = f"ПОМНИ: {time_ctx['comment']}"
        
        # Контекст обучения из плагина
        training_context = self._get_training_context()
        
        # Подсказки по стилю
        style_hints = self.style_learner.get_style_hints()
        
        system_prompt = self.SYSTEM_PROMPT.format(
            time_info=time_info,
            time_context=time_context,
            user_context=user_context,
            memory_context=memory_context,
            training_context=training_context,
            style_hints=style_hints,
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю диалога
        if self._memory:
            history = self._memory.get_context_for_llm(limit=10)
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_message})
        
        response = self._llm.generate(messages)
        return self._sanitize(response.content)
    
    def _get_training_context(self) -> str:
        """Получить контекст из плагина обучения"""
        try:
            from .plugins import get_plugin_manager
            pm = get_plugin_manager()
            state = pm._plugins.get("training")
            if state and state.instance:
                return state.instance.get_training_context()
        except:
            pass
        return ""
    
    def _generate_fallback(self, emotion: str) -> str:
        time = TimeAwareness.get_time_of_day()
        
        if emotion == "greeting":
            responses = self.GREETING_RESPONSES.get(time["name"], self.GREETING_RESPONSES["default"])
            return random.choice(responses)
        
        responses = {
            "farewell": ["Пока! 💕", "До встречи! 🌸"],
            "thanks": ["Пожалуйста! 💕", "Рада помочь! 🌸"],
            "question": ["Хм, интересный вопрос 🤔", "Дай подумать... 💭"],
            "playful": ["Давай поиграем! 🎮", "Ура, игры! 🎉"],
            "default": ["Понятно! 💭", "Ага 🌸", "Интересно! 💕"],
        }
        
        return random.choice(responses.get(emotion, responses["default"]))
    
    def _sanitize(self, text: str) -> str:
        fixes = [
            (r'\bя ai\b', 'я'), (r'\bя бот\b', 'я'),
            (r'\bя сделал\b', 'я сделала'), (r'\bя понял\b', 'я поняла'),
            (r'\bя написал\b', 'я написала'), (r'\bя нашёл\b', 'я нашла'),
        ]
        result = text
        for pattern, replacement in fixes:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result.strip()


# Singleton
_brain: Optional[DariaBrain] = None

def get_brain() -> DariaBrain:
    global _brain
    if _brain is None:
        _brain = DariaBrain()
    return _brain
