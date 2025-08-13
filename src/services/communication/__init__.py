"""
Communication services for email and Slack notifications.
"""

from .email_service import send_text_email, send_pdf_email
from .slack_service import send_pdf, get_channel_id, create_channel