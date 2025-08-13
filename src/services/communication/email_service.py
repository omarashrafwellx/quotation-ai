"""
Email service for sending notifications and PDF attachments.
"""

import requests
import base64
import os
from typing import Optional
from src.services.auth.token_manager import refresh_access_token
from src.core.constants import EmailTemplates
from src.core.exceptions import EmailProcessingError

class EmailService:
    """Handles email operations using Microsoft Graph API."""
    
    def __init__(self):
        self.graph_api_base = "https://graph.microsoft.com/v1.0"
    
    def _get_headers(self) -> dict:
        """Get authorization headers for API requests."""
        try:
            access_token = refresh_access_token()
            return {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            raise EmailProcessingError(f"Failed to get access token: {e}")
    
    def send_text_email(self, to_email: str, subject: str, body_text: str) -> bool:
        """
        Send a text email without attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Email body content
            
        Returns:
            True if email sent successfully, False otherwise
        """
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body_text
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ],
            },
            "saveToSentItems": "true"
        }
        
        try:
            headers = self._get_headers()
            response = requests.post(
                f"{self.graph_api_base}/me/sendMail",
                headers=headers,
                json=message
            )
            
            if response.status_code == 202:
                print(f"✅ Text email sent to {to_email}")
                return True
            else:
                print(f"❌ Failed to send text email: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending text email: {e}")
            return False
    
    def send_pdf_email(self, to_email: str, subject: str, body_text: str, pdf_path: str) -> bool:
        """
        Send an email with PDF attachment.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Email body content
            pdf_path: Path to PDF file to attach
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found: {pdf_path}")
            return False
        
        try:
            # Read and encode the PDF
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            encoded_pdf = base64.b64encode(pdf_data).decode("utf-8")
            
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": body_text
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_email
                            }
                        }
                    ],
                    "attachments": [
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": os.path.basename(pdf_path),
                            "contentType": "application/pdf",
                            "contentBytes": encoded_pdf
                        }
                    ]
                },
                "saveToSentItems": "true"
            }
            
            headers = self._get_headers()
            response = requests.post(
                f"{self.graph_api_base}/me/sendMail",
                headers=headers,
                json=message
            )
            
            if response.status_code == 202:
                print(f"✅ PDF email sent to {to_email}")
                return True
            else:
                print(f"❌ Failed to send PDF email: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending PDF email: {e}")
            return False
    
    def send_no_attachments_email(self, sender_email: str) -> bool:
        """Send email notification for missing attachments."""
        return self.send_text_email(
            to_email=sender_email,
            subject=EmailTemplates.NO_ATTACHMENTS_SUBJECT,
            body_text=EmailTemplates.NO_ATTACHMENTS_BODY.format(sender=sender_email)
        )
    
    def send_insufficient_attachments_email(self, sender_email: str) -> bool:
        """Send email notification for insufficient attachments."""
        return self.send_text_email(
            to_email=sender_email,
            subject=EmailTemplates.INSUFFICIENT_ATTACHMENTS_SUBJECT,
            body_text=EmailTemplates.INSUFFICIENT_ATTACHMENTS_BODY.format(sender=sender_email)
        )
    
    def send_missing_census_email(self, sender_email: str) -> bool:
        """Send email notification for missing census file."""
        return self.send_text_email(
            to_email=sender_email,
            subject=EmailTemplates.MISSING_CENSUS_SUBJECT,
            body_text=EmailTemplates.MISSING_CENSUS_BODY.format(sender=sender_email)
        )
    
    def send_category_mismatch_email(self, sender_email: str, error_message: str) -> bool:
        """Send email notification for category mismatch."""
        return self.send_text_email(
            to_email=sender_email,
            subject=EmailTemplates.CATEGORY_MISMATCH_SUBJECT,
            body_text=EmailTemplates.CATEGORY_MISMATCH_BODY.format(error_message=error_message)
        )
    
    def send_quote_success_email(self, to_email: str, subject: str, body_text: str, pdf_path: str) -> bool:
        """Send successful quote generation email with PDF."""
        return self.send_pdf_email(to_email, subject, body_text, pdf_path)

# Global email service instance
email_service = EmailService()

# Convenience functions for backward compatibility
def send_text_email(to_email: str, subject: str, body_text: str) -> bool:
    """Convenience function to send text email."""
    return email_service.send_text_email(to_email, subject, body_text)

def send_pdf_email(to_email: str, subject: str, body_text: str, pdf_path: str) -> bool:
    """Convenience function to send PDF email."""
    return email_service.send_pdf_email(to_email, subject, body_text, pdf_path)

def reply_to_email(original_message_id: str, reply_body: str, pdf_path):
    """
    Replies to a specific email using its message ID and includes a simple comment.
    """
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    encoded_pdf = base64.b64encode(pdf_data).decode("utf-8")
    
    access_token = refresh_access_token()
    if not access_token:
        print("❌ Failed to get access token. Cannot send reply.")
        return False

    reply_url = f"https://graph.microsoft.com/v1.0/me/messages/{original_message_id}/reply"

    message = {
        "message": {
            # "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": reply_body
            },
            # "toRecipients": [
            #     {
            #         "emailAddress": {
            #             "address": to_email
            #         }
            #     }
            # ],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": pdf_path.split("/")[-1],
                    "contentType": "application/pdf",
                    "contentBytes": encoded_pdf
                }
            ]
        },
        "saveToSentItems": "true"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"Replying to message ID: {original_message_id}")
        response = requests.post(reply_url, headers=headers, json=message)

        if response.status_code == 202:
            print("✅ Reply sent successfully.")
            return True
        else:
            print(f"❌ Failed to send reply. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ An exception occurred while sending the reply: {e}")
        return False