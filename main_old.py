#!/usr/bin/env python3
"""
Main entry point for the Quotation AI system.
Provides commands to start different services.
"""

import sys
import argparse
import uvicorn
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def start_webhook_server():
    """Start the webhook server."""
    print("🚀 Starting Webhook Server...")
    uvicorn.run(
        "src.api.webhook_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

def start_email_processor():
    """Start the email processing server."""
    print("🚀 Starting Email Processing Server...")
    uvicorn.run(
        "src.api.process_email:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )

def validate_config():
    """Validate system configuration."""
    try:
        from src.core.config import settings
        settings.validate_required_settings()
        print("✅ Configuration validation passed")
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def setup_auth():
    """Setup Microsoft Graph authentication."""
    try:
        from src.services.auth.token_manager import token_manager
        print("🔐 Starting device code flow for authentication...")
        token_manager.device_code_flow()
        print("✅ Authentication setup completed")
        return True
    except Exception as e:
        print(f"❌ Authentication setup failed: {e}")
        return False

def main():
    """Main entry point with command-line interface."""
    parser = argparse.ArgumentParser(description="Quotation AI System")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Webhook server command
    webhook_parser = subparsers.add_parser("webhook", help="Start webhook server")
    
    # Email processor command
    processor_parser = subparsers.add_parser("processor", help="Start email processing server")
    
    # Validation command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    
    # Authentication setup command
    auth_parser = subparsers.add_parser("auth", help="Setup authentication")
    
    # Both servers command
    both_parser = subparsers.add_parser("both", help="Instructions for running both servers")
    
    args = parser.parse_args()
    
    if args.command == "webhook":
        if validate_config():
            start_webhook_server()
        else:
            sys.exit(1)
    
    elif args.command == "processor":
        if validate_config():
            start_email_processor()
        else:
            sys.exit(1)
    
    elif args.command == "validate":
        if validate_config():
            print("✅ All configurations are valid")
        else:
            sys.exit(1)
    
    elif args.command == "auth":
        setup_auth()
    
    elif args.command == "both":
        print("""
🚀 To run both servers, open two terminal windows:

Terminal 1 (Webhook Server):
    python main.py webhook

Terminal 2 (Email Processor):
    python main.py processor

Make sure to also setup ngrok tunnel:
    ngrok http 8000

Then register the webhook subscription using:
    python scripts/setup_subscription.py
        """)
    
    else:
        parser.print_help()
        print("""
Examples:
    python main.py validate      # Validate configuration
    python main.py auth          # Setup authentication
    python main.py webhook       # Start webhook server (port 8000)
    python main.py processor     # Start email processor (port 8001)
    python main.py both          # Show instructions for running both
        """)

if __name__ == "__main__":
    main()