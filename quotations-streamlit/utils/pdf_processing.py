import google.generativeai as genai
import json
import io
import time
import sys
import os
# Add the grandparent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Now import from get_json_from_TOB.py
from get_json_from_TOB import format_price, STANDARDIZE_PRICES_FIELDS, BENEFIT_DETAILS_DATA, data

def extract_tob_data(file, api_key):
    """
    Extract structured data from a Table of Benefits PDF using Gemini.
    
    Args:
        file: Streamlit uploaded PDF file object
        api_key: Gemini API key
        
    Returns:
        dict: Final formatted JSON structure from TOB
    """
    if not api_key:
        raise ValueError("Missing Gemini API key. Please set the GEMINI_API_KEY environment variable.")
    
    # Configure Gemini
    genai.configure(api_key=api_key)

    # Step 1: Upload PDF to Gemini
    file_bytes = file.getvalue()
    uploaded_file = genai.upload_file(io.BytesIO(file_bytes), mime_type="application/pdf")

    # Wait for the file to become active
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(1)
        uploaded_file = genai.get_file(uploaded_file.name)
        print(f"Waiting for file to become active. Current state: {uploaded_file.state.name}")

    if uploaded_file.state.name != "ACTIVE":
        raise Exception(f"File processing failed with state: {uploaded_file.state.name}")
    
    print(f"File is now active: {uploaded_file.name}")

    # Step 2: Extract Markdown from PDF
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    markdown_prompt = [
        {
            "role": "user",
            "parts": [
                {"text": "This is the benefits table. Carefully read the content of the table and return me a markdown for it. Do not miss anything. Include all the details. Do not miss the complete company name which could be written in the text or in the logo. Do not include any introductory or explanatory text. The markdown should be the only output."},
                {"file_data": {"file_uri": uploaded_file.uri, "mime_type": "application/pdf"}}
            ]
        }
    ]
    markdown_response = model.generate_content(markdown_prompt)
    tob_markdown = markdown_response.text.strip().replace("```", "").replace("markdown", "")

    # Step 3: Extract JSON from Markdown
    json_prompt = [
        {
            "role": "user",
            "parts": [
                {
                    "text": f"""
                    {data}
                    Now process the TOB below and return only the populated JSON. Do not return any text or explanations. The JSON should match exactly the format of the given template. 
                    ### TOB (Markdown):
                    {tob_markdown}
                    ### JSON Template:
                    {BENEFIT_DETAILS_DATA}
                    """
                }
            ]
        }
    ]
    json_response = model.generate_content(json_prompt)
    response_text = json_response.text.strip().replace("```", "").replace("json", "")
    raw_json = json.loads(response_text)

    # Step 4: Post-process price formatting
    for field, rules in STANDARDIZE_PRICES_FIELDS.items():
        if field in raw_json:
            value = raw_json[field]
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                raw_json[field] = format_price(str(value), prefix=rules["prefix"], comma=rules["comma"])

    return raw_json


def extract_company_from_trade_license(file, api_key):
    """
    Extract company name from trade license PDF.
    
    Args:
        file: Streamlit uploaded PDF file
        api_key: Gemini API key
        
    Returns:
        dict: Dictionary containing the company name
    """
    if not api_key:
        raise ValueError("Missing Gemini API key. Please set the GEMINI_API_KEY environment variable.")
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Get file bytes
    file_bytes = file.getvalue()
    
    try:
        # Upload the file to Gemini
        uploaded_file = genai.upload_file(io.BytesIO(file_bytes), mime_type="application/pdf")
        
        # Wait for the file to become active
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)
            print(f"Waiting for file to become active. Current state: {uploaded_file.state.name}")
        
        if uploaded_file.state.name != "ACTIVE":
            raise Exception(f"File processing failed with state: {uploaded_file.state.name}")
        
        # Initialize the Gemini model
        model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
        
        # Define the prompt for data extraction
        prompt = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "This is a trade license PDF. Carefully read the content and extract the company name whose trade license is given. "
                             "Just directly return the company name as JSON without any extra explanation.\n\n"
                             "Example JSON format:\n"
                             "{\n"
                             "    \"company_name\": \"Actual Company Name\"\n"
                             "}"
                             
                             
                             },
                    {"file_data": {"file_uri": uploaded_file.uri, "mime_type": "application/pdf"}}
                ]
            }
        ]
        
        # Generate the response
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up the response and parse JSON
        json_str = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
        
    except Exception as e:
        raise Exception(f"Error extracting company name from PDF: {str(e)}")