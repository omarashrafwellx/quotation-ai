"""
Setup Microsoft Graph webhook subscription.
Refactored from create_subscription.py
"""

import sys
import requests
import datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.services.auth.token_manager import refresh_access_token
from src.core.config import settings

def create_subscription(webhook_url: str, expiry_minutes: int = 4230):
    """
    Create a Microsoft Graph webhook subscription.
    
    Args:
        webhook_url: The webhook endpoint URL
        expiry_minutes: Subscription expiry in minutes (default ~3 days)
    """
    try:
        # Get access token
        access_token = refresh_access_token()
        
        # Calculate expiry time
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_minutes)).isoformat() + "Z"
        
        # Subscription payload
        payload = {
            "changeType": "created",
            "notificationUrl": webhook_url,
            "resource": "me/mailFolders('Inbox')/messages",
            "expirationDateTime": expiry,
            "clientState": settings.WEBHOOK_CLIENT_STATE
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Create subscription
        response = requests.post(
            "https://graph.microsoft.com/v1.0/subscriptions", 
            headers=headers, 
            json=payload
        )
        
        if response.status_code == 201:
            subscription_data = response.json()
            print("✅ Subscription created successfully!")
            print(f"   Subscription ID: {subscription_data['id']}")
            print(f"   Webhook URL: {webhook_url}")
            print(f"   Expires: {expiry}")
            return True
        else:
            print(f"❌ Failed to create subscription: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating subscription: {e}")
        return False

def main():
    """Main function to setup webhook subscription."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Microsoft Graph webhook subscription")
    parser.add_argument(
        "--webhook-url", 
        required=True,
        help="Webhook endpoint URL (e.g., https://494c-39-37-153-98.ngrok-free.app/email-sub)"
    )
    parser.add_argument(
        "--expiry-minutes", 
        type=int, 
        default=4230,
        help="Subscription expiry in minutes (default: 4230 ~ 3 days)"
    )
    
    args = parser.parse_args()
    
    print("🔗 Setting up Microsoft Graph webhook subscription...")
    print(f"   Webhook URL: {args.webhook_url}")
    print(f"   Client State: {settings.WEBHOOK_CLIENT_STATE}")
    
    success = create_subscription(args.webhook_url, args.expiry_minutes)
    
    if success:
        print("\n✅ Subscription setup completed!")
        print("\nNext steps:")
        print("1. Keep your webhook server running")
        print("2. Keep ngrok tunnel active")
        print("3. Monitor incoming emails")
    else:
        print("\n❌ Subscription setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()