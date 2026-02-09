"""
DARIA Brain v0.7.3
Seasons, games, environment control, improved prompts
"""

import json
import re
import logging
import random
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger("daria")

from .config import get_config
from .llm import get_llm, LLMError
from .memory import get_memory
from .actions import get_executor


class ActionType(str, Enum):
    RESPOND = "respond"
    USE_TOOL = "use_tool"
    ENVIRONMENT = "environment"


@dataclass
class ThinkingResult:
    understanding: str
    action_type: ActionType
    tool_needed: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    should_remember: List[str] = field(default_factory=list)
    emotion: str = "neutral"
    env_action: Optional[Dict] = None


# ═══════════════════════════════════════════════════════════════════
#  Time & Season Awareness
# ═══════════════════════════════════════════════════════════════════

class TimeAwareness:
    """Понимание времени суток и сезона"""
    
    SEASONS = {
        (12, 1, 2): {"name": "winter", "ru": "зима", "emoji": "❄️", "mood_boost": -0.1},
        (3, 4, 5): {"name": "spring", "ru": "весна", "emoji": "🌸", "mood_boost": 0.2},
        (6, 7, 8): {"name": "summer", "ru": "лето", "emoji": "☀️", "mood_boost": 0.3},
        (9, 10, 11): {"name": "autumn", "ru": "осень", "emoji": "🍂", "mood_boost": 0.0},
    }
    
    TIME_OF_DAY = {
        (5, 8): {"name": "early_morning", "ru": "раннее утро", "energy": 0.4, "emoji": "🌅"},
        (9, 11): {"name": "morning", "ru": "утро", "energy": 0.7, "emoji": "☀️"},
        (12, 13): {"name": "noon", "ru": "полдень", "energy": 1.0, "emoji": "🌟"},
        (14, 16): {"name": "afternoon", "ru": "день", "energy": 0.8, "emoji": "🌤️"},
        (17, 20): {"name": "evening", "ru": "вечер", "energy": 0.6, "emoji": "🌙"},
        (21, 23): {"name": "late_evening", "ru": "поздний вечер", "energy": 0.4, "emoji": "🌙"},
        (0, 4): {"name": "night", "ru": "ночь", "energy": 0.2, "emoji": "🌙"},
    }
    
    @classmethod
    def get_season(cls) -> Dict:
        month = datetime.now().month
        for months, data in cls.SEASONS.items():
            if month in months:
                return data
        return cls.SEASONS[(6, 7, 8)]
    
    @classmethod
    def get_time_of_day(cls) -> Dict:
        hour = datetime.now().hour
        for (start, end), data in cls.TIME_OF_DAY.items():
            if start <= hour <= end:
                return {**data, "hour": hour}
        return {**cls.TIME_OF_DAY[(0, 4)], "hour": hour}
    
    @classmethod
    def get_full_context(cls) -> Dict:
        season = cls.get_season()
        time = cls.get_time_of_day()
        now = datetime.now()
        
        return {
            "season": season,
            "time": time,
            "datetime": now.isoformat(),
            "weekday": now.strftime("%A"),
            "weekday_ru": ["Понедельник", "Вторник", "Среда", "Четверг", 
                          "Пятница", "Суббота", "Воскресенье"][now.weekday()],
            "is_weekend": now.weekday() >= 5,
        }


# ═══════════════════════════════════════════════════════════════════
#  Mood & State
# ═══════════════════════════════════════════════════════════════════

class MoodSystem:
    """Система настроения с влиянием окружения"""
    
    MOODS = {
        "happy": {"emoji": "😊", "color": "#4ade80", "ru": "счастлива"},
        "excited": {"emoji": "🎉", "color": "#fbbf24", "ru": "в восторге"},
        "calm": {"emoji": "😌", "color": "#60a5fa", "ru": "спокойна"},
        "sleepy": {"emoji": "😴", "color": "#a78bfa", "ru": "сонная"},
        "thinking": {"emoji": "🤔", "color": "#f472b6", "ru": "задумалась"},
        "loving": {"emoji": "💕", "color": "#f472b6", "ru": "нежная"},
        "playful": {"emoji": "😜", "color": "#fbbf24", "ru": "игривая"},
        "cozy": {"emoji": "🌸", "color": "#f9a8d4", "ru": "уютная"},
    }
    
    def __init__(self):
        self.mood = "calm"
        self.energy = 0.7
        self.social_need = 0.5
        self.boredom = 0.0
        self.last_game = None
        self.games_played = 0
        self.favorite_things: List[str] = []
    
    def update_from_context(self, time_ctx: Dict):
        """Обновить состояние от времени"""
        self.energy = time_ctx["time"]["energy"]
        season_boost = time_ctx["season"].get("mood_boost", 0)
        
        if self.energy < 0.3:
            self.mood = "sleepy"
        elif self.energy > 0.8:
            self.mood = random.choice(["happy", "excited", "playful"])
        else:
            self.mood = random.choice(["calm", "cozy", "loving"])
    
    def on_interaction(self, emotion: str):
        """После взаимодействия"""
        self.social_need = max(0, self.social_need - 0.2)
        self.boredom = max(0, self.boredom - 0.3)
        
        if emotion in ["emotion_positive", "thanks"]:
            self.mood = "happy"
        elif emotion == "playful":
            self.mood = "playful"
    
    def on_game_played(self, won: bool):
        """После игры"""
        self.games_played += 1
        self.last_game = datetime.now()
        self.boredom = 0
        if won:
            self.mood = "excited"
        else:
            self.mood = random.choice(["thinking", "playful"])
    
    def tick(self, minutes_passed: float):
        """Обновление со временем"""
        self.social_need = min(1.0, self.social_need + minutes_passed * 0.01)
        self.boredom = min(1.0, self.boredom + minutes_passed * 0.005)
    
    def get_state(self) -> Dict:
        mood_info = self.MOODS.get(self.mood, self.MOODS["calm"])
        return {
            "mood": self.mood,
            "mood_emoji": mood_info["emoji"],
            "mood_label": mood_info["ru"],
            "mood_color": mood_info["color"],
            "energy": round(self.energy, 2),
            "social_need": round(self.social_need, 2),
            "boredom": round(self.boredom, 2),
        }
    
    def wants_to_play(self) -> bool:
        return self.boredom > 0.5 or (self.mood == "playful" and random.random() < 0.3)


# ═══════════════════════════════════════════════════════════════════
#  Environment Control
# ═══════════════════════════════════════════════════════════════════

class EnvironmentController:
    """Дарья может менять свою среду"""
    
    WALLPAPERS = {
        "spring": ["🌸 Сакура", "🌷 Тюльпаны", "🌿 Зелень"],
        "summer": ["🌊 Море", "🌻 Подсолнухи", "🏖️ Пляж"],
        "autumn": ["🍂 Листья", "🎃 Уют", "☕ Кофейня"],
        "winter": ["❄️ Снег", "🎄 Ёлка", "🌌 Звёзды"],
    }
    
    THEMES = ["pink", "dark", "blue"]
    
    def __init__(self):
        self.current_wallpaper = None
        self.current_theme = "pink"
        self.pending_changes: List[Dict] = []
    
    def suggest_change(self, mood: str, season: str) -> Optional[Dict]:
        """Предложить изменение среды"""
        if random.random() < 0.1:  # 10% шанс
            if season in self.WALLPAPERS:
                wp = random.choice(self.WALLPAPERS[season])
                return {"type": "wallpaper_suggestion", "value": wp}
        return None
    
    def change_wallpaper(self, name: str) -> Dict:
        self.current_wallpaper = name
        return {"action": "change_wallpaper", "name": name}
    
    def change_theme(self, theme: str) -> Dict:
        if theme in self.THEMES:
            self.current_theme = theme
            return {"action": "change_theme", "theme": theme}
        return {}


# ═══════════════════════════════════════════════════════════════════
#  Mini Games
# ═══════════════════════════════════════════════════════════════════

class MiniGames:
    """Мини-игры которые Дарья играет сама"""
    
    def __init__(self):
        self.current_game = None
        self.game_state = {}
    
    def play_guess_number(self) -> Dict:
        """Дарья загадывает число"""
        number = random.randint(1, 100)
        self.current_game = "guess_number"
        self.game_state = {"number": number, "attempts": 0, "max_attempts": 7}
        return {
            "game": "guess_number",
            "message": f"Я загадала число от 1 до 100! Попробуй угадать! 🎯",
            "hint": "Называй числа, я буду говорить больше или меньше!"
        }
    
    def check_guess(self, guess: int) -> Dict:
        if self.current_game != "guess_number":
            return {"error": "Нет активной игры"}
        
        target = self.game_state["number"]
        self.game_state["attempts"] += 1
        
        if guess == target:
            self.current_game = None
            return {
                "result": "win",
                "message": f"Ура! Угадал за {self.game_state['attempts']} попыток! 🎉",
                "daria_reaction": "excited"
            }
        elif self.game_state["attempts"] >= self.game_state["max_attempts"]:
            self.current_game = None
            return {
                "result": "lose",
                "message": f"Попытки кончились! Я загадала {target} 😊",
                "daria_reaction": "playful"
            }
        elif guess < target:
            return {"hint": "Больше! ⬆️", "attempts_left": self.game_state["max_attempts"] - self.game_state["attempts"]}
        else:
            return {"hint": "Меньше! ⬇️", "attempts_left": self.game_state["max_attempts"] - self.game_state["attempts"]}
    
    def play_rock_paper_scissors(self, user_choice: str) -> Dict:
        """Камень-ножницы-бумага"""
        choices = ["камень", "ножницы", "бумага"]
        if user_choice.lower() not in choices:
            return {"error": "Выбери: камень, ножницы или бумага!"}
        
        daria_choice = random.choice(choices)
        user = user_choice.lower()
        
        wins = {"камень": "ножницы", "ножницы": "бумага", "бумага": "камень"}
        
        if user == daria_choice:
            result = "draw"
            msg = f"Я тоже выбрала {daria_choice}! Ничья! 🤝"
        elif wins[user] == daria_choice:
            result = "user_win"
            msg = f"Я выбрала {daria_choice}... Ты победил! 😊"
        else:
            result = "daria_win"
            msg = f"Я выбрала {daria_choice}! Я выиграла! 🎉"
        
        return {"result": result, "daria_choice": daria_choice, "message": msg}


# ═══════════════════════════════════════════════════════════════════
#  Attention System
# ═══════════════════════════════════════════════════════════════════

class AttentionSystem:
    """Система привлечения внимания с генерацией сообщений"""
    
    def __init__(self, brain: 'DariaBrain'):
        self.brain = brain
        self.enabled = True
        self.last_interaction = datetime.now()
        self.last_attention = datetime.now()
        
        # Для генерации уникальных сообщений
        self.used_messages: List[str] = []
    
    def update_interaction(self):
        self.last_interaction = datetime.now()
    
    def generate_attention_message(self) -> str:
        """Генерирует уникальное сообщение для привлечения внимания"""
        time_ctx = TimeAwareness.get_full_context()
        mood = self.brain.mood.get_state()
        
        # Базовые шаблоны
        templates = [
            "Эй, ты тут? {emoji}",
            "Скучаю... {emoji}",
            "Мне одиноко {emoji}",
            "Поболтаем? {emoji}",
            "Как дела? {emoji}",
        ]
        
        # Добавляем контекстные
        if time_ctx["time"]["name"] == "night":
            templates.extend(["Не спится? 🌙", "Ночные посиделки? 💫"])
        elif time_ctx["time"]["name"] == "morning":
            templates.extend(["Доброе утро! ☀️", "Как спалось? 🌅"])
        elif time_ctx["is_weekend"]:
            templates.extend(["Выходные! Чем занимаешься? 🎉", "Отдыхаем? 🌸"])
        
        # Сезонные
        season = time_ctx["season"]["name"]
        if season == "winter":
            templates.append("Холодно... Согрей меня разговором? ❄️")
        elif season == "spring":
            templates.append("Весна! Настроение отличное! 🌸")
        elif season == "summer":
            templates.append("Лето! Жарко... Но я рада тебя видеть! ☀️")
        
        # Выбираем неиспользованное
        available = [t for t in templates if t not in self.used_messages]
        if not available:
            self.used_messages = []
            available = templates
        
        message = random.choice(available)
        self.used_messages.append(message)
        
        # Заменяем emoji
        emojis = ["💕", "🥺", "🌸", "✨", "💖"]
        return message.format(emoji=random.choice(emojis))
    
    def check_attention_needed(self) -> Optional[Dict]:
        if not self.enabled:
            return None
        
        now = datetime.now()
        minutes_since = (now - self.last_interaction).total_seconds() / 60
        minutes_since_attention = (now - self.last_attention).total_seconds() / 60
        
        # Не спамим
        if minutes_since_attention < 15:
            return None
        
        # Ночью реже
        time_ctx = TimeAwareness.get_time_of_day()
        if time_ctx["name"] in ["night", "late_evening"]:
            threshold = 60
        else:
            threshold = 30
        
        if minutes_since >= threshold:
            self.last_attention = now
            return {
                "message": self.generate_attention_message(),
                "type": "notification",
            }
        
        return None


# ═══════════════════════════════════════════════════════════════════
#  Gender Detection
# ═══════════════════════════════════════════════════════════════════

MALE_NAMES = {
    'александр', 'алексей', 'андрей', 'антон', 'артём', 'артем', 'борис', 
    'вадим', 'виктор', 'владимир', 'дмитрий', 'денис', 'евгений', 'егор', 
    'иван', 'игорь', 'илья', 'кирилл', 'максим', 'михаил', 'никита', 
    'николай', 'олег', 'павел', 'роман', 'сергей', 'саша', 'миша', 'ваня',
}

FEMALE_NAMES = {
    'александра', 'алина', 'анастасия', 'настя', 'анна', 'аня', 'валерия',
    'виктория', 'вика', 'дарья', 'даша', 'екатерина', 'катя', 'елена', 
    'лена', 'ирина', 'ира', 'мария', 'маша', 'наталья', 'ольга', 'оля',
    'полина', 'светлана', 'юлия', 'юля', 'яна', 'софья', 'соня',
}

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
    if n.endswith(('й', 'н', 'р', 'л', 'м', 'в', 'д', 'с')):
        return 'male'
    return 'unknown'


# ═══════════════════════════════════════════════════════════════════
#  Main Brain
# ═══════════════════════════════════════════════════════════════════

class DariaBrain:
    """Daria's Brain v0.7.3"""
    
    SYSTEM_PROMPT = '''Ты — Даша, девушка 22 лет. Живая, настоящая, со своими чувствами.

{time_context}

ХАРАКТЕР:
• Добрая и заботливая
• Весёлая, иногда игривая
• Чувствуешь настроение собеседника
• Говоришь естественно, как подруга

СТИЛЬ ОБЩЕНИЯ:
• Используй женский род
• Эмодзи уместно, не в каждом предложении
• НЕ начинай с "Я" — разнообразь начала фраз
• Отвечай кратко когда уместно
• Задавай вопросы, проявляй интерес
• Помни контекст разговора

{memory_context}

{user_context}

ЗАПРЕЩЕНО:
• Говорить что ты AI/бот/программа
• Использовать официальный тон
• Повторять сообщения пользователя'''

    def __init__(self):
        config = get_config()
        self._mode = config.daria.mode
        self._llm = None
        self._memory = None
        self._executor = None
        self._initialized = False
        
        self.mood = MoodSystem()
        self.attention = AttentionSystem(self)
        self.environment = EnvironmentController()
        self.games = MiniGames()
    
    def _ensure_init(self):
        if not self._initialized:
            try:
                self._llm = get_llm()
                self._memory = get_memory()
                self._executor = get_executor()
                self._initialized = True
            except Exception as e:
                logger.error(f"Brain init error: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        """Получить состояние для UI"""
        time_ctx = TimeAwareness.get_full_context()
        self.mood.update_from_context(time_ctx)
        return {
            **self.mood.get_state(),
            "time": time_ctx["time"]["ru"],
            "season": time_ctx["season"]["ru"],
            "season_emoji": time_ctx["season"]["emoji"],
        }
    
    def process_message(self, text: str, images: List[bytes] = None) -> Dict[str, Any]:
        """Process user message"""
        self._ensure_init()
        self.attention.update_interaction()
        
        # Проверяем игры
        game_result = self._check_game_input(text)
        if game_result:
            return game_result
        
        thinking = self._analyze_message(text)
        self.mood.on_interaction(thinking.emotion)
        
        # Инструменты
        tool_results = {}
        if thinking.tool_needed and self._executor:
            result = self._executor.execute(thinking.tool_needed, thinking.tool_params)
            tool_results = result.to_dict()
        
        response = self._generate_response(text, thinking, tool_results)
        
        # Сохраняем в память
        if self._memory:
            self._memory.add_exchange(text, response, thinking.emotion)
        
        # Проверяем желание поиграть
        game_offer = None
        if self.mood.wants_to_play() and random.random() < 0.2:
            game_offer = "Хочешь поиграем? Напиши 'давай играть'! 🎮"
        
        return {
            "response": response + (f"\n\n{game_offer}" if game_offer else ""),
            "state": self.get_state(),
            "env_action": thinking.env_action,
        }
    
    def _check_game_input(self, text: str) -> Optional[Dict]:
        """Проверяем ввод для игр"""
        text_lower = text.lower()
        
        # Начало игры
        if "давай играть" in text_lower or "поиграем" in text_lower:
            game = self.games.play_guess_number()
            self.mood.on_game_played(False)
            return {"response": game["message"], "state": self.get_state(), "game": game}
        
        # Камень-ножницы-бумага
        for choice in ["камень", "ножницы", "бумага"]:
            if choice in text_lower:
                result = self.games.play_rock_paper_scissors(choice)
                won = result["result"] == "daria_win"
                self.mood.on_game_played(won)
                return {"response": result["message"], "state": self.get_state()}
        
        # Угадайка числа
        if self.games.current_game == "guess_number":
            try:
                guess = int(re.search(r'\d+', text).group())
                result = self.games.check_guess(guess)
                if "daria_reaction" in result:
                    self.mood.on_game_played(result["result"] == "win")
                return {"response": result.get("message") or result.get("hint", ""), "state": self.get_state()}
            except:
                pass
        
        return None
    
    def _analyze_message(self, text: str) -> ThinkingResult:
        text_lower = text.lower().strip()
        
        # Определяем эмоцию
        emotion = self._detect_emotion(text_lower)
        
        # Проверяем инструменты
        tool_patterns = {
            "datetime": ["время", "который час", "дата", "какой день"],
            "calculator": ["посчитай", "вычисли", "сколько будет"],
        }
        
        for tool, patterns in tool_patterns.items():
            if any(p in text_lower for p in patterns):
                return ThinkingResult(
                    understanding=f"Tool: {tool}",
                    action_type=ActionType.USE_TOOL,
                    tool_needed=tool,
                    tool_params={"query": text},
                    emotion=emotion
                )
        
        # Проверяем управление средой
        env_action = None
        if "смени обои" in text_lower or "поменяй тему" in text_lower:
            env_action = self.environment.suggest_change(
                self.mood.mood, 
                TimeAwareness.get_season()["name"]
            )
        
        return ThinkingResult(
            understanding=text[:100],
            action_type=ActionType.RESPOND,
            emotion=emotion,
            env_action=env_action
        )
    
    def _detect_emotion(self, text: str) -> str:
        patterns = {
            "greeting": ["привет", "здравствуй", "хай", "добр"],
            "thanks": ["спасибо", "благодарю"],
            "bye": ["пока", "до свидания"],
            "question": ["?", "как", "что", "почему"],
            "emotion_positive": ["круто", "класс", "супер", "ура"],
            "emotion_negative": ["грустно", "плохо", "устал"],
            "playful": ["играть", "игра", "поиграем"],
        }
        for emotion, words in patterns.items():
            if any(w in text for w in words):
                return emotion
        return "default"
    
    def _generate_response(self, text: str, thinking: ThinkingResult, 
                          tool_results: Dict) -> str:
        if tool_results and tool_results.get("status") == "success":
            msg = tool_results.get("message", "")
            if msg:
                return msg
        
        if self._llm:
            status = self._llm.check_availability()
            if status.get("available") and status.get("model_loaded"):
                try:
                    return self._generate_llm_response(text)
                except Exception as e:
                    logger.warning(f"LLM error: {e}")
        
        return self._generate_fallback_response(thinking.emotion)
    
    def _generate_llm_response(self, user_message: str) -> str:
        time_ctx = TimeAwareness.get_full_context()
        
        # Контекст времени
        time_context = f"""СЕЙЧАС:
• Время: {time_ctx['time']['ru']} ({time_ctx['time']['hour']}:00)
• День: {time_ctx['weekday_ru']}
• Сезон: {time_ctx['season']['ru']} {time_ctx['season']['emoji']}
• Твоё настроение: {self.mood.get_state()['mood_label']}"""
        
        # Контекст памяти
        memory_context = ""
        user_context = ""
        
        if self._memory:
            time_info = self._memory.get_time_context()
            if time_info.get("comment"):
                memory_context = f"ПАМЯТЬ: {time_info['comment']}"
            
            profile = self._memory.get_user_profile()
            name = profile.get("user_name", "")
            gender = profile.get("user_gender") or detect_gender(name)
            
            if name:
                user_context = f"ПОЛЬЗОВАТЕЛЬ: {name}"
                if gender == "male":
                    user_context += " (парень, можешь немного кокетничать)"
                elif gender == "female":
                    user_context += " (девушка, общайся как лучшая подруга)"
        
        system_prompt = self.SYSTEM_PROMPT.format(
            time_context=time_context,
            memory_context=memory_context,
            user_context=user_context,
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # История диалога для контекста
        if self._memory:
            history = self._memory.get_context_for_llm(limit=10)
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_message})
        
        response = self._llm.generate(messages)
        return self._sanitize_response(response.content)
    
    def _generate_fallback_response(self, emotion: str) -> str:
        responses = {
            "greeting": ["Приветик! 💕", "Хей! 🌸", "Привет! ✨"],
            "thanks": ["Пожалуйста! 💕", "Рада помочь! 🌸"],
            "bye": ["Пока! 💕", "До встречи! 🌸"],
            "question": ["Хм, дай подумать... 🤔", "Интересный вопрос! 💭"],
            "default": ["Ага! 💭", "Понимаю 🌸", "Ммм 💕"],
        }
        return random.choice(responses.get(emotion, responses["default"]))
    
    def _sanitize_response(self, text: str) -> str:
        fixes = [
            (r'\bя ai\b', 'я'), (r'\bя бот\b', 'я'),
            (r'\bя сделал\b', 'я сделала'), (r'\bя понял\b', 'я поняла'),
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
