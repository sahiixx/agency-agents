"""Main orchestration engine for JARVIS."""

from __future__ import annotations

import re

from jarvis.automation.hotword_detector import HotwordDetector
from jarvis.automation.macros import MacroRecorder
from jarvis.automation.task_scheduler import TaskScheduler
from jarvis.automation.workflow_engine import WorkflowEngine
from jarvis.config import OWNER_NAME, RESPONSES_FILE
from jarvis.core.command_parser import CommandParser
from jarvis.core.voice_input import VoiceInput
from jarvis.core.voice_output import VoiceOutput
from jarvis.modules.app_launcher import AppLauncher
from jarvis.modules.battery_status import BatteryStatus
from jarvis.modules.calculator import Calculator
from jarvis.modules.clipboard_manager import ClipboardManager
from jarvis.modules.datetime_info import DatetimeInfo
from jarvis.modules.email_sender import EmailSender
from jarvis.modules.file_manager import FileManager
from jarvis.modules.github_manager import GitHubManager
from jarvis.modules.jokes import JokesModule
from jarvis.modules.media_player import MediaPlayer
from jarvis.modules.network_info import NetworkInfo
from jarvis.modules.news import NewsModule
from jarvis.modules.notes import NotesModule
from jarvis.modules.process_manager import ProcessManager
from jarvis.modules.reminder import ReminderModule
from jarvis.modules.screenshot import ScreenshotModule
from jarvis.modules.system_control import SystemControl
from jarvis.modules.weather import WeatherModule
from jarvis.modules.web_browser import WebBrowser
from jarvis.modules.wikipedia_search import WikipediaSearch
from jarvis.utils.helpers import choose, greeting_for_hour, load_json
from jarvis.utils.logger import setup_logger


class JarvisEngine:
    """Drive listen → parse → execute → respond loop."""

    EXIT_COMMANDS = frozenset({"goodbye", "exit", "shutdown jarvis", "quit"})

    def __init__(self) -> None:
        self.logger = setup_logger("jarvis.engine")
        self.voice_in = VoiceInput()
        self.voice_out = VoiceOutput()
        self.parser = CommandParser()
        self.hotword = HotwordDetector()
        self.scheduler = TaskScheduler()
        self.workflow = WorkflowEngine()
        self.macros = MacroRecorder()

        self.system_control = SystemControl()
        self.app_launcher = AppLauncher()
        self.file_manager = FileManager()
        self.web = WebBrowser()
        self.media = MediaPlayer()
        self.clipboard = ClipboardManager()
        self.screen = ScreenshotModule()
        self.weather = WeatherModule()
        self.news = NewsModule()
        self.email = EmailSender()
        self.reminders = ReminderModule()
        self.notes = NotesModule()
        self.calc = Calculator()
        self.wiki = WikipediaSearch()
        self.jokes = JokesModule()
        self.datetime = DatetimeInfo()
        self.battery = BatteryStatus()
        self.network = NetworkInfo()
        self.processes = ProcessManager()
        self.github = GitHubManager()

        self.responses = load_json(RESPONSES_FILE, {})

    def start(self) -> None:
        """Start scheduler, greet user, and process commands forever."""
        self.scheduler.start()
        greeting = f"{greeting_for_hour()}, {OWNER_NAME}. {self._random_response('greeting')}"
        self.respond(greeting)

        while True:
            command = self.voice_in.listen(require_wake_word=True)
            if not command:
                continue
            normalized = command.lower().strip()

            self.logger.info("Command: %s", command)
            if normalized in self.EXIT_COMMANDS:
                self.respond("Goodbye. Standing by.")
                break

            response = self.execute_command(command)
            self.respond(response)

    def execute_command(self, command: str) -> str:
        """Execute parsed command and return human-friendly response."""
        try:
            parsed = self.parser.parse(command)
            intent = parsed.get("intent", "unknown")
            lowered = command.lower()

            if intent == "system_control":
                if "volume up" in lowered:
                    return self.system_control.volume_up()
                if "volume down" in lowered:
                    return self.system_control.volume_down()
                if "mute" in lowered:
                    return self.system_control.mute()
                if "shutdown" in lowered:
                    return self.system_control.shutdown()
                if "restart" in lowered:
                    return self.system_control.restart()
                if "sleep" in lowered:
                    return self.system_control.sleep()
                if "lock" in lowered:
                    return self.system_control.lock()
                if "brightness" in lowered and "up" in lowered:
                    return self.system_control.brightness_up()
                if "brightness" in lowered and "down" in lowered:
                    return self.system_control.brightness_down()

            if intent == "launch_app":
                return self.app_launcher.open_app(lowered.replace("open", "", 1).strip())
            if intent == "close_app":
                return self.app_launcher.close_app(lowered.replace("close", "", 1).strip())
            if intent == "web":
                if "youtube" in lowered and "search" in lowered:
                    query = lowered.replace("search", "", 1).replace("youtube", "", 1).strip()
                    return self.web.youtube_search(query)
                if "search" in lowered:
                    return self.web.google_search(lowered.replace("search", "", 1).strip())
                return self.web.open_website(lowered.replace("open", "", 1).strip())
            if intent == "weather":
                match = re.search(r"(?:what(?:'s| is)\s+)?(?:the\s+)?weather(?:\s+in)?\s*(.*)", lowered)
                city = match.group(1).strip() if match else ""
                city = city or "your city"
                return self.weather.current_weather(city)
            if intent == "news":
                return " | ".join(self.news.top_headlines())
            if intent == "wikipedia":
                topic = lowered.replace("wikipedia", "").replace("search", "").strip()
                return self.wiki.summary(topic or "artificial intelligence")
            if intent == "joke":
                return self.jokes.random_joke()
            if intent == "datetime":
                return self.datetime.now()
            if intent == "battery":
                return self.battery.status()
            if intent == "network":
                return self.network.local_ip()
            if intent == "processes":
                return " | ".join(self.processes.list_processes())
            if intent == "screenshot":
                return self.screen.take_screenshot()
            if intent == "note":
                text = lowered.replace("note", "", 1).strip()
                return self.notes.save_note(text or "No content")
            if intent == "calculate":
                expr = lowered.replace("calculate", "", 1).strip()
                return self.calc.evaluate(expr)
            if intent == "media":
                if "next" in lowered:
                    return self.media.next_track()
                if "previous" in lowered:
                    return self.media.previous_track()
                return self.media.play_pause()
            if intent == "github":
                if "list repos" in lowered:
                    return " | ".join(self.github.list_repos())
                return "Say 'list repos' or 'repo status owner slash repo'."

            return self._random_response("unknown")
        except Exception:
            self.logger.exception("Command execution failed")
            return "I hit an internal error while executing that command, but I am still online."

    def respond(self, text: str) -> None:
        """Speak and log response text."""
        self.logger.info("Response: %s", text)
        self.voice_out.say(text)

    def _random_response(self, key: str) -> str:
        variants = self.responses.get(key, [])
        fallback = "At your service."
        return choose(variants, fallback)
