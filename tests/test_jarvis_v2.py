import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import config
from jarvis.automation.voice_macros import VoiceMacros
from jarvis.modules.ai_brain import AIBrain
from jarvis.modules.knowledge_base import KnowledgeBase
from jarvis.plugins.plugin_manager import PluginManager


class TestJarvisConfig(unittest.TestCase):
    def test_required_config_flags_exist(self):
        self.assertTrue(hasattr(config, "OLLAMA_MODEL"))
        self.assertTrue(hasattr(config, "OLLAMA_URL"))
        self.assertTrue(hasattr(config, "USE_WHISPER"))
        self.assertTrue(hasattr(config, "TTS_ENGINE"))
        self.assertTrue(hasattr(config, "DASHBOARD_PORT"))


class TestAIBrainFallback(unittest.TestCase):
    def test_keyword_fallback_when_ollama_unavailable(self):
        brain = AIBrain(model="llama3", base_url="http://localhost:11434")
        with patch("jarvis.modules.ai_brain.requests.post", side_effect=RuntimeError("offline")):
            response = brain.ask("JARVIS explain quantum computing")
        self.assertEqual(response.source, "fallback")
        self.assertIn("Quantum", response.text)


class TestKnowledgeBase(unittest.TestCase):
    def test_add_and_search(self):
        with tempfile.TemporaryDirectory() as td:
            kb = KnowledgeBase(db_path=str(Path(td) / "kb.db"))
            kb.add_document("note.txt", "hello local rag world")
            rows = kb.search("rag")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "note.txt")


class TestPluginSystem(unittest.TestCase):
    def test_discover_enable_run_plugin(self):
        plugin_dir = Path(__file__).parent.parent / "jarvis" / "plugins"
        manager = PluginManager(plugin_dir=str(plugin_dir))
        names = manager.discover()
        self.assertIn("example", names)
        self.assertTrue(manager.enable("example"))
        self.assertIn("executed", manager.run("example", "ping"))


class TestVoiceMacros(unittest.TestCase):
    def test_record_and_playback(self):
        vm = VoiceMacros()
        vm.start_recording("work setup")
        vm.record_step("open editor")
        vm.record_step("start server")
        vm.stop_recording()
        self.assertEqual(vm.play("work setup"), ["open editor", "start server"])


if __name__ == "__main__":
    unittest.main()
