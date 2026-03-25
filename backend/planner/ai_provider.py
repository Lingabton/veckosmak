"""AI provider abstraction — routes between free (Cloudflare) and premium (Claude)."""

import json
import logging
import re

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)


async def call_ai(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2000,
    use_premium: bool = False,
) -> str:
    """Call AI and return raw text response.

    Tries Cloudflare Workers AI (free) first, falls back to Claude (premium).
    Set use_premium=True to go directly to Claude for complex tasks.
    """
    settings = get_settings()

    # Try Cloudflare Workers AI first (free)
    if settings.cloudflare_api_token and settings.cloudflare_account_id and not use_premium:
        try:
            result = await _call_cloudflare(system_prompt, user_message, max_tokens, settings)
            if result:
                logger.info("AI response from Cloudflare Workers AI (free)")
                return result
        except Exception as e:
            logger.warning(f"Cloudflare Workers AI failed: {e}")

    # Fall back to Claude
    if settings.anthropic_api_key:
        try:
            model = "claude-sonnet-4-20250514" if use_premium else "claude-haiku-4-5-20251001"
            result = await _call_claude(system_prompt, user_message, max_tokens, model, settings)
            if result:
                logger.info(f"AI response from Claude ({model})")
                return result
        except Exception as e:
            logger.warning(f"Claude API failed: {e}")

    logger.error("All AI providers failed")
    return ""


async def _call_cloudflare(
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    settings,
) -> str:
    """Call Cloudflare Workers AI (free tier: 10k req/day)."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/run/@cf/meta/llama-3.1-70b-instruct"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success") and data.get("result", {}).get("response"):
            return data["result"]["response"]

    return ""


async def _call_claude(
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    model: str,
    settings,
) -> str:
    """Call Anthropic Claude API."""
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=30.0,
    )

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


def parse_json_response(text: str) -> dict:
    """Extract JSON from AI response, handling markdown code blocks."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse AI response as JSON: {text[:200]}")
        return {}
