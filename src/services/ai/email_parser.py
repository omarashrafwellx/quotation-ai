"""
Email content parsing using AI.
Refactored from get_data_from_email.py
"""

import google.generativeai as genai
import json
from src.core.config import settings
from src.core.constants import BROKER_NAMES, RELATIONSHIP_MANAGERS, Defaults
from src.core.exceptions import AIServiceError

class EmailParser:
    """Parses email content to extract broker and relationship manager information."""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    
    def extract_structured_data_from_email(self, email_content: str) -> dict:
        """
        Extract broker and relationship manager information from email content.
        
        Args:
            email_content: Combined email content (headers + body)
            
        Returns:
            Dictionary containing broker_name and relationship_manager
        """
        try:
            # Create broker names list for the prompt
            broker_names_text = '\n'.join([f'"{name}"' for name in BROKER_NAMES])
            
            prompt = [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"""
You will be given the email content. You need to extract the below things from the email and return a JSON of these values.

* `policy_start_date`**
    * **Rule:** Find the date mentioned for the policy start. This might be labeled as "Policy Start Date", "Effective Date", "Inception Date", etc.
    * **Format:** Convert the extracted date into `YYYY-MM-DD` format, For Example: 2025-10-24.
    * **Default:** If no date is mentioned, the value must be `null`.

* The `relationship_manager` value MUST only be from these available optons (case incensitive): "Hishaam", "Shikha", "Sabina", "Sujith"
    * If any relationship manager name provided in the email closely matches with any one of the options listed above, select from only the given exact values. 
    * If the relationship manager name mentioned in the email does not match with any of the names mentioned in the options above, select the default option "Sabina"

* The `broker_name` value MUST only be from these available optons (case incensitive) given below.
    * If any broker name provided in the email closely matches with any one of the options listed below, select from only the given exact values. 
    * If the broker name mentioned in the email does not match with any of the names mentioned in the options above, select the default option "AES"

Available values for broker name:
{broker_names_text}

* `broker_name`: This is usally the name of the company who sent the email. You can check the email as well. For example the sender email may have a company information after '@' which may closely match with the options available for the broker name
* `broker_contact_person`: The name of the person who is reaching out on behalf of the company. This is usually a sender name. 
    * **Default:** If not mentioned, the value must be ``.
* `relationship_manager`: This is the person name who received the email
* `broker_fee`: If there is mention of the fee which broker takes. It usually is 12.5 percent. But if no information related to broker fee exist, keep it as Null

Only return the JSON directly without any other explanation.
                    
                    

This is the email content:
{email_content}
                            """
                        }
                    ]
                }
            ]
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip().replace("```", "").replace("json", "")
            
            try:
                result = json.loads(response_text)
                
                # Validate and set defaults if needed
                if "broker_name" not in result or not result["broker_name"]:
                    result["broker_name"] = Defaults.BROKER_NAME
                
                if "relationship_manager" not in result or not result["relationship_manager"]:
                    result["relationship_manager"] = Defaults.RELATIONSHIP_MANAGER
                
                if "broker_contact_person" not in result or not result["broker_contact_person"]:
                    result["broker_contact_person"] = "Sabina"  # Default contact person
                # Ensure broker_fee is properly handled
                if "broker_fee" not in result:
                    result["broker_fee"] = None
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"Error parsing AI response as JSON: {e}")
                # Return defaults on parsing error
                return {
                    "broker_name": Defaults.BROKER_NAME,
                    "relationship_manager": Defaults.RELATIONSHIP_MANAGER,
                    "broker_fee": None,
                    "broker_contact_person": None
                }
            
        except Exception as e:
            print(f"Error in email parsing: {e}")
            # Return defaults on any error
            return {
                "broker_name": Defaults.BROKER_NAME,
                "relationship_manager": Defaults.RELATIONSHIP_MANAGER,
                "broker_fee": None,
                "broker_contact_person": None
            }

# Global email parser instance
email_parser = EmailParser()

def extract_structured_data_from_email(email_content: str) -> dict:
    """Convenience function to extract structured data from email."""
    return email_parser.extract_structured_data_from_email(email_content)