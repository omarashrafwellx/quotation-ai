"""
Company information extraction from trade license PDFs using AI.
"""

import time
import json
from typing import Dict, Any
import google.generativeai as genai
from src.core.config import settings
from src.core.exceptions import AIServiceError, DocumentProcessingError

class CompanyExtractor:
    """Extracts company information from trade license PDFs."""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    
    def extract_company_data(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract company information from trade license PDF.
        
        Args:
            pdf_path: Path to the trade license PDF file
            
        Returns:
            Dictionary containing company information
            
        Raises:
            DocumentProcessingError: If PDF processing fails
            AIServiceError: If AI service fails
        """
        try:
            # Upload the PDF file
            uploaded_file = genai.upload_file(pdf_path)
            
            # Wait for the file to become active
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_file = genai.get_file(uploaded_file.name)
                print(f"Waiting for file to become active. Current state: {uploaded_file.state.name}")
            
            if uploaded_file.state.name != "ACTIVE":
                raise DocumentProcessingError(
                    f"File processing failed with state: {uploaded_file.state.name}"
                )
            
            print(f"File is now active: {uploaded_file.name}")
            
            # Define the prompt for data extraction
            prompt = [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": """    
This is the trade license pdf data. Carefully read the content of the pdf file and return me the company name whose trade license is given. Just directly return the company name as JSON without any extra explanation.

Example json format
{
    "company_name": "actual_company_name"
}
                            """
                        },
                        {
                            "file_data": {
                                "file_uri": uploaded_file.uri, 
                                "mime_type": "application/pdf"
                            }
                        }
                    ]
                }
            ]
            
            # Generate the response
            response = self.model.generate_content(prompt)
            response_text = response.text.strip().replace("```", "").replace("json", "")
            
            try:
                result = json.loads(response_text)
                
                # Validate the response
                if not isinstance(result, dict) or "company_name" not in result:
                    raise AIServiceError("Invalid response format from AI service")
                
                # Clean up the file
                genai.delete_file(uploaded_file.name)
                
                return result
                
            except json.JSONDecodeError as e:
                raise AIServiceError(f"Failed to parse AI response as JSON: {e}")
            
        except Exception as e:
            if isinstance(e, (DocumentProcessingError, AIServiceError)):
                raise
            raise DocumentProcessingError(f"Failed to extract company data: {e}")

# Global company extractor instance
company_extractor = CompanyExtractor()

def extract_company_data(pdf_path: str) -> Dict[str, Any]:
    """Convenience function to extract company data."""
    return company_extractor.extract_company_data(pdf_path)