"""
DARIA Notes Plugin v1.0.0
Personal notes with tags
"""

from datetime import datetime
from typing import Dict, Any, List
import uuid

from core.plugins import DariaPlugin, PluginAPI, PluginManifest


class NotesPlugin(DariaPlugin):
    """Personal notes plugin"""
    
    def on_load(self):
        self.api.log("Notes plugin loaded")
        self.notes = self.api.load_data("notes", [])
    
    def on_unload(self):
        self.api.save_data("notes", self.notes)
    
    def on_window_open(self) -> Dict[str, Any]:
        return {"notes": self.notes}
    
    def on_window_action(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == "get_notes":
            return {"notes": self.notes}
        
        elif action == "add_note":
            note = {
                "id": str(uuid.uuid4())[:8],
                "title": data.get("title", "Без названия"),
                "content": data.get("content", ""),
                "tags": data.get("tags", []),
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
            }
            self.notes.insert(0, note)
            self._save()
            return {"status": "ok", "note": note}
        
        elif action == "update_note":
            note_id = data.get("id")
            for note in self.notes:
                if note["id"] == note_id:
                    note["title"] = data.get("title", note["title"])
                    note["content"] = data.get("content", note["content"])
                    note["tags"] = data.get("tags", note.get("tags", []))
                    note["updated"] = datetime.now().isoformat()
                    self._save()
                    return {"status": "ok", "note": note}
            return {"error": "Note not found"}
        
        elif action == "delete_note":
            note_id = data.get("id")
            self.notes = [n for n in self.notes if n["id"] != note_id]
            self._save()
            return {"status": "ok"}
        
        elif action == "search":
            query = data.get("query", "").lower()
            results = [n for n in self.notes 
                      if query in n["title"].lower() or query in n["content"].lower()]
            return {"notes": results}
        
        return {"error": "Unknown action"}
    
    def _save(self):
        self.api.save_data("notes", self.notes)
