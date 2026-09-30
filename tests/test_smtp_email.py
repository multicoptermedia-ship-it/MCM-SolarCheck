from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPEmailSender
from mcm_solarcheck.services.email import EmailAttachment, EmailMessage


def test_smtp_sender_builds_pdf_mime_attachment_and_uses_starttls() -> None:
    config = SMTPConfig("smtp.example.com", 587, "solarcheck@example.com")
    sender = SMTPEmailSender(config, "secret-password")
    message = EmailMessage(
        sender="solarcheck@example.com",
        recipient="solarcheck@mcm-dronetech.com",
        subject="SolarCheck Rechnung R-1",
        text="Rechnung im Anhang.",
        attachments=(EmailAttachment("R-1.pdf", b"%PDF invoice", "application/pdf"),),
    )
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp

    with patch("mcm_solarcheck.infrastructure.smtp_email.smtplib.SMTP", return_value=smtp):
        sender.send(message)

    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("solarcheck@example.com", "secret-password")
    sent = smtp.send_message.call_args.args[0]
    assert sent["To"] == "solarcheck@mcm-dronetech.com"
    assert sent["Subject"] == "SolarCheck Rechnung R-1"
    attachments = list(sent.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "R-1.pdf"
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_payload(decode=True) == b"%PDF invoice"


def test_smtp_config_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="port"):
        SMTPConfig("smtp.example.com", 0, "solarcheck@example.com")


def test_smtp_sender_rejects_missing_password() -> None:
    with pytest.raises(ValueError, match="password"):
        SMTPEmailSender(SMTPConfig("smtp.example.com", 587, "user"), "")
