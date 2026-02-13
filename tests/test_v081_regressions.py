import tempfile
import unittest
from pathlib import Path

from core.memory import WorkingMemory
from core.plugins import PluginAPI
from web import app as web_app


class TestV081Regressions(unittest.TestCase):
    def test_working_memory_summary_contains_user_and_assistant(self):
        with tempfile.TemporaryDirectory() as td:
            wm = WorkingMemory(Path(td), max_turns=10)
            wm.add_turn("привет", "привет, как ты?")
            summary = wm.get_conversation_summary()
            self.assertIn("Пользователь:", summary)
            self.assertIn("Даша:", summary)

    def test_plugin_api_get_user_profile_safe(self):
        api = PluginAPI("voice-call", Path("plugins/voice-call"))
        profile = api.get_user_profile()
        self.assertIsInstance(profile, dict)

    def test_behavior_endpoint_no_500(self):
        class DummyMood:
            def get_behavior_hints(self):
                return {"desktop_mischief": False}

        class DummyBrain:
            mood = DummyMood()

            def get_state(self):
                return {"mood": "calm"}

        old_get_brain = web_app.get_brain
        web_app.get_brain = lambda: DummyBrain()
        try:
            client = web_app.app.test_client()
            resp = client.get("/api/behavior")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertIn("behavior", data)
            self.assertIn("state", data)
        finally:
            web_app.get_brain = old_get_brain

    def test_external_chat_mirror_endpoint(self):
        client = web_app.app.test_client()
        resp = client.post("/api/chats/external", json={
            "source": "telegram",
            "source_chat_id": "test-room",
            "role": "user",
            "content": "привет из теста"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertTrue(data.get("chat_id", "").startswith("telegram_"))

    def test_self_perception_endpoint(self):
        class DummyBrain:
            def get_self_perception(self):
                return {"self_name": "Даша", "state": {"mood": "calm"}, "traits": []}

        old_get_brain = web_app.get_brain
        web_app.get_brain = lambda: DummyBrain()
        try:
            client = web_app.app.test_client()
            resp = client.get("/api/self/perception")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("self_name"), "Даша")
        finally:
            web_app.get_brain = old_get_brain


if __name__ == "__main__":
    unittest.main()
