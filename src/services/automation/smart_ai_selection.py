import google.generativeai as genai
# Gemini API configuration
from dotenv import load_dotenv
import os
import json

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")


def ai_smart_selecting_fun(actual_value, dropdown_values):
    output_format = """
    {
        "value": "", # String value which is select by ai.
        "reason": "" # String reason for selecting this value.
    }
    """

    text = f"""
    Your are an Helpfull AI assistant. Your task is to compare the actual value with dropdown value and return the most relivant or the exact match.
    Note: The selecting criteria is select the most close largest value.
    Note: if the values are string then selected which is reasonably most closed.

    Actual Value: {actual_value}

    Dropdown Values: {dropdown_values} 

    Always Give output is JSON format like this:
    {output_format}
    """
    prompt = [
            {
                "role": "user",
                "parts": [
                    {"text": text},
                ]
            }
        ]

    response = model.generate_content(prompt)

    response = response.text.replace('```json','').replace('```','')

    return json.loads(response)