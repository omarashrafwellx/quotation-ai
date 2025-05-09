import time
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY =os.getenv("GEMINI_API_KEY") 
genai.configure(api_key=GEMINI_API_KEY)

def extract_structured_data(pdf_path: str):
    # Upload the PDF file
    uploaded_file = genai.upload_file(pdf_path)
    
    # Wait for the file to become active
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(1)
        uploaded_file = genai.get_file(uploaded_file.name)
        print(f"Waiting for file to become active. Current state: {uploaded_file.state.name}")
    
    if uploaded_file.state.name != "ACTIVE":
        raise Exception(f"File processing failed with state: {uploaded_file.state.name}")
    
    print(f"File is now active: {uploaded_file.name}")
    
    # Initialize the Gemini model
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    
    # Define the prompt for data extraction
    prompt = [
        {
            "role": "user",
            "parts": [
                {"text":
                """    
                This is the trade license pdf data. Carefully read the content of the pdf file and return me the company name whose trade license is given. Just directly return the company name as JSON without any extra explanation.
                
                Example json format
                {
                    "company_name":actual_company_name
                }
                 """
                 },
                {"file_data": {"file_uri": uploaded_file.uri, "mime_type": "application/pdf"}}
            ]
        }
    ]
    
    # Generate the response
    response = model.generate_content(prompt)
    response_text = response.text.strip().replace("```","").replace("json","")
    return json.loads(response_text)

# Example usage
if __name__ == "__main__":
    pdf_file_path = "LICENSE 2025.pdf" 
    structured_data = extract_structured_data(pdf_file_path)
    print(structured_data)

