"""
DARIA Plugin System v0.8.1
Fixed: catalog download, auto-install from plugins folder
"""

import os
import sys
import json
import shutil
import logging
import importlib
import importlib.util
import subprocess
import zipfile
import tempfile
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, TYPE_CHECKING
from datetime import datetime
from abc import ABC, abstractmethod
from io import BytesIO

if TYPE_CHECKING:
    from .brain import DariaBrain
    from .memory import MemoryManager
    from .llm import LLMManager

logger = logging.getLogger("daria.plugins")

try:
    import yaml
    HAS_YAML = True
except ImportError:
    yaml = None
    HAS_YAML = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    requests = None
    HAS_REQUESTS = False

from .config import get_config


# ════════════════════════════════════════════════════════════════════
#  Plugin Data Classes
# ════════════════════════════════════════════════════════════════════

@dataclass
class PluginManifest:
    """Plugin manifest from plugin.yaml"""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = "Unknown"
    icon: str = "🧩"
    category: str = "general"
    
    has_desktop_icon: bool = False
    desktop_icon: str = ""
    desktop_title: str = ""
    
    has_window: bool = False
    window_title: str = ""
    window_size: Dict[str, int] = field(default_factory=lambda: {"width": 400, "height": 300})
    window_template: str = ""
    
    entry_point: str = "main.py"
    main_class: str = "Plugin"
    
    static_dir: str = "static"
    templates_dir: str = "templates"
    
    dependencies: List[str] = field(default_factory=list)
    python_dependencies: List[str] = field(default_factory=list)
    
    capabilities: List[str] = field(default_factory=list)
    
    repository_url: str = ""
    download_url: str = ""
    homepage: str = ""
    license: str = "MIT"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginManifest':
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            author=data.get('author', 'Unknown'),
            icon=data.get('icon', '🧩'),
            category=data.get('category', 'general'),
            has_desktop_icon=data.get('has_desktop_icon', False),
            desktop_icon=data.get('desktop_icon', ''),
            desktop_title=data.get('desktop_title', ''),
            has_window=data.get('has_window', False),
            window_title=data.get('window_title', ''),
            window_size=data.get('window_size', {"width": 400, "height": 300}),
            window_template=data.get('window_template', ''),
            entry_point=data.get('entry_point', 'main.py'),
            main_class=data.get('main_class', 'Plugin'),
            static_dir=data.get('static_dir', 'static'),
            templates_dir=data.get('templates_dir', 'templates'),
            dependencies=data.get('dependencies', []),
            python_dependencies=data.get('python_dependencies', []),
            capabilities=data.get('capabilities', []),
            repository_url=data.get('repository_url', ''),
            download_url=data.get('download_url', ''),
            homepage=data.get('homepage', ''),
            license=data.get('license', 'MIT'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'icon': self.icon,
            'category': self.category,
            'has_desktop_icon': self.has_desktop_icon,
            'desktop_icon': self.desktop_icon,
            'desktop_title': self.desktop_title,
            'has_window': self.has_window,
            'window_title': self.window_title,
            'window_size': self.window_size,
        }


@dataclass
class PluginState:
    """Runtime state of a plugin"""
    manifest: PluginManifest
    path: Path
    enabled: bool = True
    loaded: bool = False
    instance: Optional['DariaPlugin'] = None
    error: Optional[str] = None
    venv_path: Optional[Path] = None
    deps_installed: bool = False


# ════════════════════════════════════════════════════════════════════
#  Plugin API
# ════════════════════════════════════════════════════════════════════

class PluginAPI:
    """API provided to plugins"""
    
    def __init__(self, plugin_id: str, plugin_path: Path):
        self.plugin_id = plugin_id
        self.plugin_path = plugin_path
        self._brain = None
        self._memory = None
        self._llm = None
        self._config = get_config()
    
    @property
    def data_dir(self) -> Path:
        path = self._config.data_dir / "plugins" / self.plugin_id / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def log(self, message: str, level: str = "info"):
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.plugin_id}] {message}")
    
    def save_data(self, key: str, data: Any):
        file_path = self.data_dir / f"{key}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_data(self, key: str, default: Any = None) -> Any:
        file_path = self.data_dir / f"{key}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    
    def get_brain(self):
        if self._brain is None:
            try:
                from .brain import get_brain
                self._brain = get_brain()
            except:
                pass
        return self._brain
    
    def get_memory(self):
        if self._memory is None:
            try:
                from .memory import get_memory
                self._memory = get_memory()
            except:
                pass
        return self._memory

    def get_user_profile(self) -> Dict[str, Any]:
        memory = self.get_memory()
        return memory.get_user_profile() if memory else {}

    def set_user_profile(self, key: str, value: str):
        memory = self.get_memory()
        if memory:
            memory.set_user_profile(key, value)

    def remember(self, content: str, importance: float = 0.5) -> Optional[str]:
        memory = self.get_memory()
        if memory:
            return memory.remember(content, importance=importance)
        return None

    def store_fact(self, key: str, value: str):
        memory = self.get_memory()
        if memory:
            memory.set_user_profile(key, value)

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        memory = self.get_memory()
        if not memory:
            return []
        return [m.to_dict() for m in memory.recall(query, limit=limit)]

    def add_to_conversation(self, user_message: str, assistant_response: str, emotion: str = "neutral"):
        memory = self.get_memory()
        if memory:
            memory.add_exchange(user_message, assistant_response, emotion)

    def get_data_path(self) -> Path:
        return self.data_dir

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if self._llm is None:
            try:
                from .llm import get_llm
                self._llm = get_llm()
            except Exception:
                return {"error": "LLM unavailable"}
        try:
            response = self._llm.generate(messages, **kwargs)
            return {"content": response.content, "model": response.model, "tokens_used": response.tokens_used}
        except Exception as e:
            return {"error": str(e)}

    def generate_with_context(self, prompt: str, include_history: bool = True, limit: int = 10, **kwargs) -> Dict[str, Any]:
        messages: List[Dict[str, str]] = []
        if include_history:
            memory = self.get_memory()
            if memory:
                messages.extend(memory.get_context_for_llm(limit=limit))
        messages.append({"role": "user", "content": prompt})
        return self.generate(messages, **kwargs)
    
    def send_message(self, text: str) -> Dict[str, Any]:
        brain = self.get_brain()
        if brain:
            return brain.process_message(text)
        return {"response": "Brain unavailable", "error": True}
    
    def send_notification(self, title: str, message: str, type: str = "info", action: str = None):
        """Send notification to web interface"""
        try:
            if HAS_REQUESTS:
                requests.post('http://127.0.0.1:7777/api/notifications/add', json={
                    "title": title, "message": message, "type": type, "action": action
                }, timeout=1)
        except:
            pass


# ════════════════════════════════════════════════════════════════════
#  Base Plugin Class
# ════════════════════════════════════════════════════════════════════

class DariaPlugin(ABC):
    """Base class for all DARIA plugins"""
    
    def __init__(self, api: PluginAPI, manifest: PluginManifest):
        self.api = api
        self.manifest = manifest
    
    def on_load(self):
        pass
    
    def on_unload(self):
        pass
    
    def on_chat_message(self, message: str) -> Optional[str]:
        return None
    
    def on_chat_response(self, message: str, response: str) -> Optional[str]:
        return None
    
    def on_window_open(self) -> Dict[str, Any]:
        return {}
    
    def on_window_close(self):
        pass
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"error": "Not implemented"}


# ════════════════════════════════════════════════════════════════════
#  Plugin Manager
# ════════════════════════════════════════════════════════════════════

class PluginManager:
    """Manages plugin discovery, loading, and lifecycle"""
    
    CATALOG_URL = "https://raw.githubusercontent.com/dariumi/Daria-Plagins/refs/heads/main/catalog.yaml"
    
    def __init__(self):
        self._config = get_config()
        self._plugins: Dict[str, PluginState] = {}
        self._hooks: Dict[str, List[tuple]] = {
            "chat_message": [],
            "chat_response": [],
        }
        self._catalog_cache: Optional[List[Dict]] = None
        self._catalog_cache_time: Optional[datetime] = None
        
        self._copy_bundled_plugins()
        self.discover_plugins()
        self.load_all_plugins()
    
    @property
    def plugins_dir(self) -> Path:
        return self._config.data_dir / "plugins"
    
    def _copy_bundled_plugins(self):
        """Copy plugins from installation folder to data dir"""
        # Check for bundled plugins in app directory
        app_plugins = Path(__file__).parent.parent / "plugins"
        if not app_plugins.exists():
            return
        
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        for plugin_dir in app_plugins.iterdir():
            if not plugin_dir.is_dir():
                continue
            if not (plugin_dir / "plugin.yaml").exists():
                continue
            
            dest = self.plugins_dir / plugin_dir.name
            if not dest.exists():
                logger.info(f"Installing bundled plugin: {plugin_dir.name}")
                shutil.copytree(plugin_dir, dest)
    
    # ─── Plugin Discovery ───────────────────────────────────────────
    
    def discover_plugins(self):
        """Discover installed plugins"""
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                continue
            
            try:
                manifest = self._load_manifest(manifest_path)
                if manifest:
                    venv_path = plugin_dir / "venv"
                    self._plugins[manifest.id] = PluginState(
                        manifest=manifest,
                        path=plugin_dir,
                        venv_path=venv_path if venv_path.exists() else None,
                        deps_installed=venv_path.exists() or not manifest.python_dependencies
                    )
                    logger.debug(f"Discovered plugin: {manifest.name}")
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_dir}: {e}")
    
    def _load_manifest(self, path: Path) -> Optional[PluginManifest]:
        if not HAS_YAML:
            logger.warning("PyYAML not installed")
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return PluginManifest.from_dict(data)
    
    # ─── Plugin Dependencies ────────────────────────────────────────
    
    def _setup_plugin_venv(self, plugin_id: str) -> bool:
        """Create isolated venv and install dependencies"""
        if plugin_id not in self._plugins:
            return False
        
        state = self._plugins[plugin_id]
        
        if not state.manifest.python_dependencies:
            state.deps_installed = True
            return True
        
        venv_path = state.path / "venv"
        
        # Create venv
        if not venv_path.exists():
            logger.info(f"Creating venv for {plugin_id}...")
            try:
                import venv
                venv.create(venv_path, with_pip=True)
            except Exception as e:
                logger.error(f"Failed to create venv: {e}")
                return False
        
        # Get pip path
        if sys.platform == 'win32':
            pip_path = venv_path / 'Scripts' / 'pip.exe'
        else:
            pip_path = venv_path / 'bin' / 'pip'
        
        if not pip_path.exists():
            logger.error(f"Pip not found for {plugin_id}")
            return False
        
        # Install dependencies
        logger.info(f"Installing deps for {plugin_id}: {state.manifest.python_dependencies}")
        try:
            for dep in state.manifest.python_dependencies:
                subprocess.run(
                    [str(pip_path), 'install', dep, '-q'],
                    check=True, capture_output=True
                )
            state.venv_path = venv_path
            state.deps_installed = True
            return True
        except Exception as e:
            logger.error(f"Failed to install deps: {e}")
            return False
    
    def _activate_plugin_venv(self, plugin_id: str):
        """Add plugin's venv to sys.path"""
        state = self._plugins.get(plugin_id)
        if not state or not state.venv_path:
            return
        
        if sys.platform == 'win32':
            site_packages = state.venv_path / 'Lib' / 'site-packages'
        else:
            for p in (state.venv_path / 'lib').iterdir():
                if p.name.startswith('python'):
                    site_packages = p / 'site-packages'
                    break
            else:
                return
        
        if site_packages.exists() and str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))
    
    # ─── Plugin Loading ─────────────────────────────────────────────
    
    def load_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        
        state = self._plugins[plugin_id]
        if state.loaded:
            return True
        
        try:
            # Setup venv if needed
            if state.manifest.python_dependencies and not state.deps_installed:
                if not self._setup_plugin_venv(plugin_id):
                    state.error = "Failed to install dependencies"
                    return False
            
            self._activate_plugin_venv(plugin_id)
            
            api = PluginAPI(plugin_id, state.path)
            
            entry_point = state.path / state.manifest.entry_point
            if not entry_point.exists():
                raise FileNotFoundError(f"Entry point not found: {entry_point}")
            
            spec = importlib.util.spec_from_file_location(
                f"daria_plugins.{plugin_id}", entry_point
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            plugin_class = getattr(module, state.manifest.main_class, None)
            if plugin_class is None:
                raise AttributeError(f"Class {state.manifest.main_class} not found")
            
            instance = plugin_class(api, state.manifest)
            instance.on_load()
            
            state.instance = instance
            state.loaded = True
            state.error = None
            
            self._register_plugin_hooks(plugin_id, instance)
            logger.info(f"Loaded plugin: {state.manifest.name}")
            return True
            
        except Exception as e:
            state.error = str(e)
            logger.error(f"Failed to load {plugin_id}: {e}")
            return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        
        state = self._plugins[plugin_id]
        if not state.loaded:
            return True
        
        try:
            if state.instance:
                state.instance.on_unload()
            self._unregister_plugin_hooks(plugin_id)
            state.instance = None
            state.loaded = False
            return True
        except Exception as e:
            logger.error(f"Failed to unload {plugin_id}: {e}")
            return False
    
    def load_all_plugins(self):
        for plugin_id in self._plugins:
            if self._plugins[plugin_id].enabled:
                self.load_plugin(plugin_id)
    
    # ─── Hooks ──────────────────────────────────────────────────────
    
    def _register_plugin_hooks(self, plugin_id: str, instance: DariaPlugin):
        if hasattr(instance, 'on_chat_message'):
            self._hooks["chat_message"].append((plugin_id, instance.on_chat_message))
        if hasattr(instance, 'on_chat_response'):
            self._hooks["chat_response"].append((plugin_id, instance.on_chat_response))
    
    def _unregister_plugin_hooks(self, plugin_id: str):
        for hook_name in self._hooks:
            self._hooks[hook_name] = [
                (pid, func) for pid, func in self._hooks[hook_name]
                if pid != plugin_id
            ]
    
    def execute_hook(self, hook_name: str, *args) -> Optional[Any]:
        result = None
        for plugin_id, func in self._hooks.get(hook_name, []):
            try:
                r = func(*args)
                if r is not None:
                    result = r
            except Exception as e:
                logger.error(f"Hook error [{plugin_id}]: {e}")
        return result
    
    # ─── Plugin Info ────────────────────────────────────────────────
    
    def get_installed_plugins(self) -> List[PluginState]:
        return list(self._plugins.values())
    
    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        state = self._plugins.get(plugin_id)
        if not state:
            return None
        return {
            **state.manifest.to_dict(),
            "installed": True,
            "enabled": state.enabled,
            "loaded": state.loaded,
            "error": state.error,
        }
    
    def get_desktop_plugins(self) -> List[Dict[str, Any]]:
        result = []
        for state in self._plugins.values():
            if state.manifest.has_desktop_icon or state.manifest.has_window:
                result.append({
                    "id": state.manifest.id,
                    "icon": state.manifest.desktop_icon or state.manifest.icon,
                    "title": state.manifest.desktop_title or state.manifest.name,
                    "has_window": state.manifest.has_window,
                })
        return result
    
    def get_plugin_window_data(self, plugin_id: str) -> Dict[str, Any]:
        state = self._plugins.get(plugin_id)
        if not state:
            return {"error": "Not found"}
        
        data = {}
        if state.instance:
            try:
                data = state.instance.on_window_open()
            except Exception as e:
                logger.error(f"Window open error [{plugin_id}]: {e}")
        
        return {"manifest": state.manifest.to_dict(), "data": data}
    
    def call_plugin_action(self, plugin_id: str, action: str, data: Dict) -> Dict[str, Any]:
        state = self._plugins.get(plugin_id)
        if not state or not state.instance:
            return {"error": "Not available"}
        
        try:
            return state.instance.on_window_action(action, data)
        except Exception as e:
            return {"error": str(e)}
    
    # ─── Plugin Installation ────────────────────────────────────────

    @staticmethod
    def _version_key(version: str) -> List[int]:
        nums = [int(x) for x in re.findall(r"\d+", str(version or ""))]
        return nums if nums else [0]

    def _find_catalog_item(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        for item in self.fetch_catalog():
            if item.get("id") == plugin_id:
                return item
        return None

    def _download_plugin_zip(self, plugin_id: str, download_url: str) -> Optional[bytes]:
        if not HAS_REQUESTS:
            logger.error("requests not installed")
            return None
        logger.info(f"Downloading plugin {plugin_id}...")
        response = requests.get(download_url, timeout=30)
        if response.status_code != 200:
            logger.error(f"Download failed: {response.status_code}")
            return None
        return response.content

    def _extract_zip(self, archive: bytes, target_dir: Path):
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(BytesIO(archive)) as zf:
            names = zf.namelist()
            top = [n for n in names if n and not n.endswith('/') and not n.startswith("__MACOSX")]
            root = None
            if top and "/" in top[0]:
                candidate = top[0].split("/", 1)[0]
                if all(n.startswith(candidate + "/") or n == candidate + "/" for n in names):
                    root = candidate

            for name in names:
                if name.endswith('/') or name.startswith("__MACOSX"):
                    continue
                rel_name = name[len(root) + 1:] if root and name.startswith(root + "/") else name
                if not rel_name:
                    continue
                target = target_dir / rel_name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))

    def _install_from_archive(self, plugin_id: str, archive: bytes, replacing: bool = False) -> bool:
        plugin_dir = self.plugins_dir / plugin_id
        backup_data = None
        try:
            with tempfile.TemporaryDirectory(prefix=f"daria-plugin-{plugin_id}-") as td:
                unpacked = Path(td) / "plugin"
                self._extract_zip(archive, unpacked)
                if not (unpacked / "plugin.yaml").exists():
                    logger.error(f"Invalid plugin archive for {plugin_id}: plugin.yaml not found")
                    return False

                if replacing and plugin_id in self._plugins:
                    state = self._plugins[plugin_id]
                    self.unload_plugin(plugin_id)
                    data_dir = state.path / "data"
                    if data_dir.exists():
                        backup_data = Path(td) / "data_backup"
                        shutil.copytree(data_dir, backup_data)
                    if state.path.exists():
                        shutil.rmtree(state.path)
                    plugin_dir = state.path
                elif plugin_dir.exists() and not replacing:
                    logger.info(f"Plugin {plugin_id} already exists")
                    return True

                shutil.copytree(unpacked, plugin_dir, dirs_exist_ok=True)

                if backup_data and backup_data.exists():
                    restored = plugin_dir / "data"
                    if restored.exists():
                        shutil.rmtree(restored)
                    shutil.copytree(backup_data, restored)

                (plugin_dir / ".installed").write_text(datetime.now().isoformat(), encoding="utf-8")

            self.discover_plugins()
            if plugin_id in self._plugins:
                return self.load_plugin(plugin_id)
            return False
        except Exception as e:
            logger.error(f"Install failed [{plugin_id}]: {e}")
            return False
    
    def install_plugin(self, plugin_id: str) -> bool:
        """Install plugin from catalog"""
        if plugin_id in self._plugins:
            logger.info(f"Plugin {plugin_id} already installed")
            return True

        plugin_info = self._find_catalog_item(plugin_id)
        if not plugin_info:
            logger.error(f"Plugin {plugin_id} not found in catalog")
            return False

        download_url = plugin_info.get("download_url")
        if not download_url:
            logger.error(f"No download URL for {plugin_id}")
            return False

        archive = self._download_plugin_zip(plugin_id, download_url)
        if not archive:
            return False
        return self._install_from_archive(plugin_id, archive, replacing=False)

    def check_plugin_updates(self) -> List[Dict[str, Any]]:
        updates: List[Dict[str, Any]] = []
        catalog = {item.get("id"): item for item in self.fetch_catalog()}
        for plugin_id, state in self._plugins.items():
            item = catalog.get(plugin_id)
            if not item:
                continue
            current = state.manifest.version or "0.0.0"
            latest = item.get("version", current)
            if self._version_key(latest) > self._version_key(current):
                updates.append({
                    "id": plugin_id,
                    "name": state.manifest.name,
                    "current_version": current,
                    "latest_version": latest,
                    "download_url": item.get("download_url", ""),
                })
        return updates

    def update_plugin(self, plugin_id: str) -> bool:
        state = self._plugins.get(plugin_id)
        if not state:
            return False
        item = self._find_catalog_item(plugin_id)
        if not item:
            return False
        latest = item.get("version", state.manifest.version or "0.0.0")
        if self._version_key(latest) <= self._version_key(state.manifest.version or "0.0.0"):
            return True
        download_url = item.get("download_url")
        if not download_url:
            return False
        archive = self._download_plugin_zip(plugin_id, download_url)
        if not archive:
            return False
        return self._install_from_archive(plugin_id, archive, replacing=True)

    def update_all_plugins(self) -> Dict[str, Any]:
        updates = self.check_plugin_updates()
        results = []
        for item in updates:
            pid = item["id"]
            ok = self.update_plugin(pid)
            results.append({"id": pid, "status": "ok" if ok else "error"})
        return {"total": len(updates), "results": results}
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        
        self.unload_plugin(plugin_id)
        
        state = self._plugins[plugin_id]
        if state.path.exists():
            shutil.rmtree(state.path)
        
        del self._plugins[plugin_id]
        logger.info(f"Uninstalled: {plugin_id}")
        return True
    
    # ─── Catalog ────────────────────────────────────────────────────
    
    def fetch_catalog(self) -> List[Dict[str, Any]]:
        """Fetch plugin catalog"""
        if self._catalog_cache and self._catalog_cache_time:
            age = (datetime.now() - self._catalog_cache_time).total_seconds()
            if age < 300:
                return self._catalog_cache
        
        if HAS_REQUESTS and HAS_YAML:
            try:
                response = requests.get(self.CATALOG_URL, timeout=10)
                if response.status_code == 200:
                    data = yaml.safe_load(response.text)
                    catalog = data.get('plugins', [])
                    
                    for item in catalog:
                        item['installed'] = item.get('id') in self._plugins
                    
                    self._catalog_cache = catalog
                    self._catalog_cache_time = datetime.now()
                    return catalog
            except Exception as e:
                logger.debug(f"Catalog fetch failed: {e}")
        
        return self._get_builtin_catalog()
    
    def _get_builtin_catalog(self) -> List[Dict[str, Any]]:
        catalog = []
        for state in self._plugins.values():
            catalog.append({
                **state.manifest.to_dict(),
                "installed": True,
            })
        return catalog


# ════════════════════════════════════════════════════════════════════
#  Singleton
# ════════════════════════════════════════════════════════════════════

_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
