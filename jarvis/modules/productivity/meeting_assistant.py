"""Meeting transcription and action-item extraction scaffolding."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class MeetingSummary:
    summary: str
    action_items: list[str]


class MeetingAssistant:
    """Summarize transcript and pull action items."""

    def summarize(self, transcript: str) -> MeetingSummary:
        lines = [line.strip() for line in transcript.splitlines() if line.strip()]
        action_items = [line for line in lines if re.search(r"\b(todo|action|follow up|next step)\b", line, re.I)]
        summary = lines[0] if lines else "No transcript available"
        return MeetingSummary(summary=summary, action_items=action_items)
