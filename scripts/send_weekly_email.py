"""Send weekly menu email to subscribers.

Usage:
    python scripts/send_weekly_email.py
    python scripts/send_weekly_email.py --dry-run
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiosqlite
from backend.config import get_settings
from backend.db.database import DB_PATH, init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def get_subscribers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute("SELECT email FROM email_signups")
        return [row["email"] async for row in rows]


async def send_email(email, subject, html):
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning(f"No Resend API key — would send to {email}")
        return False

    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.email_from,
            "to": email,
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        logger.error(f"Failed to send to {email}: {e}")
        return False


def build_email_html():
    """Build a simple weekly email with a link to the site."""
    from datetime import datetime
    week = datetime.now().isocalendar()[1]

    return f"""
    <div style="font-family: 'Outfit', Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h1 style="font-size: 24px; color: #0f3d22; margin-bottom: 4px;">veckosmak</h1>
        <p style="color: #8a8a8a; font-size: 14px; margin-top: 0;">Vecka {week}</p>

        <p style="font-size: 16px; color: #1a1a1a; line-height: 1.6;">
            Veckans erbjudanden är uppdaterade! Skapa din veckomeny och se vad du kan spara.
        </p>

        <a href="https://veckosmak.vercel.app"
           style="display: inline-block; background: #d4552a; color: white; padding: 14px 28px;
                  border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px; margin: 16px 0;">
            Skapa veckans meny
        </a>

        <p style="font-size: 13px; color: #8a8a8a; margin-top: 24px;">
            Du får detta mejl för att du registrerade dig på veckosmak.vercel.app.
            <br>Svara på detta mejl om du vill avsluta prenumerationen.
        </p>
    </div>
    """


async def main():
    dry_run = "--dry-run" in sys.argv
    await init_db()

    subscribers = await get_subscribers()
    logger.info(f"Subscribers: {len(subscribers)}")

    if not subscribers:
        logger.info("No subscribers yet")
        return

    subject = "Veckans meny är redo"
    html = build_email_html()

    sent = 0
    for email in subscribers:
        if dry_run:
            logger.info(f"  [DRY RUN] Would send to {email}")
            sent += 1
        else:
            if await send_email(email, subject, html):
                sent += 1

    logger.info(f"Sent: {sent}/{len(subscribers)}")


if __name__ == "__main__":
    asyncio.run(main())
