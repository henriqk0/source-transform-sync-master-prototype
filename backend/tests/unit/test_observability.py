import json
import logging

from uvicorn.logging import AccessFormatter

from portal.observability import (
    install_masking,
    mask_payload,
    mask_sensitive,
)


class TestMaskSensitive:
    def test_redacts_email_value_in_text(self):
        masked = mask_sensitive("user wrote email joao.silva@ifes.edu.br in the report")
        assert "joao.silva@ifes.edu.br" not in masked
        assert "[REDACTED]" in masked

    def test_redacts_sensitive_key_values(self):
        line = 'login failed: {"username": "admin", "password": "hunter2"}'
        assert "hunter2" not in mask_sensitive(line)

    def test_redacts_identification_and_birthday(self):
        line = "identification_id=LGPD-abc123 birthday=1990-01-01"
        masked = mask_sensitive(line)
        assert "LGPD-abc123" not in masked
        assert "1990-01-01" not in masked

    def test_redacts_financial_value(self):
        masked = mask_sensitive('{"fellowship": {"value": 2500.5}}')
        assert "2500.5" not in masked

    def test_leaves_public_fields_untouched(self):
        line = "researcher Carlos Roberto Pires Campos, article A1"
        assert mask_sensitive(line) == line


class TestMaskPayload:
    def test_masks_nested_dict_recursively(self):
        payload = {
            "name": "Maria Souza",
            "emails": ["maria@ifes.edu.br"],
            "nested": {"birthday": "1985-05-05", "cpf": "123.456.789-00"},
            "articles": [{"title": "T1"}],
        }
        masked = mask_payload(payload)
        assert masked["emails"] == ["[REDACTED]"]
        assert masked["nested"]["birthday"] == "[REDACTED]"
        assert masked["nested"]["cpf"] == "[REDACTED]"
        assert masked["name"] == "Maria Souza"
        assert masked["articles"][0]["title"] == "T1"

    def test_masks_case_insensitively(self):
        masked = mask_payload({"Email": "a@b.c", "IDentification_ID": "x"})
        assert masked["Email"] == "[REDACTED]"
        assert masked["IDentification_ID"] == "[REDACTED]"

    def test_masks_key_names_only_when_value_is_string_or_number(self):
        masked = mask_payload({"emails": None, "password": 123456})
        assert masked["emails"] is None
        assert masked["password"] == "[REDACTED]"


class TestLoggingFilter:
    def test_log_records_are_masked(self, caplog):
        install_masking()
        logger = logging.getLogger("portal.test")
        with caplog.at_level(logging.INFO, logger="portal.test"):
            logger.info("sync error for email %s", "x@y.z")
        assert "x@y.z" not in caplog.text
        assert "[REDACTED]" in caplog.text

    def test_keyed_sensitive_values_masked_in_logs(self, caplog):
        install_masking()
        logger = logging.getLogger("portal.test.keyed")
        with caplog.at_level(logging.INFO, logger="portal.test.keyed"):
            logger.info("fellowship value=%s rejected", 99)
        assert "99" not in caplog.text
        assert "[REDACTED]" in caplog.text

    def test_exception_logging_masked(self, caplog):
        install_masking()
        logger = logging.getLogger("portal.test.err")
        try:
            raise ValueError("email maria@ifes.edu.br leaked")
        except ValueError:
            with caplog.at_level(logging.ERROR, logger="portal.test.err"):
                logger.exception("boom")
        assert "maria@ifes.edu.br" not in caplog.text

    def test_json_blob_logged_is_masked(self, caplog):
        install_masking()
        logger = logging.getLogger("portal.test.json")
        blob = json.dumps({"identification_id": "LGPD-hash", "name": "Joao"})
        with caplog.at_level(logging.INFO, logger="portal.test.json"):
            logger.info("payload %s", blob)
        assert "LGPD-hash" not in caplog.text
        assert "Joao" in caplog.text


class TestUvicornAccessLogCompatibility:
    def test_access_records_keep_args_for_uvicorn_formatter(self):
        install_masking()
        logger = logging.getLogger("uvicorn.access")
        record = logger.makeRecord(
            "uvicorn.access",
            logging.INFO,
            __file__,
            0,
            '%s - "%s %s HTTP/%s" %d',
            (("127.0.0.1", 1234), "GET", "/api/professors", "1.1", 200),
            None,
        )
        formatted = AccessFormatter().format(record)
        assert '"GET /api/professors HTTP/1.1" 200' in formatted
