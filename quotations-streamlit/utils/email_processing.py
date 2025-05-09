"""
Module for extracting structured data from email content using Gemini API
"""

import google.generativeai as genai
import os
import json

def extract_structured_data_from_email(email_content, api_key=None):
    """
    Extract structured data from email content using Google's Gemini API
    
    Args:
        email_content (str): The email content to extract data from
        api_key (str, optional): Gemini API key. If None, uses GEMINI_API_KEY from environment
        
    Returns:
        dict: Extracted data in dictionary format
    """
    # Configure API key
    if api_key:
        genai.configure(api_key=api_key)
    else:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Create the model
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    
    # Create prompt
    prompt = [
        {
            "role": "user",
            "parts": [
                {
                    "text": 
                    f"""
                    You will be given the email content. You need to extract the below things from the email and return a JSON of these values.
                    
                    * The `relationship_manager` value MUST only be from these available optons (case incensitive): "Hishaam", "Shikha", "Sabina", "Sujith"
                        * If any relationship manager name provided in the email closely matches with any one of the options listed above, select from only the given exact values. 
                        * If the relationship manager name mentioned in the email does not match with any of the names mentioned in the options above, select the default option "Sabina"
                        * You MUST NOT LEAVE THIS OPTION EMPTY. SELECTING A VALUE IS NECESSARY
                        
                    * The `broker_name` value MUST only be from these available optons (case incensitive) given below.
                        * If any broker name provided in the email closely matches with any one of the options listed below, select from only the given exact values. 
                        * If the broker name mentioned in the email does not match with any of the names mentioned in the options above, select the default option "AES"
                        * You MUST NOT LEAVE THIS OPTION EMPTY. SELECTING A VALUE IS NECESSARY
                    
                    Available values for broker name:
                    "AES"
                    "Al Manarah"
                    "Al Raha"
                    "Al Rahaib"
                    "Al Sayegh"
                    "Al Nabooda Insurance Brokers"
                    "Aon International"
                    "Aon Middle East"
                    "Bayzat"
                    "Beneple"
                    "Burns & Wilcox"
                    Care
                    Compass
                    Crisecure
                    Deinon
                    Direct Sale
                    E-Sanad
                    European
                    Fisco
                    Gargash
                    Howden 
                    Indemnity
                    Interactive
                    Kaizzen Plus
                    Lifecare
                    Lockton
                    Marsh Mclenann
                    Medstar
                    Metropolitan
                    Myrisk Advisors
                    Nasco
                    Nasco Emirates
                    New Sheild
                    Newtech
                    Nexus
                    Omega
                    Pacific Prime
                    Pearl
                    Prominent
                    PWS
                    RMS
                    Seguro
                    UIB
                    Unitrust
                    Wehbe
                    Willis Towers Watson
                    Wellx.ai
                    "Unitrust Insurance Brokers"
                    "Cross Road Insurance Brokers"
                    "Seven Insurance Brokers"
                    QHX-242205
                    "Abu Dhabi Insurance Brokers"
                    Wayyak
                    ds
                    Northern Insurance Brokers L.L.C
                    ADIB
                    Earnest
                    Gulf Oasis
                    JDV
                    Links
                    Noble
                    Northern
                    R2S
                    Seven
                    Viva
                    Wayyak
                    Al Nabooda
                    Capstone
                    CRI
                    Gateway
                    Phillip Middle East
                    Platinum
                    Policy Bazaar
                    YallaCompare
                    Alia
                    Continental
                    Cosmos
                    Cross Roads
                    Emirates International
                    Fenchurch Faris
                    Fidelity
                    Honor
                    Global Eye
                    Greenshield
                    Kaissen Plus
                    Leaders
                    New Shield
                    Pearl
                    Phillip ME
                    Star
                    Wills
                    "Acuma" 
                    "AFIA" 
                    Ascot & Fitch
                    "BMS"
                    "Cedars"
                    "Clover"
                    "Dana"
                    "Doo"
                    "Federal"
                    
                    broker_name: This is usally the name of the company who sent the email. You can check the email as well. For example the sender email may have a company information after '@' which may closely match with the options available for the broker name
                    relationship_manager: This is the person name who received the email
                    broker_fee: If there is mention of the fee which broker takes. It usually is 12.5 percent. But if no information related to broker fee exist, keep it as Null
                        
                    Only return the JSON directly without any other explanation.
                    
                    This is the email content:
                    {email_content}
                        """
                }
            ]
        }
    ]
    
    # Generate response
    response = model.generate_content(prompt)
    
    # Process response
    response_text = response.text.strip()
    
    # Clean up the response to get valid JSON
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        # Parse the JSON response
        extracted_data = json.loads(response_text)
        return extracted_data
    except json.JSONDecodeError as e:
        # Return error information if JSON parsing fails
        return {
            "error": f"Failed to parse JSON response: {str(e)}",
            "raw_response": response_text
        }