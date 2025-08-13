"""
Email processing utilities for handling Microsoft Graph email data.
"""

import re
import uuid
import base64
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from src.services.storage.gcs_manager import gcs_manager
from src.services.communication.email_service import email_service
from src.utils.file_utils import create_temp_filename, clean_filename
from src.database.database import get_db_session
from src.database import crud
from src.core.constants import APIEndpoints

class EmailProcessor:
    """Handles email processing operations."""
    
    def __init__(self):
        self.executor = None  # Can be set if needed for thread pool operations
    
    def generate_business_key(self, email_data: Dict[str, Any]) -> str:
        """Generate a business key from email data for content-based deduplication"""
        if not email_data:
            return ""
        
        internet_message_id = email_data.get("internetMessageId", "")
        subject = email_data.get("subject", "")
        sender = email_data.get("from_email", "")
        received_time = email_data.get("receivedDateTime", "")
        attachment_count = len(email_data.get("attachments", []))
        
        business_key = f"{internet_message_id}|{subject}|{sender}|{received_time}|{attachment_count}"
        return business_key
    
    async def check_duplicate_quotation(self, email_id: str) -> bool:
        """Check if quotation already exists for this email"""
        try:
            loop = asyncio.get_event_loop()
            
            def check_duplicate():
                try:
                    db = get_db_session()
                    existing = crud.get_quotation_by_email_id(db, email_id)
                    db.close()
                    return existing is not None
                except Exception as e:
                    print(f"Error checking duplicate quotation: {e}")
                    return False
            
            return await loop.run_in_executor(None, check_duplicate)
        except Exception as e:
            print(f"Error in duplicate check: {e}")
            return False
    
    async def get_email_details(self, resource: str, access_token: str) -> Optional[Dict[str, Any]]:
        """Get email details from Microsoft Graph API"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{APIEndpoints.MS_GRAPH_BASE}/{resource}", headers=headers) as response:
                    if response.status != 200:
                        print(f"Failed to fetch email: {response.status}")
                        return None
                    
                    email = await response.json()
            
            message_id = resource.split("/")[-1] if "/" in resource else "unknown"
            print(f"📨 Fetching email details for: {message_id[:8]}...")
            
            # Check for duplicate processing
            if await self.check_duplicate_quotation(message_id):
                print(f"⚠️ Email {message_id[:8]} already processed, skipping...")
                return None
            
            email_id = email.get("id", str(uuid.uuid4()))
            sender_email = email["from"]["emailAddress"]["address"]
            subject = email.get("subject", "")
            original_sender_email = ""
            
            # Check for forwarded emails
            if subject.lower().startswith(("fw:", "fwd:")):
                body_content = email["body"]["content"]
                from_matches = re.findall(r'From:.*?&lt;([^&]+)&gt;', body_content)
                if from_matches:
                    original_sender_email = from_matches[-1]
                    print(f"📧 Detected forwarded email, original sender: {original_sender_email}")
            
            result = {
                "from_email": sender_email,
                "original_sender_email": original_sender_email,
                "to": [r["emailAddress"]["address"] for r in email["toRecipients"]],
                "subject": subject,
                "body": email["body"]["content"],
                "attachments": [],
                "email_id": email_id,
                "internetMessageId": email.get("internetMessageId", ""),
                "receivedDateTime": email.get("receivedDateTime", "")
            }
            
            # Process attachments if any
            if not email.get("hasAttachments", False):
                await email_service.send_no_attachments_email(sender_email)
                return None
            
            attachments = await self.fetch_attachments(resource, access_token)
            if not attachments or len(attachments) < 3:
                await email_service.send_insufficient_attachments_email(sender_email)
                return None
            
            gcs_folder = f"quote/{sender_email}-{original_sender_email}/" if original_sender_email else f"quote/{sender_email}/"
            
            # Process attachments
            for att in attachments:
                if "contentBytes" in att:
                    att_result = await self.process_attachment(att, gcs_folder)
                    if att_result:
                        result["attachments"].append(att_result)
            
            return result
            
        except Exception as e:
            print(f"Error getting email details: {e}")
            return None
    
    async def fetch_attachments(self, resource: str, access_token: str) -> List[Dict[str, Any]]:
        """Fetch email attachments"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{APIEndpoints.MS_GRAPH_BASE}/{resource}/attachments", headers=headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch attachments: {response.status}")
                    return []
                
                data = await response.json()
                return data.get("value", [])
    
    async def process_attachment(self, att: Dict[str, Any], gcs_folder: str) -> Optional[Dict[str, Any]]:
        """Process a single attachment"""
        try:
            filename = clean_filename(att["name"])
            
            temp_id = str(uuid.uuid4())[:8]
            temp_path = f"./temp_attachments/{create_temp_filename('att', f'_{filename}')}"
            
            # Save file
            with open(temp_path, "wb") as f:
                f.write(base64.b64decode(att["contentBytes"]))
            
            # Upload to GCS
            gcs_path = f"{gcs_folder}{filename}"
            gcs_url = await gcs_manager.upload_file(temp_path, gcs_path)
            
            if gcs_url:
                try:
                    import os
                    os.remove(temp_path)
                except:
                    pass
                
                return {
                    "filename": filename,
                    "gcs_path": gcs_path,
                    "gcs_url": gcs_url,
                    "contentType": att.get("contentType", "application/octet-stream"),
                }
            return None
            
        except Exception as e:
            print(f"Error processing attachment: {e}")
            return None