"""WP19(d): Sentry wiring — a strict no-op until the DSN exists."""

from __future__ import annotations

from unittest.mock import patch

from backend.main import _init_sentry


class NoDsnSettings:
    environment = "test"


class DsnSettings:
    sentry_dsn = "https://key@o0.ingest.sentry.io/0"
    environment = "test"


def test_noop_without_dsn():
    # Must not even import sentry_sdk — and must not raise.
    with patch("sentry_sdk.init") as mock_init:
        _init_sentry(NoDsnSettings())
    mock_init.assert_not_called()


def test_inits_errors_only_no_pii_with_dsn():
    with patch("sentry_sdk.init") as mock_init:
        _init_sentry(DsnSettings())
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == DsnSettings.sentry_dsn
    assert kwargs["environment"] == "test"
    # The privacy contract: errors only, never PII.
    assert kwargs["traces_sample_rate"] == 0.0
    assert kwargs["send_default_pii"] is False
