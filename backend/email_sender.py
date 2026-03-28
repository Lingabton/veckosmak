"""Email sending for magic links using Resend."""

import logging

from backend.config import get_settings

logger = logging.getLogger(__name__)


async def send_magic_link_email(email: str, token: str) -> bool:
    """Send a magic link email. Returns True if sent, False if dev mode (logged only)."""
    settings = get_settings()
    login_url = f"{settings.frontend_url}#auth={token}"

    if not settings.resend_api_key:
        logger.info(f"[DEV] Magic link for {email}: {login_url}")
        return False

    import resend

    resend.api_key = settings.resend_api_key

    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h1 style="color: #2D7D46; font-size: 24px; margin-bottom: 8px;">veckosmak</h1>
        <p style="color: #666; font-size: 14px; margin-bottom: 24px;">Logga in med din e-post</p>
        <a href="{login_url}"
           style="display: inline-block; background: #2D7D46; color: white; text-decoration: none;
                  padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
            Logga in
        </a>
        <p style="color: #999; font-size: 12px; margin-top: 24px;">
            Länken är giltig i 15 minuter. Om du inte begärde detta kan du ignorera mejlet.
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": email,
            "subject": "Logga in på Veckosmak",
            "html": html,
        })
        logger.info(f"Magic link email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        # Fall back to logging
        logger.info(f"[FALLBACK] Magic link for {email}: {login_url}")
        return False
