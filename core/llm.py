"""
DARIA LLM Provider v0.8.1
Ollama integration with YandexGPT support
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger("daria")

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    httpx = None
    HAS_HTTPX = False

from .config import get_config


class LLMError(Exception):
    """LLM-related errors"""
    pass


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0


# Поддерживаемые модели
SUPPORTED_MODELS = {
    # Ollama модели
    "llama3.2": {"provider": "ollama", "name": "Llama 3.2"},
    "llama3.1": {"provider": "ollama", "name": "Llama 3.1"},
    "mistral": {"provider": "ollama", "name": "Mistral"},
    "gemma2": {"provider": "ollama", "name": "Gemma 2"},
    "qwen2.5": {"provider": "ollama", "name": "Qwen 2.5"},
    
    # YandexGPT (для Ollama через GGUF)
    "yandex/YandexGPT-5-Lite-8B-instruct-GGUF": {
        "provider": "ollama",
        "name": "YandexGPT 5 Lite",
        "alias": "yandexgpt"
    },
}


class OllamaProvider:
    """Ollama LLM Provider"""
    
    def __init__(self, base_url: str = None, model: str = None):
        config = get_config()
        self.base_url = base_url or config.llm.base_url
        self.model = model or config.llm.model
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
    
    def generate(self, messages: List[Dict[str, str]], 
                 model: str = None,
                 temperature: float = None) -> LLMResponse:
        """Generate response synchronously"""
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        try:
            if HAS_HTTPX:
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
            else:
                import urllib.request
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode())
            
            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                model=data.get("model", self.model),
                tokens_used=data.get("eval_count", 0)
            )
            
        except Exception as e:
            error_str = str(e)
            if "Connection refused" in error_str or "ConnectError" in error_str:
                raise LLMError("Cannot connect to Ollama. Make sure it's running.")
            logger.error(f"LLM error: {e}")
            raise LLMError(f"LLM generation failed: {e}")
    
    def check_availability(self) -> Dict[str, Any]:
        """Check if Ollama is available"""
        try:
            url = f"{self.base_url}/api/tags"
            
            if HAS_HTTPX:
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                    else:
                        return self._unavailable_response()
            else:
                import urllib.request
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
            
            models = [m["name"] for m in data.get("models", [])]
            model_base = self.model.split(":")[0]
            
            return {
                "available": True,
                "models": models,
                "current_model": self.model,
                "model_loaded": self.model in models or any(model_base in m for m in models)
            }
            
        except Exception as e:
            logger.debug(f"Ollama check failed: {e}")
            return self._unavailable_response()
    
    def _unavailable_response(self) -> Dict[str, Any]:
        return {
            "available": False,
            "models": [],
            "current_model": self.model,
            "model_loaded": False
        }


class LLMManager:
    """LLM Manager - singleton"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.provider = OllamaProvider()
    
    def generate(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Generate response"""
        return self.provider.generate(messages, **kwargs)
    
    def check_availability(self) -> Dict[str, Any]:
        """Check LLM availability"""
        return self.provider.check_availability()
    
    def set_model(self, model: str):
        """Change current model"""
        self.provider.model = model


_llm: Optional[LLMManager] = None


def get_llm() -> LLMManager:
    global _llm
    if _llm is None:
        _llm = LLMManager()
    return _llm
