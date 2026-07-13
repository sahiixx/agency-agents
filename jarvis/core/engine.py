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

    EXIT_COMMANDS = {"goodbye", "exit", "shutdown jarvis", "quit"}

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
