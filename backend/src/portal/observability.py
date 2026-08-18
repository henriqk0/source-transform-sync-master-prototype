from __future__ import annotations

import logging
import re

SENSITIVE_KEYS = {
    "email",
    "emails",
    "identification_id",
    "birthday",
    "cpf",
    "rg",
    "password",
    "password_hash",
    "value",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SENSITIVE_ALTERNATION = "|".join(re.escape(k) for k in SENSITIVE_KEYS)
KEY_VALUE_RE = re.compile(
    rf'(?P<key>["\']?(?:{_SENSITIVE_ALTERNATION})["\']?\s*[:=]\s*)(?P<value>"[^"]*"|[^,\s}}"]+)',
    re.IGNORECASE,
)
IDENTIFICATION_RE = re.compile(r"LGPD-[0-9a-f]+", re.IGNORECASE)


def mask_sensitive(text: str) -> str:
    """Redact sensitive values (emails, CPF/RG, identification ids, financial
    values) from arbitrary text. Central masking per Constitution Art. V."""
    if not text:
        return text
    text = EMAIL_RE.sub("[REDACTED]", text)
    text = IDENTIFICATION_RE.sub("[REDACTED]", text)
    text = KEY_VALUE_RE.sub(lambda m: f"{m.group('key')}[REDACTED]", text)
    return text


def mask_value(key: str, value) -> object:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)) and key.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"
    return value


def mask_payload(payload, sensitive: bool = False):
    """Recursively redact sensitive fields from a JSON-able payload."""
    if isinstance(payload, dict):
        return {
            str(k): mask_payload(v, sensitive=str(k).lower() in SENSITIVE_KEYS)
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [mask_payload(item, sensitive=sensitive) for item in payload]
    if sensitive and payload is not None:
        return "[REDACTED]"
    return payload


class SensitiveLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = mask_sensitive(str(record.msg))
            if record.args:
                record.args = tuple(mask_sensitive(str(a)) for a in record.args)
        except Exception:  # noqa: BLE001 - never break logging
            pass
        return True


_installed = False


def install_masking() -> None:
    """Apply central masking to every log record (message + traceback) and to
    the root logger's handlers (idempotent)."""
    global _installed
    if _installed:
        return
    logging.getLogger().addFilter(SensitiveLogFilter())
    factory = logging.getLogRecordFactory()

    def masked_factory(*args, **kwargs) -> logging.LogRecord:
        record = factory(*args, **kwargs)
        if record.name == "uvicorn.access":
            # Uvicorn's AccessFormatter unpacks record.args and re-formats
            # the original message; access lines carry no sensitive values
            # (URL + status only), so leave the record untouched.
            return record
        try:
            if record.args:
                record.msg = mask_sensitive(record.getMessage())
                record.args = None
            else:
                record.msg = mask_sensitive(str(record.msg))
            if record.exc_info:
                import traceback

                trace = "".join(traceback.format_exception(*record.exc_info))
                record.exc_text = mask_sensitive(trace)
        except Exception:  # noqa: BLE001 - never break logging
            pass
        return record

    logging.setLogRecordFactory(masked_factory)
    _installed = True
