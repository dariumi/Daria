"""
DARIA Weather Plugin v1.0.0
Weather with Daria's comments
"""

from typing import Dict, Any
import random

from core.plugins import DariaPlugin, PluginAPI, PluginManifest


class WeatherPlugin(DariaPlugin):
    """Weather plugin with cute comments"""
    
    WEATHER_COMMENTS = {
        "sunny": [
            "Отличная погода для прогулки! ☀️",
            "Солнышко светит! Не забудь солнцезащитные очки 😎",
            "Прекрасный день! Может, погуляем? 🌸",
        ],
        "cloudy": [
            "Облачно, но тоже неплохо! ☁️",
            "Небо в облаках, но настроение пусть будет ясным! 💕",
            "Серенько сегодня... Зато уютно! 🌸",
        ],
        "rainy": [
            "Дождик идёт! Не забудь зонтик! ☔",
            "Мокро на улице... Самое время для чая дома 🍵",
            "Дождь — это романтично, но лучше возьми зонт! 💕",
        ],
        "snowy": [
            "Снежок! Как красиво! ❄️",
            "Зимняя сказка! Одевайся теплее! 🧣",
            "Снег идёт... Можно лепить снеговиков! ⛄",
        ],
        "cold": [
            "Холодно! Надень что-нибудь тёплое! 🧥",
            "Бррр, морозно! Шапку не забудь! 🌸",
            "Холодина! Согревайся чаем! ☕",
        ],
        "hot": [
            "Жарко! Пей больше воды! 💧",
            "Настоящее лето! Не перегрейся! ☀️",
            "Жара... Мороженое поможет! 🍦",
        ],
    }
    
    def on_load(self):
        self.api.log("Weather plugin loaded")
    
    def on_window_open(self) -> Dict[str, Any]:
        settings = self.api.load_data("settings", {"city": "Москва"})
        return {"city": settings.get("city", "Москва")}
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "set_city":
            city = data.get("city", "Москва")
            self.api.save_data("settings", {"city": city})
            return {"status": "ok", "city": city}
        
        elif action == "get_weather":
            city = data.get("city", "Москва")
            
            # Try to get real weather (requires API key)
            # For now, return mock data with Daria's comments
            weather = self._get_mock_weather(city)
            
            return weather
        
        return {"error": "Unknown action"}
    
    def _get_mock_weather(self, city: str) -> Dict[str, Any]:
        """Get mock weather data with Daria's comments"""
        import random
        from datetime import datetime, timedelta
        
        # Random weather for demo
        conditions = ["sunny", "cloudy", "rainy"]
        condition = random.choice(conditions)
        temp = random.randint(-5, 30)
        
        # Determine weather type for comment
        if temp < 0:
            comment_type = "cold"
        elif temp > 25:
            comment_type = "hot"
        else:
            comment_type = condition
        
        comment = random.choice(self.WEATHER_COMMENTS.get(comment_type, self.WEATHER_COMMENTS["cloudy"]))
        
        # Icons
        icons = {"sunny": "☀️", "cloudy": "☁️", "rainy": "🌧️", "snowy": "❄️"}
        
        # Forecast
        forecast = []
        for i in range(5):
            day = datetime.now() + timedelta(days=i)
            cond = random.choice(conditions)
            forecast.append({
                "day": day.strftime("%a"),
                "icon": icons.get(cond, "☁️"),
                "temp_high": temp + random.randint(-3, 5),
                "temp_low": temp + random.randint(-8, -3),
            })
        
        return {
            "city": city,
            "temp": temp,
            "condition": condition,
            "icon": icons.get(condition, "☁️"),
            "humidity": random.randint(40, 80),
            "wind": random.randint(1, 15),
            "comment": comment,
            "forecast": forecast,
        }
