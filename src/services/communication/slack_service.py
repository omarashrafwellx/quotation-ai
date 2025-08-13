"""
Slack service for sending notifications and file uploads.
"""

import time
from typing import Optional, Tuple
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from http.client import IncompleteRead
from src.core.config import settings
from src.core.constants import SlackConfig
from src.core.exceptions import EmailProcessingError

class SlackService:
    """Handles Slack operations for notifications and file uploads."""
    
    def __init__(self):
        if not settings.SLACK_API_KEY:
            raise EmailProcessingError("Slack API key not configured")
        self.client = WebClient(token=settings.SLACK_API_KEY)
    
    def get_channel_id(self, channel_name: str) -> Optional[str]:
        """
        Get channel ID by channel name.
        
        Args:
            channel_name: Name of the Slack channel
            
        Returns:
            Channel ID if found, None otherwise
        """
        try:
            result = self.client.conversations_list(types="public_channel", limit=1000)
            for channel in result['channels']:
                if channel['name'] == channel_name:
                    return channel['id']
            return None
        except SlackApiError as e:
            print(f"Error fetching channels: {e.response['error']}")
            return None
    
    def create_channel(self, channel_name: str) -> Optional[str]:
        """
        Create a new Slack channel.
        
        Args:
            channel_name: Name of the channel to create
            
        Returns:
            Channel ID if created successfully, None otherwise
        """
        try:
            response = self.client.conversations_create(name=channel_name)
            return response['channel']['id']
        except SlackApiError as e:
            if e.response['error'] == 'name_taken':
                print(f"Channel '{channel_name}' already exists.")
                return self.get_channel_id(channel_name)
            else:
                print(f"Error creating channel: {e.response['error']}")
                return None
    
    def send_message(self, channel_id: str, message: str) -> bool:
        """
        Send a text message to a Slack channel.
        
        Args:
            channel_id: Slack channel ID
            message: Message content
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            response = self.client.chat_postMessage(channel=channel_id, text=message)
            print(f"Message sent: {response['ts']}")
            return True
        except SlackApiError as e:
            print(f"Error sending message: {e.response['error']}")
            return False
    
    def send_pdf_with_retry(self, channel_id: str, file_path: str, message: str = "", ts = None,
                           max_retries: int = None, delay: int = None) -> Tuple[bool, str]:
        """
        Send PDF file to Slack channel with retry logic.
        
        Args:
            channel_id: Slack channel ID
            file_path: Path to the PDF file
            message: Optional message to include
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            ts: ts id for replying to the message.
            
        Returns:
            Tuple of (success, message)
        """
        max_retries = max_retries or SlackConfig.MAX_RETRIES
        delay = delay or SlackConfig.RETRY_DELAY
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.files_upload_v2(
                    channel=channel_id,
                    title="Quote PDF",
                    file=file_path,
                    # initial_comment=message,
                    thread_ts=ts,
                )
                result = self.client.chat_postMessage(
                channel=channel_id,
                thread_ts=ts,
                text=message,
                # You could also use a blocks[] array to send richer content
                )
                return True, "PDF uploaded successfully."
            except IncompleteRead as e:
                print(f"⚠️ IncompleteRead: {e}, attempt {attempt+1}/{max_retries+1}")
                if attempt == max_retries:
                    return False, f"Failed after {max_retries+1} attempts due to IncompleteRead"
                time.sleep(delay)
            except SlackApiError as e:
                print(f"Error uploading file: {e.response['error']}")
                return False, e.response['error']
            except Exception as e:
                print(f"Unexpected error uploading file: {e}")
                return False, str(e)
        
        return False, "Failed after all retry attempts"
    
    def send_pdf(self, channel_id: str, file_path: str, message: str = "") -> Tuple[bool, str]:
        """
        Send PDF file to Slack channel (single attempt).
        
        Args:
            channel_id: Slack channel ID
            file_path: Path to the PDF file
            message: Optional message to include
            
        Returns:
            Tuple of (success, message)
        """
        try:
            response = self.client.files_upload_v2(
                channel=channel_id,
                title="Quote PDF",
                file=file_path,
                initial_comment=message,
            )
            
            return True, "PDF uploaded successfully."
        except SlackApiError as e:
            print(f"Error uploading file: {e.response['error']}")
            return False, e.response['error']
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False, str(e)
    
    def send_quote_notification(self, pdf_path: str, message: str, 
                              channel_name: str = None) -> Tuple[bool, str]:
        """
        Send quote notification to Slack with PDF attachment.
        
        Args:
            pdf_path: Path to the PDF file
            message: Message content
            channel_name: Slack channel name (defaults to quote-notifications)
            
        Returns:
            Tuple of (success, response_message)
        """
        channel_name = channel_name or SlackConfig.DEFAULT_CHANNEL
        
        # Get or create channel
        channel_id = self.get_channel_id(channel_name)
        if not channel_id:
            print(f"Channel '{channel_name}' not found. Creating...")
            channel_id = self.create_channel(channel_name)
        
        if not channel_id:
            return False, f"Failed to get or create channel '{channel_name}'"
        
        # Send PDF with retry logic
        success, response = self.send_pdf_with_retry(channel_id, pdf_path, message)
        
        if success:
            return True, f"PDF uploaded successfully to '{channel_name}'"
        else:
            return False, f"Failed to upload PDF to '{channel_name}': {response}"
        
    def reply_to_the_message(self, channel_name, text, ts=None):
        try:
            # Call the chat.postMessage method using the WebClient
            # The client passes the token you included in initialization  
            channel_id = self.get_channel_id(channel_name)
            if not channel_id:
                print(f"Channel '{channel_name}' not found. Creating...")
                channel_id = self.create_channel(channel_name)  
            result = self.client.chat_postMessage(
                channel=channel_id,
                thread_ts=ts,
                text=text,
                # You could also use a blocks[] array to send richer content
            )

            # print(result)
            return result

        except SlackApiError as e:
            print(f"Error: {e}")

# Global Slack service instance
slack_service = SlackService() if settings.SLACK_API_KEY else None

# Convenience functions for backward compatibility
def get_channel_id(channel_name: str) -> Optional[str]:
    """Convenience function to get channel ID."""
    if not slack_service:
        return None
    return slack_service.get_channel_id(channel_name)

def create_channel(channel_name: str) -> Optional[str]:
    """Convenience function to create channel."""
    if not slack_service:
        return None
    return slack_service.create_channel(channel_name)

def send_pdf(channel_id: str, file_path: str, message: str = "") -> Tuple[bool, str]:
    """Convenience function to send PDF."""
    if not slack_service:
        return False, "Slack service not configured"
    return slack_service.send_pdf(channel_id, file_path, message)

def send_message(channel_id: str, message: str) -> bool:
    """Convenience function to send message."""
    if not slack_service:
        return False
    return slack_service.send_message(channel_id, message)