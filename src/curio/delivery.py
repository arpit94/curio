"""Email delivery via the Resend HTTP API."""

import os
from typing import Any

import httpx

RESEND_URL = "https://api.resend.com/emails"


def _dry_run_enabled() -> bool:
    return os.getenv("CURIO_DRY_RUN") == "1"


async def send_digest(
    subject: str, html_body: str, text_body: str
) -> dict[str, Any]:
    """Send the digest via Resend. Honors CURIO_DRY_RUN=1 as a no-op."""
    if _dry_run_enabled():
        return {
            "sent": False,
            "dry_run": True,
            "subject": subject,
            "html_chars": len(html_body),
            "text_chars": len(text_body),
        }

    api_key = os.getenv("RESEND_API_KEY")
    frm = os.getenv("DIGEST_FROM")
    to = os.getenv("DIGEST_TO")
    from_name = os.getenv("DIGEST_FROM_NAME", "Curio")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY must be set in .env")
    if not frm:
        raise RuntimeError(
            "DIGEST_FROM must be set in .env (e.g. curio@arpitagg.me)"
        )
    if not to:
        raise RuntimeError("DIGEST_TO must be set in .env")

    # RFC 5322 "friendly from" — display name + address, so inbox shows
    # "Curio" rather than the raw email prefix.
    from_header = f'"{from_name}" <{frm}>' if from_name else frm

    payload = {
        "from": from_header,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": text_body or "(no plaintext body)",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            RESEND_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    if r.status_code >= 300:
        raise RuntimeError(f"Resend error {r.status_code}: {r.text}")

    data = r.json()
    return {"sent": True, "id": data.get("id"), "from": frm, "to": to, "subject": subject}
