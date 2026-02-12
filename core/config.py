"""
DARIA Config v0.8.1
Configuration management
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml

logger = logging.getLogger("daria")


@dataclass
class WebConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "llama3.1:8b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class VoiceConfig:
    tts_enabled: bool = False
    stt_enabled: bool = False
    language: str = "ru"


@dataclass
class DariaPersona:
    mode: str = "adaptive"
    name: str = "Дарья"


@dataclass
class PluginsConfig:
    enabled: bool = True
    repository: str = "https://github.com/dariumi/Daria-Plagins"
    auto_update: bool = False


@dataclass
class DariaConfig:
    version: str = "0.8.1"
    web: WebConfig = field(default_factory=WebConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    daria: DariaPersona = field(default_factory=DariaPersona)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    data_dir: Path = field(default_factory=lambda: Path.home() / ".daria")
    
    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "plugins").mkdir(exist_ok=True)


_config: Optional[DariaConfig] = None


def get_config() -> DariaConfig:
    """Get configuration (singleton)"""
    global _config
    if _config is None:
        _config = DariaConfig()
        _load_from_file(_config)
        _load_from_env(_config)
    return _config


def _load_from_file(config: DariaConfig):
    """Load from config.yaml"""
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    if not config_file.exists():
        return
    
    try:
        data = yaml.safe_load(config_file.read_text())
        if not data:
            return
        
        sections = [
            ("web", config.web),
            ("llm", config.llm),
            ("voice", config.voice),
            ("daria", config.daria),
            ("plugins", config.plugins),
        ]
        
        for name, obj in sections:
            if name in data and isinstance(data[name], dict):
                for k, v in data[name].items():
                    if hasattr(obj, k):
                        setattr(obj, k, v)
                        
    except Exception as e:
        logger.warning(f"Config file error: {e}")


def _load_from_env(config: DariaConfig):
    """Load from environment variables"""
    env_mappings = {
        "DARIA_HOST": ("web", "host", str),
        "DARIA_PORT": ("web", "port", int),
        "DARIA_DEBUG": ("web", "debug", lambda x: x.lower() in ("true", "1", "yes")),
        "OLLAMA_MODEL": ("llm", "model", str),
        "OLLAMA_URL": ("llm", "base_url", str),
        "DARIA_MODE": ("daria", "mode", str),
    }
    
    for env_var, (section, attr, converter) in env_mappings.items():
        value = os.getenv(env_var)
        if value:
            try:
                section_obj = getattr(config, section)
                setattr(section_obj, attr, converter(value))
            except Exception as e:
                logger.warning(f"Failed to set {env_var}: {e}")
