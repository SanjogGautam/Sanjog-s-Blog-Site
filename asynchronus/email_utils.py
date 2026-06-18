from email.message import EmailMessage
import aiosmtplib
from fastapi.templating import Jinja2Templates
from config import settings

templates = Jinja2Templates(directory="templates")


async def send_email(
    email_to: str,
    subject: str,
    plain_text: str,
    html_content: str | None,
) -> None:
    print(f"[DEBUG] Attempting to send email to {email_to}")  # ← add this
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = email_to
    message["Subject"] = subject

    message.set_content(plain_text)
    if html_content:
        message.add_alternative(html_content, subtype="html")
    await aiosmtplib.send(
    message,
    hostname=settings.mail_server,
    port=settings.mail_port,
    username=settings.mail_username,
    password=settings.mail_password.get_secret_value(),
    start_tls=True,        
    timeout=30,            
)


async def send_password_reset_email(email_to: str, username: str, token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    template = templates.env.get_template("email/password-reset.html")
    html_content = template.render(reset_url=reset_url, username=username)
    plain_text = f"""Hi {username},
You requested to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in 1 hour.
If you didn't request this, you can safely ignore this email.

Best regards,
The Sanjog's Blog Team
"""
    await send_email(
        email_to=email_to,
        subject="Reset your password - Sanjog's Blog",   
        plain_text=plain_text,
        html_content=html_content,
    )