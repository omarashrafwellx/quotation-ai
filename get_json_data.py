import time
import google.generativeai as genai
import json
# Replace with your actual Gemini API key
API_KEY = "AIzaSyARrmT13H-8O8yQYhfjTqI3az65r_uAPb8"

# Configure the Gemini API client
genai.configure(api_key=API_KEY)

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
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash-preview-04-17")
    
    # Define the prompt for data extraction
    prompt = [
        {
            "role": "user",
            "parts": [
                {"text": "This is the benefits table. Carefully read the content of the table and return me a structured output in JSON. Do not miss anything. Include all the details. Do not miss the complete company name which could be written in the text or in the logo. Do not include any introductory or explanatory text. The JSON should be the only output."},
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
    pdf_file_path = "Benefits Table.pdf" 
    structured_data = extract_structured_data(pdf_file_path)
    with open("test.json","w") as f:
        json.dump(structured_data, f, indent=4)
    print(structured_data)

