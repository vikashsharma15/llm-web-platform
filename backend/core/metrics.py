import logging
from core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


class _Metrics:
    """
    Production metrics — dual mode:
        METRICS_ENABLED=True  → Prometheus counters (scrape via /metrics)
        METRICS_ENABLED=False → structured log lines only (dev / CI)

    Prometheus setup:
        pip install prometheus-client
        In main.py: mount prometheus_client.make_asgi_app() at /metrics
        Prometheus scrapes /metrics → Grafana dashboards read from Prometheus

    Counters exposed:
        auth_login_attempts_total   labels=[identifier_type: email|ip]
        auth_login_failures_total   labels=[identifier_type: email|ip]
        auth_account_locks_total
        auth_token_blacklist_total
        auth_otp_sent_total
        auth_otp_failed_total       labels=[reason: expired|invalid|max_attempts]
    """

    def __init__(self) -> None:
        self._ok = False   # True only if prometheus_client loaded successfully

        if not settings.METRICS_ENABLED:
            logger.info("Metrics disabled — structured logging only")
            return

        try:
            from prometheus_client import Counter

            self._login_attempts = Counter(
                "auth_login_attempts_total",
                "Total login attempts (all outcomes)",
                ["identifier_type"],
            )
            self._login_failures = Counter(
                "auth_login_failures_total",
                "Total failed login attempts",
                ["identifier_type"],
            )
            self._account_locks = Counter(
                "auth_account_locks_total",
                "Total account lockouts triggered",
            )
            self._token_blacklisted = Counter(
                "auth_token_blacklist_total",
                "Total tokens blacklisted (logout + rotation)",
            )
            self._otp_sent = Counter(
                "auth_otp_sent_total",
                "Total OTPs sent via email",
            )
            self._otp_failed = Counter(
                "auth_otp_failed_total",
                "Total OTP verification failures",
                ["reason"],   # expired | invalid | max_attempts
            )

            self._ok = True
            logger.info("Prometheus metrics initialized")

        except ImportError:
            logger.warning(
                "prometheus_client not installed — metrics logging only. "
                "Fix: pip install prometheus-client"
            )

    # ─── Public Counters ──────────────────────────────────────────────────────

    def login_attempt(self, identifier: str) -> None:
        """Call on every login attempt regardless of outcome."""
        id_type = "email" if "@" in identifier else "ip"
        if self._ok:
            self._login_attempts.labels(identifier_type=id_type).inc()
        logger.info(f"METRIC login_attempt type={id_type}")

    def login_failure(self, identifier: str) -> None:
        """Call on wrong password / unknown email."""
        id_type = "email" if "@" in identifier else "ip"
        if self._ok:
            self._login_failures.labels(identifier_type=id_type).inc()
        logger.warning(f"METRIC login_failure type={id_type}")

    def account_locked(self, email: str) -> None:
        """Call when account lockout is triggered."""
        if self._ok:
            self._account_locks.inc()
        logger.warning(f"METRIC account_locked email={email}")

    def token_blacklisted(self) -> None:
        """Call when any token is blacklisted (logout or rotation)."""
        if self._ok:
            self._token_blacklisted.inc()
        logger.info("METRIC token_blacklisted")

    def otp_sent(self) -> None:
        """Call after OTP email is sent successfully."""
        if self._ok:
            self._otp_sent.inc()
        logger.info("METRIC otp_sent")

    def otp_failed(self, reason: str) -> None:
        """
        Call on OTP verification failure.
        reason must be: 'expired' | 'invalid' | 'max_attempts'
        """
        if self._ok:
            self._otp_failed.labels(reason=reason).inc()
        logger.warning(f"METRIC otp_failed reason={reason}")


# Module-level singleton — single instance across entire app
# Usage: from core.metrics import metrics
metrics = _Metrics()