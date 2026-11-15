"""Outgoing email.

- `smtp`: any SMTP server. Locally that's Mailpit from docker-compose (web inbox on :8025).
- `ses`: Amazon SES through its API, with credentials from the task's IAM role.
- `console`: logs that an email was sent, never its body (links in it are sign-in secrets).
  For tests and for running the API on its own.
"""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

import boto3

from app.core.config import get_settings

logger = logging.getLogger("app.email")


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str


class EmailSender(Protocol):
    def send(self, email: Email) -> None: ...


class ConsoleEmailSender:
    def send(self, email: Email) -> None:
        logger.info("Email not sent (console backend): %r", email.subject)


class SmtpEmailSender:
    def __init__(self) -> None:
        self._settings = get_settings()

    def send(self, email: Email) -> None:
        s = self._settings
        msg = EmailMessage()
        msg["From"] = s.email_from
        msg["To"] = email.to
        msg["Subject"] = email.subject
        msg.set_content(email.text)
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            if s.smtp_starttls:
                smtp.starttls()
            if s.smtp_username and s.smtp_password:
                smtp.login(s.smtp_username, s.smtp_password)
            smtp.send_message(msg)


class SesEmailSender:
    def __init__(self) -> None:
        settings = get_settings()
        self._from = settings.email_from
        self._client = boto3.client("sesv2", region_name=settings.ses_region or settings.s3_region)

    def send(self, email: Email) -> None:
        self._client.send_email(
            FromEmailAddress=self._from,
            Destination={"ToAddresses": [email.to]},
            Content={
                "Simple": {
                    "Subject": {"Data": email.subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": email.text, "Charset": "UTF-8"}},
                }
            },
        )


@lru_cache
def get_email_sender() -> EmailSender:
    backend = get_settings().email_backend
    if backend == "smtp":
        return SmtpEmailSender()
    if backend == "ses":
        return SesEmailSender()
    return ConsoleEmailSender()


def send_safely(sender: EmailSender, email: Email) -> None:
    """For background tasks: a mail failure is logged, never shown to the person (it would reveal
    whether the address has an account)."""
    try:
        sender.send(email)
    except Exception:
        logger.exception("Sending email %r failed", email.subject)
