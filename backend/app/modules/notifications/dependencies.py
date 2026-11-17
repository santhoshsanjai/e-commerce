from typing import Annotated

from fastapi import BackgroundTasks, Depends

from app.infrastructure.email import EmailSender, get_email_sender
from app.modules.notifications.service import deliver_safely


def _send_queued_emails(
    background: BackgroundTasks, sender: Annotated[EmailSender, Depends(get_email_sender)]
) -> None:
    """After the response, send the emails this request queued. The scheduled `send-emails` task
    retries any that fail."""
    background.add_task(deliver_safely, sender)


SendQueuedEmails = Depends(_send_queued_emails)
