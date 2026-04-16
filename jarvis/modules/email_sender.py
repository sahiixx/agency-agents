"""Email composition and sending module."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


class EmailSender:
    """Send email using SMTP credentials from environment."""

    def send(self, to_email: str, subject: str, body: str) -> str:
        server = os.getenv("JARVIS_SMTP_SERVER", "")
        port = int(os.getenv("JARVIS_SMTP_PORT", "587"))
        username = os.getenv("JARVIS_SMTP_USERNAME", "")
        password = os.getenv("JARVIS_SMTP_PASSWORD", "")
        if not all([server, username, password]):
            return "SMTP credentials are missing. Configure JARVIS_SMTP_* variables."
        try:
            msg = EmailMessage()
            msg["From"] = username
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(body)

            with smtplib.SMTP(server, port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(username, password)
                smtp.send_message(msg)
            return f"Email sent to {to_email}."
        except Exception as exc:
            return f"Email send failed: {exc}"
