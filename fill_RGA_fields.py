import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
load_dotenv()


STANDARDIZE_PRICES_FIELDS = {
    "annual_medical": {"prefix": "AED ", "comma": True},
    "deductible_consultation":{"prefix": "", "comma": False},
    "diagnostic_op_copay":{"prefix": "", "comma": False},
    "pec": {"prefix": "", "comma": False},
    "maternity_limit": {"prefix": "", "comma": False},
    "dental_limit": {"prefix": "", "comma": False},
    "optical_limit": {"prefix": "", "comma": False},
    "repatriation": {"prefix": "", "comma": True},
    "nursing_at_home": {"prefix": "", "comma": True},
    "op_psychiatric_limit": {"prefix": "", "comma": True},
    "alternative_medicine_limit": {"prefix": "", "comma": True},
    "routine_health_checkup": {"prefix": "", "comma": True},
}

def format_price(value, prefix="", comma=False):
    try:
        num = int(value.replace(",", "").replace("AED", "").strip())
        formatted = f"{num:,}" if comma else str(num)
        return f"{prefix}{formatted}".strip()
    except:
        return value  # In case of "Upto AML", "Not Covered", etc.
data="""
     "You are given a Table of Benefits (TOB) in Markdown format and a JSON schema. "
    "Extract values from the TOB and populate the corresponding fields in the JSON. "
    "If no matching value is found for a field, set the default value for it"
    "Return only the JSON — no explanations.\n\n"
    "### Example TOB (Markdown):\n"
    "## Table of Benefits:\n"
    "TPA: NAS\n"
    "Category: Category A\n"
    "Region: Dubai\n"
    "Plan Name: Comprehensive Network\n"
    "Access: ( Direct Access to Network Hospital/ Clinics for OP Treatment )\n"
    "Annual Medical Limit: AED 1,000,000\n"
    "Inpatient Room Type: Private\n"
    "Coinsurance: 0% - Cap of 500 AED payable per encounter and an annual aggregate cap of 1000 AED (for insured). Above these caps the insurer will cover 100% of treatment.\n"
    "Consultation Deductible: Nil\n"
    "Area of Coverage: Worldwide at R&C of UAE\n"
    "Diagnostics OP Copay: 0%\n"
    "Pharmacy Copay: 0%\n"
    "Pharmacy Limit: Upto AML\n"
    "Medication Type: Branded\n"
    "PEC Limit: Upto AML - AML applies if evidence of continuity of coverage (COC) in UAE is provided; otherwise, PEC will be restricted to AED 150000\n"
    "Maternity: Limit AED 25000, Copay 0%, Additional Premium -, Lives 0\n"
    "Dental: Limit AED 500, Copay 30%, Additional Premium 305, Lives 1\n"
    "Optical: Not Covered, Copay 20%, Additional Premium -, Lives 1\n"
    "Impact to Base Rate: AML 95.4%, Room Type 100%, Coinsurance 100%, Deductible 110%, Area of Coverage 100%, Diagnostics OP Copay 100%, Pharmacy Copay 100%, Pharmacy Limit 100%, Medication Type 100%, PEC Limit 100%\n\n"
                        
    
    ### IMPORTANT POINTS.
    1. Pay attention to the exact available options provided against each field. One field similar in context can have different type of options available. Always refer to the exact default and possible values to fill in the JSON
    2. If you cannot find any value for the field, keep the default value for it (except the `additional_loading` field which will be empty if value not found)
    3. The field names may not exactly match from the TOB data. You need to intelligently decide which data belongs to which field. Refer to the contextual similarity if the exact fields do not match in the TOB.
        For example: Instead of dental limit, there could be teeth limit or similar words.
    4. You must select values from the default and given available options only. YOU MUST NOT WRITE ANYTHING OUTSIDE THE DEFAULT AND GIVEN OPTIONS AGAINST THAT SPECIFIC FIELD. DO NOT MIX THE OPTIONS OF OTHER FIELDS. ALL FIELD OPTIONS ARE WRITTEN AGAINST THAT FIELD IN # COMMENTS
                        
    {{
    "policy_start_date": "2025-04-08",
    "additional_loading": "15",
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
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
def extract_structured_data_from_tob(tob_markdown: str, json_template: dict):
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    instructions = data + "\nIMPORTANT: For all monetary fields, return only raw numeric values without AED or commas (e.g., return `'3000'` instead of `AED 3,000` or `3,000`). Return non-numeric values like `Not Covered` or `Upto AML` as-is. Even if `AED` is written with some monetary field, just return the monetary value not with AED."
    prompt = [
        {
            "role": "user",
            "parts": [
                {
                    "text":
                    f"""
                    {instructions}
                    "Now process the following TOB and fill this JSON structure:
                    "### TOB (Markdown):
                    {tob_markdown}
                    "### JSON Template:
                    {json.dumps(json_template, indent=4)}"
                    """
                
                }
            ]
        }
    ]
    response = model.generate_content(prompt)
    response_text = response.text.strip().replace("```", "").replace("json", "")
    raw_json = json.loads(response_text)
    # Post-process monetary values based on rules
    for field, rules in STANDARDIZE_PRICES_FIELDS.items():
        if field in raw_json:
            value = raw_json[field]
            # If it's a number, convert to string and format; if not, leave as-is
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                raw_json[field] = format_price(str(value), prefix=rules["prefix"], comma=rules["comma"])
    return raw_json
if __name__ == "__main__":
    # Load TOB content from a Markdown file
    with open("sample_markdowns/TOB.md", "r", encoding="utf-8") as f:
        tob_markdown = f.read()
                
    BENEFIT_DETAILS_DATA = {
    "policy_start_date": "2025-04-08", # Date must be in this format. If the value is not given, select "2025-04-08" as default
    "additional_loading": "15", # Example value. If the value is not in the data, keep this as empty string
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
    "routine_health_checkup":"Not Covered", # "Not Covered" is the default value. Other possible values are: "1,000", "1,500", "2,000", "2,500", "3,000"
    "physiotherapy_limit": "Not Covered", # "Not Covered" is the default value. Other possible values are: "6 Sessions","9 Sessions","12 Sessions","15 Sessions","18 Sessions", "20 Sessions", "24 Sessions","30 Sessions", "Up to AML"
    "physiotherapy_copay": "0% of Co-Pay",# "0% of Co-Pay" is the default option. Other possible values are: "10% of Co-Pay", "20% of Co-Pay"
}


    structured_data = extract_structured_data_from_tob(tob_markdown, BENEFIT_DETAILS_DATA)
    with open("output1.json", "w") as f:
        json.dump(structured_data, f, indent=4)
    print(structured_data)
    
    
