import time
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# Gemini API configuration
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Fields requiring price formatting
STANDARDIZE_PRICES_FIELDS = {
    "annual_medical": {"prefix": "AED ", "comma": True},
    "deductible_consultation": {"prefix": "", "comma": False},
    "diagnostic_op_copay": {"prefix": "", "comma": False},
    "pec": {"prefix": "", "comma": False},
    "maternity_limit": {"prefix": "", "comma": False},
    "dental_limit": {"prefix": "", "comma": False},
    "optical_limit": {"prefix": "", "comma": False},
    "repatriation": {"prefix": "", "comma": True},
    "nursing_at_home": {"prefix": "", "comma": True},
    "op_psychiatric_limit": {"prefix": "", "comma": True},
    "alternative_medicine_limit": {"prefix": "", "comma": True},
    "routine_health_checkup": {"prefix": "", "comma": False},
}

def format_price(value, prefix="", comma=False):
    try:
        num = int(str(value).replace(",", "").replace("AED", "").strip())
        formatted = f"{num:,}" if comma else str(num)
        return f"{prefix}{formatted}".strip()
    except:
        return value  # Leave as-is for "Upto AML", "Not Covered", etc.

# Initial system instructions and template
data="""
You are given a Table of Benefits (TOB) in Markdown format and a JSON schema. Your job is to extract values from the TOB and populate the fields in the JSON based on the following strict rules.

---

### 🔁 HOW TO THINK STEP-BY-STEP (CHAIN OF THOUGHT):

1. **Carefully read the TOB in Markdown** and identify the relevant information for each field.
2. Each field in the JSON has a `# comment` specifying:
    - Its **default value** if no match is found.
    - A **list of allowed values** (e.g., `"AED 300,000"`, `"Private"`, `"Not Covered"`).
3. Based on the TOB and the field context, **choose one value only from the allowed options** for that field.
    - ❗ **NEVER guess or make up values**.
    - ❗ **NEVER combine multiple options**.
    - ❗ If the TOB doesn’t mention a valid value, **use the default value from the JSON template**.

---

### 💬 IMPORTANT: Field names in the TOB may not be exact matches

- The TOB might use different wording than the exact field name in the JSON.
- You must **intelligently and semantically** match the context.
- Example: For the field `op_psychiatric_copay`, the TOB may not say this exact phrase.
    - If the TOB says something like: *"Psychiatric sessions: Copay 0%"* or *"Mental health consultation 0%"*, this is clearly referring to `op_psychiatric_copay`.
    - In such a case, you must assign the value **`"0% of Co-Pay"`** to `op_psychiatric_copay`, because it's the only allowed option that semantically matches.

💡 So: **use semantic reasoning to identify which field is being referenced**, but once you assign a value, **only use allowed values listed in the comment** for that field.

---

### 💰 Special Instructions for the Following Monetary Fields:
    These fields expect a price-like integer, such as 3000, 10000, etc., or a special allowed value like "Nil" or "Not Covered". You MUST:
    
    * Use only the allowed options listed in the # comment above each field.

    * Return raw numeric values without commas or AED. For example:

        ✅ 3000

        ❌ AED 3,000

        ❌ 3,000

    * For any field value in the TOB that is a monetary amount but doesn't exactly match an allowed value, select the next highest allowed value from the available options. If the high value does not exist, then select the closest value from the available options.

        Example: If the TOB mentions 36,700 for a field, and the allowed options are [30000, 40000, 50000], you must return 40000.
        Example: If the TOB mentions 5000000 for a field, and the allowed options are [3000000,4000000], you must select 4000000.

    * If the TOB explicitly says or indicates (using similar words) "Nil", "Not Covered", "Upto AML", or any other special keyword listed in the allowed values, use that exact value.

    * Do NOT return float or stringified prices like "3000.0", "AED 2500", or "2,500" — return clean integers unless it's one of the special non-numeric options.

    The monetary fields are:

    - `annual_medical`
    - `deductible_consultation`
    - `diagnostic_op_copay`
    - `pec`
    - `maternity_limit`
    - `dental_limit`
    - `optical_limit`
    - `repatriation`
    - `nursing_at_home`
    - `op_psychiatric_limit`
    - `alternative_medicine_limit`
    - `routine_health_checkup`

    ---

### 📋 All other fields:

You MUST select one and only one value from the allowed options listed against that field in the `# comment`. No guessing, no combining values.

---

### ✅ If no match is found for a field:
Use the default value given in the JSON template (written above or below the field in comments). Do NOT return an empty string or generate your own defaults.
---

### ⚠️ DO NOT DO THESE:
- ❌ Do not infer or synthesize values not present in the allowed options.
- ❌ Do not make educated guesses.
- ❌ Do not use currency symbols or commas in any monetary field.

--

          
    
    Example JSON response:
    {{
    "policy_start_date": "2025-04-08",
    "additional_loading": "0",
    "nas_network": "RN",
    "annual_medical": "AED 150,000",
    "ip_room_type": "Private",
    "copayment_ip_daycase": "0%",
    "deductible_consultation": "Nil",
    "territorial_cover": "UAE only",
    "diagnostic_op_copay": "0%", 
    "pharmacy_copay": "0 %",
    "pharmacy_limit": "Upto AML", 
    "medication_type": "Branded",
    "pec": "Upto AML",
    "maternity_limit": "Not Covered",
    "maternity_copay": "0% copayment. Routine Benefits",
    "dental_limit": "Not Covered", 
    "dental_copay": "0% copayment. Routine Benefits", 
    "optical_limit": "Not Covered", 
    "optical_copay": "0% copayment. Routine Benefits",
    "repatriation": "Not Covered", 
    "nursing_at_home": "Not Covered",
    "op_psychiatric_limit": "Not Covered",
    "op_psychiatric_copay": "0% of Co-Pay", 
    "alternative_medicine_limit": "Not Covered", 
    "alternative_medicine_copay": "0% of Co-Pay",
    "routine_health_checkup":"Not Covered", 
    "physiotherapy_limit": "Not Covered", 
    "physiotherapy_copay": "0% of Co-Pay",
                    }}
"""

BENEFIT_DETAILS_DATA ="""
{
    "policy_start_date": "2025-04-08", # Date must be in this format. If the value is not given, select "2025-04-08" as default
    "additional_loading": "0", # If the value is not in the data, keep this as "0". The value could be any integer indicating percentages like "10", "11" etc
    "nas_network": "RN", # 'RN' is the default option if this value is not given in the TOB. Other possible options are "Rn 3.8", "Dubai GN+", "Dubai SRN"
    "annual_medical": "AED 150,000",# AED 150,000 is the default value other possible options are "AED 250,000", "AED 300,000", "AED 500,000", "AED 1,000,000", "AED 1,500,000", "AED 2,000,000", "AED 2,500,000"
    "ip_room_type": "Private", # "Private" is the default value. Other possible values are "Semi-Private", "Shared"
    "copayment_ip_daycase": "0%", # "0%" is the default option, other possible values are "5%", "10%", "15%", "20%", "30%"
    "deductible_consultation": "Nil", # "Nil" is the default value, other possible options are "AED 20","AED 25", "AED 30", "AED 50","AED 75", "AED 100", "20%", "10%"
    "territorial_cover": "UAE only", # "UAE only" is the default value
    "diagnostic_op_copay": "0%", # "0%"" is the default value. Other possible options are "0%","5%","10%","15%","20%", "AED 10","AED 20","AED 25","AED 30","AED 50","AED 75", "AED 100"
    "pharmacy_copay": "0 %", # "0 %" is the default value. Other possible values are: "5 %","10 %","15 %","20 %","25 %", "30 %". Be mindful of the space between the number and % in this field. There is a space between them and you should return the exact option.
    "pharmacy_limit": "Upto AML", # "Upto AML" is the default value. Other possible values are "10% of AML", "20% of AML","30% of AML","40% of AML","50% of AML"
    "medication_type": "Branded", # "Branded" is the default option. Other possible values are: "Generic"
    "pec": "Upto AML", # "Upto AML" is the default option. Other possible values are: "150000", "250000"
    "maternity_limit": "Not Covered", # "Not Covered" is the default option. Other possible values are: "Up to AML", "7500", "10000", "15000", "20000", "25000", "30000", "40000", "50000"
    "maternity_copay": "0% copayment. Routine Benefits", # "0% copayment. Routine Benefits" is the default option. Other possible values are: "10% copayment. Routine Benefits", "20% copayment. Routine Benefits", "30% copayment. Routine Benefits"
    "dental_limit": "Not Covered", # "Not Covered" is the default value. Other possible values are: "1000", "2000","2500","3000", "3500", "5000", "7500", "10000"
    "dental_copay": "0% copayment. Routine Benefits", # "0% copayment. Routine Benefits" is the default option. Other possible values are: "10% copayment. Routine Benefits","20% copayment. Routine Benefits", "30% copayment. Routine Benefits"
    "optical_limit": "Not Covered", # "Not Covered" is the default value. Other possible values are: "300", "500", "750","1000", "1500", "2000", "2500"
    "optical_copay": "0% copayment. Routine Benefits", # "0% copayment. Routine Benefits" is the default value. Other possible values are: "10% copayment. Routine Benefits","20% copayment. Routine Benefits","30% copayment. Routine Benefits"
    "repatriation": "Not Covered", # "Not Covered" is the default value. Other possible values are: "5,000", "7,500", "10,000", "20,000", "25,000", "30,000" This field is actually "Repatriation of Mortal Remains to the Country of Domicile:"
    "nursing_at_home": "Not Covered", # "Not Covered" is the default value. Other possible values are: "1,000", "1,500", "2,000", "2,500", "3,000", "5,000", "7,500", "10,000", "15,000", "20,000", "24,000". YOU CANNOT SELECT UPTO AML HERE AS IT IS NOT AN OPTION
    "op_psychiatric_limit": "Not Covered", # "Not Covered" is the default option. Other possible values are: "1,000", "1,500", "2,000", "2,500", "3,000", "5,000", "7,500", "10,000", "15,000". YOU CANNOT SELECT UPTO AML HERE AS IT IS NOT AN OPTION
    "op_psychiatric_copay": "0% of Co-Pay", # "0% of Co-Pay" is the default option. Other possible values are: "10% of Co-Pay", "20% of Co-Pay"
    "alternative_medicine_limit": "Not Covered", # "Not Covered" is the default value. Other possible values are: "1,000", "1,500", "2,000", "2,500", "3,000","4,000", "5,000", "7,500", "10,000",
    "alternative_medicine_copay": "0% of Co-Pay", # "0% of Co-Pay" is the default option. Other possible values are: "10% of Co-Pay", "20% of Co-Pay"
    "routine_health_checkup":"Not Covered", # "Not Covered" is the default value. Other possible values are: "1000", "1500", "2000", "2500", "3000"
    "physiotherapy_limit": "Not Covered", # "Not Covered" is the default value. Other possible values are: "6 Sessions","9 Sessions","12 Sessions","15 Sessions","18 Sessions", "20 Sessions", "24 Sessions","30 Sessions", "Up to AML"
    "physiotherapy_copay": "0% of Co-Pay",# "0% of Co-Pay" is the default option. Other possible values are: "10% of Co-Pay", "20% of Co-Pay"
}
"""
def extract_markdown_from_pdf(pdf_path: str) -> str:
    uploaded_file = genai.upload_file(pdf_path)

    while uploaded_file.state.name == "PROCESSING":
        time.sleep(1)
        uploaded_file = genai.get_file(uploaded_file.name)
        print(f"Waiting for file to become active. Current state: {uploaded_file.state.name}")

    if uploaded_file.state.name != "ACTIVE":
        raise Exception(f"File processing failed with state: {uploaded_file.state.name}")

    print(f"File is now active: {uploaded_file.name}")

    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    prompt = [
        {
            "role": "user",
            "parts": [
                {"text": "This is the benefits table. Carefully read the content of the table and return me a markdown for it. Do not miss anything. Include all the details. Do not miss the complete company name which could be written in the text or in the logo. Do not include any introductory or explanatory text. The markdown should be the only output."},
                {"file_data": {"file_uri": uploaded_file.uri, "mime_type": "application/pdf"}}
            ]
        }
    ]
    response = model.generate_content(prompt)
    return response.text.strip().replace("```", "").replace("markdown", "")

def extract_structured_data_from_tob(tob_markdown: str, json_template: dict) -> dict:
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    prompt = [
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
                    {json_template}
                    """
                }
            ]
        }
    ]
    response = model.generate_content(prompt)
    response_text = response.text.strip().replace("```", "").replace("json", "")
    raw_json = json.loads(response_text)

    for field, rules in STANDARDIZE_PRICES_FIELDS.items():
        if field in raw_json:
            value = raw_json[field]
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                raw_json[field] = format_price(str(value), prefix=rules["prefix"], comma=rules["comma"])
    return raw_json

if __name__ == "__main__":
    pdf_path = "files/pdf/Benefits Table.pdf"
    print("🔍 Extracting markdown from PDF...")
    markdown_text = extract_markdown_from_pdf(pdf_path)
    
    print("\n📄 Extracted Markdown:")
    print(markdown_text[:500] + "\n...") 

    print("\n📊 Extracting structured JSON...")
    final_data = extract_structured_data_from_tob(markdown_text, BENEFIT_DETAILS_DATA)

    output_path = "output.json"
    with open(output_path, "w") as f:
        json.dump(final_data, f, indent=4)
    
    print(f"\n✅ JSON saved to {output_path}")
    print(json.dumps(final_data, indent=4))
