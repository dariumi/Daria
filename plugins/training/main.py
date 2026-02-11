"""
DARIA Training Plugin v1.0.0
Help Daria learn better responses
"""

import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from core.plugins import DariaPlugin, PluginAPI, PluginManifest


class TrainingPlugin(DariaPlugin):
    """Training plugin for improving responses"""
    
    CATEGORIES = {
        "greeting": "Приветствия",
        "farewell": "Прощания",
        "thanks": "Благодарности",
        "question": "Вопросы",
        "emotion": "Эмоции",
        "time": "Время суток",
        "general": "Общее",
    }
    
    def on_load(self):
        self.api.log("Training plugin loaded")
        self.examples = self.api.load_data("examples", {
            "greeting": [],
            "farewell": [],
            "thanks": [],
            "question": [],
            "emotion": [],
            "time": [],
            "general": [],
        })
        self.style_notes = self.api.load_data("style", {
            "avoid_phrases": [],
            "preferred_phrases": [],
            "notes": "",
        })
    
    def on_window_open(self) -> Dict[str, Any]:
        return {
            "categories": self.CATEGORIES,
            "examples": self.examples,
            "style": self.style_notes,
            "total": sum(len(v) for v in self.examples.values()),
        }
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "add_example":
            category = data.get("category", "general")
            example = {
                "input": data.get("input", ""),
                "output": data.get("output", ""),
                "context": data.get("context", ""),
                "created": datetime.now().isoformat(),
            }
            
            if not example["input"] or not example["output"]:
                return {"error": "Заполни сообщение и ответ"}
            
            if category not in self.examples:
                self.examples[category] = []
            
            self.examples[category].append(example)
            self._save()
            
            return {"status": "ok", "example": example}
        
        elif action == "delete_example":
            category = data.get("category")
            index = data.get("index")
            
            if category in self.examples and 0 <= index < len(self.examples[category]):
                del self.examples[category][index]
                self._save()
                return {"status": "ok"}
            
            return {"error": "Example not found"}
        
        elif action == "get_examples":
            category = data.get("category", "all")
            if category == "all":
                return {"examples": self.examples}
            return {"examples": self.examples.get(category, [])}
        
        elif action == "save_style":
            self.style_notes = {
                "avoid_phrases": data.get("avoid_phrases", []),
                "preferred_phrases": data.get("preferred_phrases", []),
                "notes": data.get("notes", ""),
            }
            self.api.save_data("style", self.style_notes)
            return {"status": "ok"}
        
        elif action == "export":
            return {
                "data": {
                    "examples": self.examples,
                    "style": self.style_notes,
                    "exported": datetime.now().isoformat(),
                }
            }
        
        elif action == "import":
            imported = data.get("data", {})
            if "examples" in imported:
                for cat, examples in imported["examples"].items():
                    if cat not in self.examples:
                        self.examples[cat] = []
                    self.examples[cat].extend(examples)
            if "style" in imported:
                self.style_notes.update(imported["style"])
            self._save()
            return {"status": "ok", "imported": True}
        
        return {"error": "Unknown action"}
    
    def _save(self):
        self.api.save_data("examples", self.examples)
    
    def get_training_context(self) -> str:
        """Get training context for LLM prompt"""
        context_parts = []
        
        # Style notes
        if self.style_notes.get("notes"):
            context_parts.append(f"ЗАМЕТКИ ПО СТИЛЮ:\n{self.style_notes['notes']}")
        
        if self.style_notes.get("avoid_phrases"):
            avoid = ", ".join(self.style_notes["avoid_phrases"])
            context_parts.append(f"ИЗБЕГАЙ ФРАЗ: {avoid}")
        
        if self.style_notes.get("preferred_phrases"):
            prefer = ", ".join(self.style_notes["preferred_phrases"])
            context_parts.append(f"ИСПОЛЬЗУЙ ФРАЗЫ: {prefer}")
        
        # Examples
        for category, examples in self.examples.items():
            if examples:
                cat_name = self.CATEGORIES.get(category, category)
                context_parts.append(f"\n═══ ПРИМЕРЫ ({cat_name}) ═══")
                for ex in examples[-3:]:  # Last 3 examples per category
                    context_parts.append(f"Пользователь: {ex['input']}")
                    context_parts.append(f"Даша: {ex['output']}")
        
        return "\n".join(context_parts)
