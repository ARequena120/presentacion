"""Cliente de WhatsApp Cloud API. Sin WHATSAPP_TOKEN funciona en modo simulado (solo registra)."""
import logging
import time
import uuid
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

log = logging.getLogger("saturna.whatsapp")
SENT_LOG: list[dict] = []  # bitácora en memoria del modo simulado (útil en desarrollo y pruebas)


@dataclass
class SendResult:
    ok: bool
    message_id: str = ""
    detail: str = ""


def mask_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) <= 4:
        return "*" * len(digits)
    return digits[:2] + "*" * (len(digits) - 4) + digits[-2:]


def is_mock() -> bool:
    s = get_settings()
    return not (s.whatsapp_token and s.whatsapp_phone_id)


def _record(entry: dict) -> SendResult:
    SENT_LOG.append(entry)
    del SENT_LOG[:-200]
    logged = dict(entry)
    if "to" in logged:
        logged["to"] = mask_phone(str(logged["to"]))
    log.info("[WhatsApp simulado] %s", logged)
    return SendResult(True, "mock-" + uuid.uuid4().hex[:12])


def _post(payload: dict) -> SendResult:
    s = get_settings()
    url = f"https://graph.facebook.com/{s.whatsapp_graph_version}/{s.whatsapp_phone_id}/messages"
    headers = {"Authorization": f"Bearer {s.whatsapp_token}"}
    last = "sin respuesta"
    for attempt in range(2):  # Máximo un reintento: 2 intentos x 8 segundos
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=8)
            body = r.text[:300]
            if 200 <= r.status_code < 300:
                message_id = r.json().get("messages", [{}])[0].get("id")
                if message_id:
                    log.info("WhatsApp status=%s message_id=%s", r.status_code, message_id)
                    return SendResult(True, str(message_id))
                log.error("WhatsApp status=%s cuerpo=%s", r.status_code, body)
                return SendResult(False, detail="Meta respondió 2xx sin message id")
            last = f"HTTP {r.status_code}: {r.text[:150]}"
            log.error("WhatsApp status=%s cuerpo=%s", r.status_code, body)
            if r.status_code < 500:  # error del cliente: no tiene sentido reintentar
                break
        except httpx.HTTPError as exc:
            last = str(exc)[:150]
            log.error("WhatsApp fallo=%s", last)
        time.sleep(0.25)
    return SendResult(False, detail=last)


def send_template(to: str, template: str, params: list[str]) -> SendResult:
    if is_mock():
        return _record({"type": "template", "to": to, "template": template, "params": params})
    s = get_settings()
    return _post(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": s.whatsapp_template_lang},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}
                ],
            },
        }
    )


def send_text(to: str, text: str) -> SendResult:
    if is_mock():
        return _record({"type": "text", "to": to, "text": text})
    return _post({"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})


def send_image(to: str, url: str, caption: str = "") -> SendResult:
    if is_mock():
        return _record({"type": "image", "to": to, "url": url, "caption": caption})
    return _post(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"link": url, "caption": caption},
        }
    )
