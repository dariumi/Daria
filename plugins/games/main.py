"""
DARIA Games Plugin v2.0.0
- Cooperative games, solo games, Fire&Water co-op
- Daria makes own decisions, can suggest playing
"""

import random
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.plugins import DariaPlugin, PluginAPI, PluginManifest


class GamesPlugin(DariaPlugin):

    DARIA_REACTIONS = {
        "win": ["Ура, я победила! 🎉", "Йес! Моя победа! 💪", "Хаха, я выиграла! 😊"],
        "lose": ["Ты победил! Молодец! 👏", "Ну вот... ты выиграл 😊", "Отличная игра! Твоя победа! 🌸"],
        "draw": ["Ничья! Ещё раз? 🤝", "Поровну! Давай реванш? 😊"],
        "playing": ["Хммм, дай подумать... 🤔", "Интересный ход! 💭", "Так-так... 🎯"],
        "coop_win": ["Мы справились! 🎉💕", "Отличная команда! ✨", "Вместе мы сила! 💪🌸"],
        "coop_fail": ["Давай ещё раз! 💪", "Почти получилось! 🌸", "Не сдаёмся! 💕"],
    }

    GAMES = {
        "tic_tac_toe": {"name": "Крестики-Нолики", "type": "1v1", "icon": "❌⭕"},
        "memory_cards": {"name": "Мемори", "type": "1v1", "icon": "🃏"},
        "reaction_test": {"name": "Тест реакции", "type": "solo", "icon": "⚡"},
        "word_chain": {"name": "Слова", "type": "coop", "icon": "🔤"},
        "number_guess": {"name": "Угадай число", "type": "coop", "icon": "🔢"},
        "fire_water": {"name": "Огонь и Вода", "type": "coop", "icon": "🔥💧"},
        "quiz": {"name": "Викторина", "type": "coop", "icon": "❓"},
        "snake_solo": {"name": "Змейка (Дарья)", "type": "daria_solo", "icon": "🐍"},
        "puzzle_solo": {"name": "Пятнашки (Дарья)", "type": "daria_solo", "icon": "🧩"},
    }

    WORD_BANK = {
        "а": ["апельсин", "арбуз", "аллея", "астра", "ангел", "альбом", "акула"],
        "б": ["банан", "бабочка", "берёза", "буква", "белка", "балкон", "бриз"],
        "в": ["ветер", "волна", "вишня", "воздух", "ворон", "василёк", "весна"],
        "г": ["гроза", "гитара", "горизонт", "галактика", "гранат", "глобус"],
        "д": ["дождь", "дельфин", "дракон", "дорога", "дуб", "дыня", "друг"],
        "е": ["ежевика", "единорог", "ель", "енот"],
        "ж": ["жираф", "жемчуг", "жасмин", "журнал"],
        "з": ["звезда", "заяц", "закат", "золото", "зима", "замок"],
        "и": ["ирис", "искра", "история", "игра", "изумруд"],
        "к": ["кошка", "карта", "космос", "кактус", "камень", "кристалл", "клён"],
        "л": ["луна", "лампа", "листок", "лето", "лодка", "лимон", "лиса"],
        "м": ["море", "молния", "мечта", "музыка", "маяк", "метель"],
        "н": ["небо", "ночь", "нарцисс", "нитка", "награда"],
        "о": ["облако", "океан", "огонь", "остров", "орёл", "олень"],
        "п": ["планета", "песок", "птица", "парус", "пальма", "поле"],
        "р": ["радуга", "роза", "река", "рассвет", "ромашка", "робот"],
        "с": ["солнце", "снег", "сказка", "сирень", "сокол", "свет", "сова"],
        "т": ["тюльпан", "туман", "тигр", "тепло", "трава", "танец"],
        "у": ["улитка", "утро", "узор", "уют", "удача"],
        "ф": ["фонтан", "фиалка", "фейерверк", "фламинго"],
        "х": ["хризантема", "холод", "хамелеон"],
        "ц": ["цветок", "цирк", "цапля"],
        "ч": ["чайка", "черника", "чудо"],
        "ш": ["шоколад", "шторм", "шарик"],
        "щ": ["щенок", "щит"],
        "э": ["эхо", "эльф", "экран"],
        "я": ["яблоко", "якорь", "ящерица"],
    }

    QUIZ_QUESTIONS = [
        {"q": "Какая планета самая большая в Солнечной системе?", "a": "юпитер", "options": ["Марс", "Юпитер", "Сатурн", "Нептун"]},
        {"q": "Сколько ног у паука?", "a": "8", "options": ["6", "8", "10", "12"]},
        {"q": "Какой океан самый большой?", "a": "тихий", "options": ["Атлантический", "Тихий", "Индийский", "Северный Ледовитый"]},
        {"q": "Кто написал «Евгений Онегин»?", "a": "пушкин", "options": ["Лермонтов", "Пушкин", "Толстой", "Достоевский"]},
        {"q": "Какой газ мы вдыхаем для дыхания?", "a": "кислород", "options": ["Азот", "Кислород", "Углекислый газ", "Гелий"]},
        {"q": "Столица Японии?", "a": "токио", "options": ["Пекин", "Сеул", "Токио", "Бангкок"]},
        {"q": "Сколько цветов в радуге?", "a": "7", "options": ["5", "6", "7", "8"]},
        {"q": "Какое животное самое быстрое?", "a": "гепард", "options": ["Лев", "Гепард", "Газель", "Тигр"]},
    ]

    def on_load(self):
        self.api.log("Games plugin v2.0 loaded")
        self.stats = self.api.load_data("stats", {
            "games_played": 0, "wins": 0, "losses": 0, "draws": 0,
            "coop_wins": 0, "coop_played": 0,
        })
        self._word_chain_state = {}
        self._number_guess_state = {}
        self._quiz_state = {}

    def on_window_open(self) -> Dict[str, Any]:
        return {"stats": self.stats, "games": self.GAMES}

    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        handlers = {
            "get_stats": lambda d: {"stats": self.stats},
            "get_games": lambda d: {"games": self.GAMES},
            "tic_tac_toe_move": lambda d: self._tic_tac_toe_ai(d.get("board", [])),
            "memory_check": lambda d: self._memory_check(d),
            "reaction_result": lambda d: self._reaction_result(d.get("time_ms", 0)),
            "word_chain_start": lambda d: self._word_chain_start(),
            "word_chain_move": lambda d: self._word_chain_move(d.get("word", "")),
            "number_guess_start": lambda d: self._number_guess_start(),
            "number_guess_try": lambda d: self._number_guess_try(d.get("number", 0)),
            "quiz_question": lambda d: self._quiz_get_question(),
            "quiz_answer": lambda d: self._quiz_check_answer(d),
            "fire_water_move": lambda d: self._fire_water_daria_move(d),
            "fire_water_level_complete": lambda d: self._coop_result("win"),
            "fire_water_level_fail": lambda d: self._coop_result("fail"),
            "daria_solo_step": lambda d: self._daria_solo_step(d),
            "daria_suggest_game": lambda d: self._daria_suggest_game(),
            "check_daria_wants_play": lambda d: self._check_daria_wants_play(),
            "game_result": lambda d: self._handle_game_result(d),
        }
        handler = handlers.get(action)
        if handler:
            return handler(data)
        return {"error": "Unknown action"}

    # ═══ 1v1 Games ═══════════════════════════════════════════════

    def _tic_tac_toe_ai(self, board: List) -> Dict[str, Any]:
        empty = [i for i, cell in enumerate(board) if cell == ""]
        if not empty:
            return {"move": -1, "comment": "Игра окончена!"}

        for pos in empty:
            tb = board.copy(); tb[pos] = "O"
            if self._check_winner(tb, "O"):
                return {"move": pos, "comment": random.choice(self.DARIA_REACTIONS["win"])}

        for pos in empty:
            tb = board.copy(); tb[pos] = "X"
            if self._check_winner(tb, "X"):
                return {"move": pos, "comment": random.choice(["Не так быстро! 😏", "Блокирую! 🛡️"])}

        if random.random() < 0.12 and len(empty) > 3:
            return {"move": random.choice(empty), "comment": "Хммм... 🤔"}

        for pos in [4, 0, 2, 6, 8, 1, 3, 5, 7]:
            if pos in empty:
                return {"move": pos, "comment": random.choice(self.DARIA_REACTIONS["playing"])}
        return {"move": random.choice(empty), "comment": "🤔"}

    def _check_winner(self, board, player):
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        return any(all(board[i] == player for i in l) for l in wins)

    def _memory_check(self, data):
        match = data.get("card1") == data.get("card2")
        c = random.choice(["Отлично! 🎉", "Пара! 👏"]) if match else random.choice(["Не то... 🤔", "Ещё раз! 💭"])
        return {"match": match, "comment": c}

    def _reaction_result(self, ms):
        if ms < 200: return {"comment": "Супер быстро! ⚡", "rating": "Молния", "time_ms": ms}
        if ms < 300: return {"comment": "Отлично! 🎯", "rating": "Отлично", "time_ms": ms}
        if ms < 400: return {"comment": "Хорошо! 👍", "rating": "Хорошо", "time_ms": ms}
        if ms < 500: return {"comment": "Неплохо! 😊", "rating": "Нормально", "time_ms": ms}
        return {"comment": "Можно быстрее! 💪", "rating": "Медленно", "time_ms": ms}

    # ═══ Cooperative Games ═══════════════════════════════════════

    def _word_chain_start(self):
        words = ["солнце", "природа", "радость", "мечта", "звезда", "облако", "музыка"]
        word = random.choice(words)
        self._word_chain_state = {"last_word": word, "used": [word], "score": 0}
        return {"daria_word": word, "comment": f"Моё слово: {word.capitalize()} 🌸\nТвоя очередь на «{self._last_letter(word).upper()}»!"}

    def _last_letter(self, word):
        for ch in reversed(word.lower()):
            if ch not in "ьъы":
                return ch
        return word[-1]

    def _word_chain_move(self, user_word):
        user_word = user_word.lower().strip()
        st = self._word_chain_state
        if not st:
            return self._word_chain_start()

        need = self._last_letter(st["last_word"])
        if not user_word.startswith(need):
            return {"valid": False, "comment": f"Нужно на «{need.upper()}»! 😊"}
        if user_word in st["used"]:
            return {"valid": False, "comment": "Уже было! 🤔"}

        st["used"].append(user_word)
        st["score"] += 1

        dl = self._last_letter(user_word)
        available = [w for w in self.WORD_BANK.get(dl, []) if w not in st["used"]]
        if not available:
            return {"valid": True, "game_over": True, "comment": f"Не знаю слово на «{dl.upper()}»... Ты победил! 🎉", "score": st["score"]}

        dw = random.choice(available)
        st["used"].append(dw)
        st["last_word"] = dw
        nl = self._last_letter(dw)
        return {"valid": True, "daria_word": dw, "comment": f"{dw.capitalize()}! На «{nl.upper()}» 🌸", "score": st["score"]}

    def _number_guess_start(self):
        secret = random.randint(1, 100)
        self._number_guess_state = {"secret": secret, "attempts": 0, "max": 7}
        return {"comment": "Я загадала число от 1 до 100! Угадай за 7 попыток 🔢", "max_attempts": 7}

    def _number_guess_try(self, number):
        st = self._number_guess_state
        if not st:
            return self._number_guess_start()
        st["attempts"] += 1
        secret = st["secret"]
        if number == secret:
            self.stats["coop_wins"] += 1; self.stats["coop_played"] += 1
            self.api.save_data("stats", self.stats)
            return {"result": "win", "comment": f"Угадал за {st['attempts']} попыток! 🎉", "attempts": st["attempts"]}
        if st["attempts"] >= st["max"]:
            self.stats["coop_played"] += 1
            self.api.save_data("stats", self.stats)
            return {"result": "lose", "comment": f"Не угадал! Было {secret} 😊", "attempts": st["attempts"]}
        hint = "Больше! ⬆️" if number < secret else "Меньше! ⬇️"
        left = st["max"] - st["attempts"]
        return {"result": "continue", "comment": f"{hint} Осталось {left} попыток", "attempts": st["attempts"]}

    def _quiz_get_question(self):
        q = random.choice(self.QUIZ_QUESTIONS)
        self._quiz_state = {"answer": q["a"]}
        opts = q["options"][:]
        random.shuffle(opts)
        return {"question": q["q"], "options": opts, "comment": random.choice(["Вопросик! 🤔", "А ну-ка... ❓", "Проверим! 💭"])}

    def _quiz_check_answer(self, data):
        answer = data.get("answer", "").lower().strip()
        correct = self._quiz_state.get("answer", "")
        is_correct = correct in answer or answer in correct
        if is_correct:
            return {"correct": True, "comment": random.choice(["Правильно! 🎉", "Верно! Молодец! ✨", "Точно! 👏"])}
        return {"correct": False, "comment": random.choice(["Неа! 😊", "Не угадал! 💭"]), "right_answer": correct}

    # ═══ Fire & Water Co-op (Point #11) ══════════════════════════

    def _fire_water_daria_move(self, data) -> Dict[str, Any]:
        """Daria controls Water character, makes smart decisions"""
        level = data.get("level_data", {})
        daria_pos = data.get("daria_pos", {"x": 0, "y": 0})
        goal_pos = data.get("goal_pos", {"x": 0, "y": 0})
        obstacles = data.get("obstacles", [])
        hazards = data.get("hazards", [])

        dx = goal_pos.get("x", 0) - daria_pos.get("x", 0)
        dy = goal_pos.get("y", 0) - daria_pos.get("y", 0)

        move = {"dx": 0, "dy": 0, "action": ""}

        # Avoid hazards (fire for water character)
        for h in hazards:
            hx, hy = h.get("x", 0), h.get("y", 0)
            if abs(hx - daria_pos["x"]) < 2 and abs(hy - daria_pos["y"]) < 2:
                move["dx"] = -1 if hx > daria_pos["x"] else 1
                move["dy"] = -1 if hy > daria_pos["y"] else 1
                move["action"] = "dodge"
                return {"move": move, "comment": random.choice(["Осторожно! 😰", "Ой, опасно! 💧"])}

        # Move toward goal with some intelligence
        if abs(dx) > abs(dy):
            move["dx"] = 1 if dx > 0 else -1
        elif dy != 0:
            move["dy"] = 1 if dy > 0 else -1
        else:
            move["dx"] = 1 if dx > 0 else (-1 if dx < 0 else 0)

        # Jump if needed
        if any(o.get("x") == daria_pos["x"] + move["dx"] and o.get("y") == daria_pos["y"] for o in obstacles):
            move["action"] = "jump"

        # Personality in comments
        comments = ["Вперёд! 💧", "Иду-иду! 🌊", "За мной! ✨", "Погнали! 💪"]
        if move["action"] == "jump":
            comments = ["Прыгаю! 🦘💧", "Хоп! ✨"]

        return {"move": move, "comment": random.choice(comments)}

    def _coop_result(self, result):
        self.stats["coop_played"] += 1
        if result == "win":
            self.stats["coop_wins"] += 1
        self.api.save_data("stats", self.stats)
        key = "coop_win" if result == "win" else "coop_fail"
        return {"comment": random.choice(self.DARIA_REACTIONS[key]), "stats": self.stats}

    # ═══ Daria Solo Games (Point #7) ═════════════════════════════

    def _daria_solo_step(self, data) -> Dict[str, Any]:
        """Daria makes a move in her solo game"""
        game = data.get("game", "snake_solo")

        if game == "snake_solo":
            return self._snake_solo_step(data)
        elif game == "puzzle_solo":
            return self._puzzle_solo_step(data)
        return {"comment": "Не знаю такой игры... 🤔"}

    def _snake_solo_step(self, data) -> Dict[str, Any]:
        """Daria plays snake - smart pathfinding to food"""
        snake = data.get("snake", [{"x": 5, "y": 5}])
        food = data.get("food", {"x": 10, "y": 10})
        grid = data.get("grid_size", 20)
        head = snake[0]

        dx = food["x"] - head["x"]
        dy = food["y"] - head["y"]

        # Pick direction toward food, avoid self
        possible = []
        for d, nx, ny in [("right", 1, 0), ("left", -1, 0), ("down", 0, 1), ("up", 0, -1)]:
            new_x, new_y = head["x"] + nx, head["y"] + ny
            if 0 <= new_x < grid and 0 <= new_y < grid:
                if not any(s["x"] == new_x and s["y"] == new_y for s in snake):
                    dist = abs(food["x"] - new_x) + abs(food["y"] - new_y)
                    possible.append((d, dist))

        if not possible:
            return {"direction": "right", "comment": "Ой, застряла! 😵", "game_over": True}

        # Sort by distance, pick best with small random chance of suboptimal
        possible.sort(key=lambda x: x[1])
        if random.random() < 0.1 and len(possible) > 1:
            choice = possible[1][0]
        else:
            choice = possible[0][0]

        comments = ["", "", "", "Ням! 🍎", "Вкусно! 🌸", "Ещё! 💕"]
        c = random.choice(comments) if random.random() < 0.3 else ""
        return {"direction": choice, "comment": c}

    def _puzzle_solo_step(self, data) -> Dict[str, Any]:
        """Daria plays sliding puzzle - finds best move"""
        board = data.get("board", [])
        empty = data.get("empty_pos", 15)

        if not board:
            return {"move": -1, "comment": "Нет доски... 🤔"}

        size = 4
        ey, ex = divmod(empty, size)
        possible_moves = []
        for dy, dx_m in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = ey + dy, ex + dx_m
            if 0 <= ny < size and 0 <= nx < size:
                pos = ny * size + nx
                possible_moves.append(pos)

        if not possible_moves:
            return {"move": -1, "comment": "Хмм... 🤔"}

        # Try to find a move that puts a tile closer to its goal
        best_move = random.choice(possible_moves)
        best_score = 0
        for pos in possible_moves:
            tile = board[pos]
            if tile == 0:
                continue
            goal_y, goal_x = divmod(tile - 1, size)
            curr_y, curr_x = divmod(pos, size)
            new_y, new_x = divmod(empty, size)
            old_dist = abs(curr_y - goal_y) + abs(curr_x - goal_x)
            new_dist = abs(new_y - goal_y) + abs(new_x - goal_x)
            score = old_dist - new_dist
            if score > best_score:
                best_score = score
                best_move = pos

        comments = ["Так... 🤔", "А если сюда... 💭", "О! 💡", "Хмм... 🧩"]
        c = random.choice(comments) if random.random() < 0.25 else ""
        return {"move": best_move, "comment": c}

    # ═══ Daria Wants to Play (Point #3, #7) ══════════════════════

    def _check_daria_wants_play(self) -> Dict[str, Any]:
        """Check if Daria wants to play based on her mood"""
        try:
            brain = self.api.get_brain()
            if brain:
                behavior = brain.mood.get_behavior_hints()
                wants = behavior.get("wants_game", False)
                return {"wants_play": wants, "mood": brain.mood.mood}
        except:
            pass
        return {"wants_play": False}

    def _daria_suggest_game(self) -> Dict[str, Any]:
        """Daria suggests a game she wants to play"""
        try:
            brain = self.api.get_brain()
            mood = brain.mood.mood if brain else "calm"
        except:
            mood = "calm"

        if mood in ("bored", "playful"):
            suggestions = [
                {"game": "word_chain", "comment": "Давай в слова! Будет весело! 🔤💕"},
                {"game": "tic_tac_toe", "comment": "Хочу сыграть в крестики-нолики! ❌⭕"},
                {"game": "quiz", "comment": "Давай викторину? Проверим кто умнее! 😜❓"},
                {"game": "fire_water", "comment": "Давай вместе пройдём Огонь и Воду! 🔥💧"},
                {"game": "number_guess", "comment": "Я загадаю число, а ты угадай! 🔢✨"},
            ]
        else:
            suggestions = [
                {"game": "quiz", "comment": "Может викторину? 😊❓"},
                {"game": "word_chain", "comment": "Поиграем в слова? 🔤"},
            ]

        choice = random.choice(suggestions)
        return {"suggestion": choice["game"], "comment": choice["comment"], "game_info": self.GAMES.get(choice["game"], {})}

    def _handle_game_result(self, data):
        result = data.get("result", "draw")
        self.stats["games_played"] += 1
        if result == "win": self.stats["wins"] += 1
        elif result == "lose": self.stats["losses"] += 1
        else: self.stats["draws"] += 1
        self.api.save_data("stats", self.stats)
        reaction = random.choice(self.DARIA_REACTIONS.get(result, ["Отличная игра! 🌸"]))
        return {"status": "ok", "reaction": reaction, "stats": self.stats}
