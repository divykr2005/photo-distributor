from typing import Tuple


def render_email_template(
    guest_name: str,
    event_title: str,
    photo_count: int,
    magic_link: str,
    opt_out_link: str,
) -> Tuple[str, str, str]:
    """
    Render email subject, text body, and HTML body.
    No images attached, no photos inline.
    """
    subject = f"Your photos from {event_title} are ready!"

    text_body = f"""Hi {guest_name},

{photo_count} photo{'s' if photo_count != 1 else ''} featuring you from {event_title} are ready to view and download!

View your photos here:
{magic_link}

This link is private and unique to you. Please do not share it publicly.

---
If you wish to opt out of future notification messages for this event, click here:
{opt_out_link}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Your Photos from {event_title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px 20px; margin: 0;">
    <div style="max-width: 560px; margin: 0 auto; background-color: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155;">
        <h2 style="color: #c084fc; margin-top: 0;">Hi {guest_name} 👋</h2>
        <p style="font-size: 16px; line-height: 1.5; color: #e2e8f0;">
            Great news! We found <strong>{photo_count} photo{'s' if photo_count != 1 else ''}</strong> featuring you from <strong>{event_title}</strong>.
        </p>
        <div style="margin: 32px 0; text-align: center;">
            <a href="{magic_link}" style="background-color: #7c3aed; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 9999px; font-weight: 600; font-size: 16px; display: inline-block;">
                View Your Photos
            </a>
        </div>
        <p style="font-size: 13px; color: #94a3b8; line-height: 1.4;">
            This link is private and unique to you.
        </p>
        <hr style="border: none; border-top: 1px solid #334155; margin: 24px 0;">
        <p style="font-size: 12px; color: #64748b; text-align: center;">
            Don't want to receive these notifications? <a href="{opt_out_link}" style="color: #a855f7;">Opt out here</a>.
        </p>
    </div>
</body>
</html>"""

    return subject, text_body, html_body


def render_text_template(
    guest_name: str,
    event_title: str,
    photo_count: int,
    magic_link: str,
    opt_out_link: str,
) -> str:
    """
    Render plain text message for SMS / WhatsApp / Webhook / Console.
    """
    return (
        f"Hi {guest_name}! We found {photo_count} photo{'s' if photo_count != 1 else ''} "
        f"of you from {event_title}. View & download your photos here: {magic_link}\n"
        f"Opt-out: {opt_out_link}"
    )
