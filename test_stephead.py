from stagehand.sync import Stagehand
from dotenv import load_dotenv
import os
import time
import logging
import requests
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("PROJECT_ID")
MODEL_API_KEY = os.getenv("MODEL_API_KEY") 
STAGEHAND_SERVER_URL = os.getenv("STAGEHAND_SERVER_URL", "http://localhost:3000")

# Validate required credentials
if not MODEL_API_KEY:
    raise ValueError("MODEL_API_KEY environment variable is required")
if not BROWSERBASE_API_KEY:
    raise ValueError("BROWSERBASE_API_KEY environment variable is required")
if not BROWSERBASE_PROJECT_ID:
    raise ValueError("PROJECT_ID environment variable is required")

CENSUS_FILE_PATH = "files/excel/MemberCensusDataTemplate_standardized.xls"

# Form data
QUOTE_DATA = {
    "client_name": "essam",
    "policy_start_date": "2025-04-08",
    "broker_name": "al raha",
    "broker_contact": "John Doe",
    "relationship_manager": "Sabina",
    "adjustments_discount": "10",
    "discount_comment": "Special corporate discount",
    "brokerage_fees": "10.50",
    "healthx": "9.50",
    "tpa": "7",
    "insurer": "7"
}

def execute_task(session_id, task):
    """Execute a task using the server's execute endpoint"""
    url = f"{STAGEHAND_SERVER_URL}/sessions/{session_id}/execute"
    headers = {'Content-Type': 'application/json'}
    data = {'task': task}
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    if data['type'] == 'system':
                        if data['data']['status'] == 'finished':
                            return data['data'].get('result', True)
                        elif data['data']['status'] == 'error':
                            raise Exception(data['data']['error'])
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        return False

def main():
    """Main function to run the entire process with Stagehand"""
    session_id = None
    try:
        # Start session
        logger.info("Starting Stagehand session...")
        headers = {
            'x-bb-api-key': BROWSERBASE_API_KEY,
            'x-bb-project-id': BROWSERBASE_PROJECT_ID,
            'x-model-api-key': MODEL_API_KEY
        }
        
        response = requests.post(f"{STAGEHAND_SERVER_URL}/sessions/start", headers=headers)
        response.raise_for_status()
        session_data = response.json()
        session_id = session_data['data']['sessionId']
        logger.info(f"Session started: {session_id}")
        
        # Navigate to login page
        logger.info("Navigating to login page...")
        requests.post(f"{STAGEHAND_SERVER_URL}/sessions/{session_id}/navigate", 
                     json={'url': 'https://docs.google.com/forms/d/e/1FAIpQLSdIbWu5keJxnIp4ZGmnGZNlkEd7cYnz_jBRtkE-8xLOoDo5Mw/viewform'})
        time.sleep(3)
        
        # Login
        logger.info("Logging in...")
        execute_task(session_id, f"You need to locate the input field where 'Enter your email' is written and fill this field with this value `{EMAIL}`, then navigate to the 'Enter your password' input field and type this `{PASSWORD}`. Then left click on the 'Login' button")
        time.sleep(5)
        
        # Navigate to New Quote
        logger.info("Navigating to New Quote...")
        execute_task(session_id, "Click on the HEALTHX PLAN menu item, then click on New Quote")
        time.sleep(3)
        
        # Fill form
        logger.info("Filling quote form...")
        execute_task(session_id, f"""
            Fill out the quote form with the following information:
            - Client Name: {QUOTE_DATA['client_name']}
            - Policy Start Date: {QUOTE_DATA['policy_start_date']}
            - Broker Name: {QUOTE_DATA['broker_name']}
            - Relationship Manager: {QUOTE_DATA['relationship_manager']}
            - Adjustments Discount: {QUOTE_DATA['adjustments_discount']}
            - Discount Comment: {QUOTE_DATA['discount_comment']}
            - Brokerage Fees: {QUOTE_DATA['brokerage_fees']}
            - HealthX: {QUOTE_DATA['healthx']}
            - TPA: {QUOTE_DATA['tpa']}
            - Insurer: {QUOTE_DATA['insurer']}
            
            For dropdown fields, click on them and select the appropriate option.
        """)
        time.sleep(5)
        
        # Upload file
        logger.info("Uploading census file...")
        execute_task(session_id, "Click the Upload Census button and upload a file")
        time.sleep(5)
        
        # Handle modals
        logger.info("Handling modals...")
        execute_task(session_id, "Click OK on any modal dialogs that appear")
        time.sleep(3)
        
        logger.info("Process completed successfully!")
    
    except Exception as e:
        logger.error(f"Error during execution: {e}")
    
    finally:
        # End session
        if session_id:
            try:
                logger.info("Ending session...")
                requests.post(f"{STAGEHAND_SERVER_URL}/sessions/{session_id}/end")
                logger.info("Session ended successfully")
            except Exception as e:
                logger.error(f"Error ending session: {e}")

if __name__ == "__main__":
    main()