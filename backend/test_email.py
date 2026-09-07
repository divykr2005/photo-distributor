import os
from dotenv import load_dotenv

# Load env variables
load_dotenv(".env")
load_dotenv("../.env") # Just in case it's reading the root

from services.notifier.adapters import SmtpNotifier
from services.notifier.templates import render_email_template

def run_test():
    notifier = SmtpNotifier()
    
    frontend_url = str(settings.FRONTEND_URL).rstrip('/')
    subject, text_body, html_body = render_email_template(
        guest_name="Chanchala",
        event_title="Deep Obsidian AI Testing Event",
        photo_count=5,
        magic_link=f"{frontend_url}/g/test-magic-link",
        opt_out_link=f"{frontend_url}/opt-out/test",
    )
    
    print("Sending test email to chanchalav480@gmail.com...")
    result = notifier.send(
        recipient="chanchalav480@gmail.com",
        subject=subject,
        body_text=text_body,
        body_html=html_body
    )
    
    if result.success:
        print(f"Success! Sent via: {result.provider}")
        print(f"Message ID: {result.provider_message_id}")
    else:
        print(f"Failed! Error: {result.error}")

if __name__ == "__main__":
    run_test()
