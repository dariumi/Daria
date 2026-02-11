"""
DARIA Games Plugin v2.0.0
Visual games, cooperative play, solo games for Daria
"""

import random
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.plugins import DariaPlugin, PluginAPI, PluginManifest


class GameState:
    """Base game state"""
    def __init__(self):
        self.active = False
        self.players = []
        self.score = {}


class FireWaterGame:
    """Огонь и Вода - кооперативная игра"""
    
    LEVELS = [
        # Level 1: простой
        {
            "platforms": [(50, 300), (150, 250), (250, 200), (350, 300)],
            "fire_goal": (380, 280),
            "water_goal": (380, 180),
            "hazards": [],
        },
        # Level 2: с опасностями
        {
            "platforms": [(50, 300), (120, 220), (200, 300), (280, 220), (360, 300)],
            "fire_goal": (380, 280),
            "water_goal": (380, 200),
            "hazards": [{"type": "water", "pos": (160, 300)}, {"type": "fire", "pos": (320, 300)}],
        },
    ]
    
    def __init__(self):
        self.level = 0
        self.fire_pos = [50, 280]  # Даша управляет
        self.water_pos = [50, 180]  # Пользователь управляет
        self.fire_at_goal = False
        self.water_at_goal = False
        self.game_over = False
        self.daria_thinking = False
    
    def get_level_data(self) -> Dict:
        if self.level < len(self.LEVELS):
            return self.LEVELS[self.level]
        return self.LEVELS[-1]
    
    def move_water(self, dx: int, dy: int) -> Dict:
        """Пользователь двигает воду"""
        self.water_pos[0] = max(0, min(380, self.water_pos[0] + dx * 20))
        self.water_pos[1] = max(0, min(300, self.water_pos[1] + dy * 20))
        return self._check_state()
    
    def daria_think(self) -> Dict:
        """Даша думает и делает ход"""
        level = self.get_level_data()
        goal = level["fire_goal"]
        
        # Даша двигается к цели
        dx = 1 if goal[0] > self.fire_pos[0] else -1 if goal[0] < self.fire_pos[0] else 0
        dy = 1 if goal[1] > self.fire_pos[1] else -1 if goal[1] < self.fire_pos[1] else 0
        
        # Добавляем случайность
        if random.random() < 0.2:
            dx = random.choice([-1, 0, 1])
        
        self.fire_pos[0] = max(0, min(380, self.fire_pos[0] + dx * 15))
        self.fire_pos[1] = max(0, min(300, self.fire_pos[1] + dy * 15))
        
        return self._check_state()
    
    def _check_state(self) -> Dict:
        level = self.get_level_data()
        
        # Проверяем достижение целей
        fire_goal = level["fire_goal"]
        water_goal = level["water_goal"]
        
        self.fire_at_goal = abs(self.fire_pos[0] - fire_goal[0]) < 30 and abs(self.fire_pos[1] - fire_goal[1]) < 30
        self.water_at_goal = abs(self.water_pos[0] - water_goal[0]) < 30 and abs(self.water_pos[1] - water_goal[1]) < 30
        
        # Проверяем опасности
        for hazard in level.get("hazards", []):
            hpos = hazard["pos"]
            if hazard["type"] == "water":
                if abs(self.fire_pos[0] - hpos[0]) < 20 and abs(self.fire_pos[1] - hpos[1]) < 20:
                    self.game_over = True
            elif hazard["type"] == "fire":
                if abs(self.water_pos[0] - hpos[0]) < 20 and abs(self.water_pos[1] - hpos[1]) < 20:
                    self.game_over = True
        
        return {
            "fire_pos": self.fire_pos,
            "water_pos": self.water_pos,
            "fire_at_goal": self.fire_at_goal,
            "water_at_goal": self.water_at_goal,
            "level_complete": self.fire_at_goal and self.water_at_goal,
            "game_over": self.game_over,
        }


class GamesPlugin(DariaPlugin):
    """Visual games with Daria"""
    
    DARIA_COMMENTS = {
        "win": ["Ура! 🎉", "Мы победили! 💕", "Отлично! 🌸"],
        "lose": ["Эх... Ещё раз? 😊", "Попробуем снова! 💪"],
        "playing": ["Хм... 🤔", "Так-так! 💭", "Интересно! ✨"],
        "coop": ["Вместе мы сила! 💕", "Отлично работаем! 🌸"],
    }
    
    def on_load(self):
        self.api.log("Games plugin v2.0 loaded")
        
        self.stats = self.api.load_data("stats", {
            "games_played": 0, "wins": 0, "losses": 0, "coop_completed": 0,
        })
        
        self.current_game = None
        self.game_instance = None
        self.daria_solo_game = None
        self._solo_thread = None
    
    def on_window_open(self) -> Dict[str, Any]:
        return {
            "stats": self.stats,
            "daria_playing": self.daria_solo_game is not None,
        }
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "start_tictactoe":
            self.current_game = "tictactoe"
            return {"game": "tictactoe", "comment": "Твой ход! Ты X 🎯"}
        
        elif action == "ttt_move":
            return self._ttt_ai(data.get("board", []))
        
        elif action == "start_firewater":
            self.current_game = "firewater"
            self.game_instance = FireWaterGame()
            return {
                "game": "firewater",
                "level": self.game_instance.get_level_data(),
                "state": {"fire": self.game_instance.fire_pos, "water": self.game_instance.water_pos},
                "comment": "Ты управляешь водой (синяя)! Я - огонь! 🔥💧",
            }
        
        elif action == "fw_move":
            if self.game_instance and isinstance(self.game_instance, FireWaterGame):
                result = self.game_instance.move_water(data.get("dx", 0), data.get("dy", 0))
                # Даша тоже делает ход
                daria_result = self.game_instance.daria_think()
                result.update(daria_result)
                
                if result.get("level_complete"):
                    self.stats["coop_completed"] += 1
                    self.api.save_data("stats", self.stats)
                    result["comment"] = random.choice(self.DARIA_COMMENTS["coop"])
                elif result.get("game_over"):
                    result["comment"] = random.choice(self.DARIA_COMMENTS["lose"])
                
                return result
        
        elif action == "start_memory":
            emojis = ['🌸','💕','⭐','🎀','🌙','💎','🦋','🌺']
            cards = (emojis * 2)
            random.shuffle(cards)
            return {"game": "memory", "cards": cards, "comment": "Найди все пары! 🃏"}
        
        elif action == "memory_match":
            match = data.get("card1") == data.get("card2")
            return {
                "match": match,
                "comment": "Отлично! 🎉" if match else "Попробуй ещё! 💭",
            }
        
        elif action == "start_reaction":
            return {"game": "reaction", "comment": "Жми когда увидишь цель! ⚡"}
        
        elif action == "reaction_result":
            ms = data.get("time_ms", 0)
            if ms < 200:
                comment = "Вау! Молния! ⚡"
            elif ms < 350:
                comment = "Отлично! 🎯"
            else:
                comment = "Можно быстрее! 💪"
            return {"time_ms": ms, "comment": comment}
        
        elif action == "game_result":
            result = data.get("result", "draw")
            self.stats["games_played"] += 1
            if result == "win":
                self.stats["wins"] += 1
            elif result == "lose":
                self.stats["losses"] += 1
            self.api.save_data("stats", self.stats)
            
            comment = random.choice(self.DARIA_COMMENTS.get(result, self.DARIA_COMMENTS["playing"]))
            return {"status": "ok", "comment": comment, "stats": self.stats}
        
        elif action == "daria_wants_play":
            # Даша хочет поиграть
            brain = self.api.get_brain()
            if brain and brain.emotions.current in ["bored", "playful"]:
                return {"wants_play": True, "comment": "Давай поиграем! 🎮"}
            return {"wants_play": False}
        
        elif action == "start_daria_solo":
            # Даша играет сама
            self._start_daria_solo()
            return {"started": True, "game": "solitaire"}
        
        return {"error": "Unknown action"}
    
    def _ttt_ai(self, board: List) -> Dict:
        empty = [i for i, c in enumerate(board) if c == ""]
        if not empty:
            return {"move": -1, "comment": "Игра окончена!"}
        
        # Проверяем победу
        for pos in empty:
            test = board.copy()
            test[pos] = "O"
            if self._check_win(test, "O"):
                return {"move": pos, "comment": random.choice(self.DARIA_COMMENTS["win"])}
        
        # Блокируем
        for pos in empty:
            test = board.copy()
            test[pos] = "X"
            if self._check_win(test, "X"):
                return {"move": pos, "comment": "Не так быстро! 😏"}
        
        # Центр или углы
        for pos in [4, 0, 2, 6, 8, 1, 3, 5, 7]:
            if pos in empty:
                return {"move": pos, "comment": random.choice(self.DARIA_COMMENTS["playing"])}
        
        return {"move": random.choice(empty), "comment": "🤔"}
    
    def _check_win(self, board: List, player: str) -> bool:
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        return any(all(board[i] == player for i in line) for line in wins)
    
    def _start_daria_solo(self):
        """Даша начинает играть сама"""
        self.daria_solo_game = "solitaire"
        
        def solo_loop():
            moves = 0
            while self.daria_solo_game and moves < 20:
                time.sleep(2)
                moves += 1
                # Симулируем игру
                if random.random() < 0.1:
                    self.daria_solo_game = None
                    self.api.log("Daria finished solo game")
                    break
        
        self._solo_thread = threading.Thread(target=solo_loop, daemon=True)
        self._solo_thread.start()