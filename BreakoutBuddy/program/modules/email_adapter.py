from __future__ import annotations
from typing import List, Optional
from pathlib import Path
import os, smtplib
from email.message import EmailMessage

OUTBOX = Path("Data/email_outbox")
OUTBOX.mkdir(parents=True, exist_ok=True)

def _smtp_config():
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT","587")),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "sender": os.getenv("SMTP_SENDER") or os.getenv("SMTP_USER"),
        "tls": True,
    }

def send_digest(to_addrs: List[str], subject: str, body_text: str, attachments: List[Path]) -> bool:
    cfg = _smtp_config()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["sender"] or "no-reply@localhost"
    msg["To"] = ", ".join(to_addrs or [])
    msg.set_content(body_text or "")
    for p in attachments or []:
        try:
            data = Path(p).read_bytes()
            msg.add_attachment(data, maintype="application", subtype="octet-stream", filename=Path(p).name)
        except Exception:
            pass
    # Try SMTP if configured; otherwise write .eml to outbox
    if cfg["host"] and cfg["user"] and cfg["password"] and to_addrs:
        try:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as s:
                if cfg["tls"]:
                    s.starttls()
                s.login(cfg["user"], cfg["password"])
                s.send_message(msg)
            return True
        except Exception:
            pass
    # fallback: write EML
    target = OUTBOX / f"digest_{subject.replace(' ','_')}.eml"
    target.write_bytes(msg.as_bytes())
    return False
