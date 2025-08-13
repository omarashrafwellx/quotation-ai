"""
Microsoft Graph API token management.
Handles token refresh and authentication for Microsoft Graph API.
"""

import json
import requests
import time
from typing import Optional, Dict, Any
from src.core.config import settings
from src.core.exceptions import AuthenticationError

class TokenManager:
    """Manages Microsoft Graph API tokens."""
    
    def __init__(self):
        self.token_file = settings.TOKEN_FILE
        self.tenant_id = settings.TENANT_ID
        self.client_id = settings.CLIENT_ID
        self.client_secret = settings.CLIENT_SECRET
    
    def save_tokens(self, data: Dict[str, Any]) -> None:
        """Save tokens to file."""
        try:
            with open(self.token_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            raise AuthenticationError(f"Failed to save tokens: {e}")
    
    def load_tokens(self) -> Optional[Dict[str, Any]]:
        """Load tokens from file."""
        try:
            with open(self.token_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            raise AuthenticationError(f"Failed to load tokens: {e}")
    
    def refresh_access_token(self) -> str:
        """Refresh the access token using the refresh token."""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        tokens = self.load_tokens()
        
        if not tokens or "refresh_token" not in tokens:
            raise AuthenticationError("No refresh token available")
        
        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "scope": "Mail.Read offline_access"
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            new_tokens = response.json()
            self.save_tokens(new_tokens)
            return new_tokens["access_token"]
        except requests.RequestException as e:
            raise AuthenticationError(f"Failed to refresh token: {e}")
    
    def device_code_flow(self) -> None:
        """Perform device code flow for initial authentication."""
        device_code_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/devicecode"
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # Step 1: Get device code
        data = {
            "client_id": self.client_id,
            "scope": "Mail.Read Mail.ReadWrite offline_access"
        }
        
        try:
            response = requests.post(device_code_url, data=data)
            response.raise_for_status()
            result = response.json()
            
            print(f"\n🧑‍💻 Go to {result['verification_uri']} and enter the code: {result['user_code']}")
            print("Waiting for you to authenticate...\n")
            
            # Step 2: Poll for access token
            while True:
                time.sleep(result["interval"])
                poll_data = {
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": self.client_id,
                    "device_code": result["device_code"],
                }
                
                token_response = requests.post(token_url, data=poll_data)
                
                if token_response.status_code == 200:
                    tokens = token_response.json()
                    self.save_tokens(tokens)
                    print("✅ Auth complete. Tokens saved.")
                    break
                elif token_response.status_code == 400:
                    error_data = token_response.json()
                    if error_data.get("error") == "authorization_pending":
                        continue
                    else:
                        raise AuthenticationError(f"Authentication error: {error_data}")
                else:
                    raise AuthenticationError(f"Authentication failed: {token_response.text}")
                    
        except requests.RequestException as e:
            raise AuthenticationError(f"Device code flow failed: {e}")

# Global token manager instance
token_manager = TokenManager()

def refresh_access_token() -> str:
    """Convenience function to refresh access token."""
    return token_manager.refresh_access_token()