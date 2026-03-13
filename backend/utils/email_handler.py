import smtplib
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from dataclasses import dataclass

from core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


class EmailProvider(str, Enum):
    BREVO    = "brevo"
    SENDGRID = "sendgrid"
    AWS_SES  = "aws_ses"


@dataclass
class SMTPConfig:
    host:     str
    port:     int
    user:     str
    password: str
    provider: EmailProvider


class EmailHandler:
    """
    Production email handler — multi-provider, failover, retry.

    Provider priority (from settings):
        Primary   → Brevo SMTP
        Fallback  → SendGrid SMTP (if configured)

    PHP equivalent: AptemEmail library — same provider abstraction pattern.
    """

    # ─── Provider Configs ─────────────────────────────────────────────────────

    @staticmethod
    def _get_provider_configs() -> list[SMTPConfig]:
        """
        Returns ordered list of providers — tries each on failure.
        Primary first, fallbacks after. All from settings — zero hardcoded.
        PHP equivalent: rand() based host selection in Email.php config.
        """
        configs = []

        # Primary — Brevo
        if settings.SMTP_PASS:
            configs.append(SMTPConfig(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                user=settings.SMTP_USER,
                password=settings.SMTP_PASS,
                provider=EmailProvider.BREVO,
            ))

        # Fallback — SendGrid (optional)
        if getattr(settings, "SENDGRID_SMTP_PASS", None):
            configs.append(SMTPConfig(
                host="smtp.sendgrid.net",
                port=587,
                user="apikey",
                password=settings.SENDGRID_SMTP_PASS,
                provider=EmailProvider.SENDGRID,
            ))

        return configs

    # ─── Core Send ────────────────────────────────────────────────────────────

    @staticmethod
    def _send_via_smtp(config: SMTPConfig, to_email: str, subject: str, html: str) -> None:
        """
        Sends email via SMTP — sync, called in thread pool.
        Raises on failure — caller handles retry/fallback.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        msg["To"]      = to_email

        # Plain text fallback — RFC compliant, avoids spam filters
        plain = "Please use an HTML-capable email client to view this message."
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP(config.host, config.port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
            msg["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"


    @classmethod
    async def _send_with_fallback(
        cls,
        to_email: str,
        subject:  str,
        html:     str,
        retries:  int = 2,
    ) -> bool:
        """
        Tries each provider in order — retries on failure.
        PHP equivalent: rand() load balancing + host failover in Email.php.
        """
        configs = cls._get_provider_configs()

        if not configs:
            logger.error("No email providers configured")
            return False

        for config in configs:
            for attempt in range(1, retries + 1):
                try:
                    # Run blocking SMTP in thread pool — never block event loop
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        cls._send_via_smtp,
                        config, to_email, subject, html,
                    )
                    logger.info(
                        f"Email sent provider={config.provider} "
                        f"to={to_email} attempt={attempt}"
                    )
                    return True

                except Exception as e:
                    logger.warning(
                        f"Email attempt failed provider={config.provider} "
                        f"to={to_email} attempt={attempt}/{retries}: {e}"
                    )
                    if attempt < retries:
                        await asyncio.sleep(1 * attempt)  # backoff: 1s, 2s

            logger.error(f"Provider exhausted provider={config.provider} to={to_email}")

        logger.error(f"All email providers failed to={to_email}")
        return False

    # ─── Public API ───────────────────────────────────────────────────────────

    @classmethod
    async def send_otp(cls, to_email: str, otp: str) -> bool:
        subject = "Your Verification Code"
        html    = cls._otp_template(otp)
        return await cls._send_with_fallback(to_email, subject, html)

    @classmethod
    async def send_welcome(cls, to_email: str, username: str) -> bool:
        subject = f"Welcome to {settings.FROM_NAME}!"
        html    = cls._welcome_template(username)
        return await cls._send_with_fallback(to_email, subject, html)

    @classmethod
    async def send_password_reset(cls, to_email: str, otp: str) -> bool:
        subject = "Password Reset Request"
        html    = cls._password_reset_template(otp)
        return await cls._send_with_fallback(to_email, subject, html)

    # ─── Templates ────────────────────────────────────────────────────────────

    @staticmethod
    def _base_template(content: str) -> str:
        """Base layout — all emails share this wrapper."""
        return f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;
                    padding:32px;border:1px solid #eee;border-radius:8px;color:#333">
            <h2 style="color:#111;margin-bottom:24px">{settings.FROM_NAME}</h2>
            {content}
            <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
            <p style="color:#999;font-size:12px">
                If you didn't request this, ignore this email.
            </p>
        </div>
        """

    @classmethod
    def _otp_template(cls, otp: str) -> str:
        content = f"""
            <p>Your verification code is:</p>
            <div style="font-size:40px;font-weight:bold;letter-spacing:12px;
                        padding:16px 0;color:#111">{otp}</div>
            <p style="color:#666;font-size:13px">
                Valid for <strong>{settings.EMAIL_OTP_EXPIRE_MINUTES} minutes</strong>.
                Do not share this code with anyone.
            </p>
        """
        return cls._base_template(content)

    @classmethod
    def _welcome_template(cls, username: str) -> str:
        content = f"""
            <p>Hi <strong>{username}</strong>,</p>
            <p>Welcome! Your account has been verified successfully.</p>
            <p>You can now log in and start your adventure.</p>
        """
        return cls._base_template(content)

    @classmethod
    def _password_reset_template(cls, otp: str) -> str:
        content = f"""
            <p>You requested a password reset. Use this code:</p>
            <div style="font-size:40px;font-weight:bold;letter-spacing:12px;
                        padding:16px 0;color:#111">{otp}</div>
            <p style="color:#666;font-size:13px">
                Valid for <strong>{settings.EMAIL_OTP_EXPIRE_MINUTES} minutes</strong>.
            </p>
        """
        return cls._base_template(content)