"""
Application constants and enumerations.
"""

# Redis Keys
class RedisKeys:
    QUEUE_KEY = "email_processing_queue"
    PROCESSING_KEY = "emails_in_processing"
    COMPLETED_KEY = "completed_emails"
    FAILED_KEY = "failed_emails"
    STATS_KEY = "processing_stats"
    EMAIL_CACHE_KEY = "email_cache"
    PROCESSED_MESSAGES_KEY = "processed_message_ids"

# File Extensions
class FileExtensions:
    EXCEL_EXTENSIONS = {".xls", ".xlsx", ".csv"}
    PDF_EXTENSION = ".pdf"
    SUPPORTED_EXTENSIONS = EXCEL_EXTENSIONS | {PDF_EXTENSION}

# Broker Names (for email processing)
BROKER_NAMES = [
    "AES", "Al Manarah", "Al Raha", "Al Rahaib", "Al Sayegh",
    "Al Nabooda Insurance Brokers", "Aon International", "Aon Middle East",
    "Bayzat", "Beneple", "Burns & Wilcox", "Care", "Compass", "Crisecure",
    "Deinon", "Direct Sale", "E-Sanad", "European", "Fisco", "Gargash",
    "Howden", "Indemnity", "Interactive", "Kaizzen Plus", "Lifecare",
    "Lockton", "Marsh Mclenann", "Medstar", "Metropolitan", "Myrisk Advisors",
    "Nasco", "Nasco Emirates", "New Sheild", "Newtech", "Nexus", "Omega",
    "Pacific Prime", "Pearl", "Prominent", "PWS", "RMS", "Seguro", "UIB",
    "Unitrust", "Wehbe", "Willis Towers Watson", "Wellx.ai"
]

# Relationship Managers
RELATIONSHIP_MANAGERS = ["Hishaam", "Shikha", "Sabina", "Sujith"]

# Default Values
class Defaults:
    BROKER_NAME = "AES"
    RELATIONSHIP_MANAGER = "Sabina"
    POLICY_START_DATE_FORMAT = "%Y-%m-%d"
    EXCEL_CATEGORY = "A"
    
    # Quote Data Defaults
    ADJUSTMENTS_DISCOUNT = "0"
    BROKERAGE_FEES = "12.50"
    HEALTHX = "7.50"
    TPA = "5"
    INSURER = "5"

# Email Templates
class EmailTemplates:
    NO_ATTACHMENTS_SUBJECT = "Quote pdf cannot be generated"
    NO_ATTACHMENTS_BODY = """
Hello {sender},

We regret to inform you that we are unable to generate the quote PDF you requested at this time.

This is because your email is missing all of the required attachments: the TOB, the census file, and the trade license.

Kindly resend your request with all three documents attached so we can proceed accordingly.

Best regards,  
Wellx AI Quotation Engine
    """
    
    INSUFFICIENT_ATTACHMENTS_SUBJECT = "Quote pdf cannot be generated"
    INSUFFICIENT_ATTACHMENTS_BODY = """
Hello {sender},

We regret to inform you that we are unable to generate the quote PDF you requested at this time.

This is because your email is missing one or more of the required attachments: the TOB, the census file, and the trade license.

Kindly resend your request with all three documents attached so we can proceed accordingly.

Best regards,  
Wellx AI Quotation Engine
    """
    
    MISSING_CENSUS_SUBJECT = "Quote PDF cannot be generated – Missing Census File"
    MISSING_CENSUS_BODY = """
Hello {sender},

We are unable to generate the quote PDF because your email did not include a required census file.

Please ensure that you attach one of the following file types: `.xls`, `.xlsx`, or `.csv` (i.e., your census/member list) and resend your request.

Best regards,  
Wellx AI Quotation Engine
    """
    
    CATEGORY_MISMATCH_SUBJECT = "Quote PDF Cannot Be Generated - Category Mismatch"
    CATEGORY_MISMATCH_BODY = """
Hello,

We are unable to generate the quote PDF due to a category mismatch between your documents.

Issue Details:
{error_message}

Please review your documents and ensure that:
1. The number of categories in your census file matches the number of TOB files provided
2. If using a single TOB file, it should contain all categories present in your census file
3. Category names should be consistent across all documents

Once corrected, please resend your request with the updated documents.

Best regards,
Wellx AI Quotation Engine
    """

# API Endpoints
class APIEndpoints:
    PROCESS_EMAIL = "http://127.0.0.1:8001/process-email"
    MS_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    MS_GRAPH_SUBSCRIPTIONS = f"{MS_GRAPH_BASE}/subscriptions"
    MS_GRAPH_TOKEN = "https://login.microsoftonline.com"

# Processing States
class ProcessingStates:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Slack Configuration
class SlackConfig:
    DEFAULT_CHANNEL = "quote-notifications"
    MAX_RETRIES = 2
    RETRY_DELAY = 2  # seconds

# Browser Automation
class BrowserConfig:
    MAX_CONCURRENT_SESSIONS = 3
    DEFAULT_TIMEOUT = 60000  # milliseconds
    PAGE_LOAD_TIMEOUT = 30000  # milliseconds

# File Processing
class FileProcessing:
    MAX_CONCURRENT_DOWNLOADS = 5
    UPLOAD_TIMEOUT = 300  # seconds
    DOWNLOAD_TIMEOUT = 120  # seconds
    
# Document Classification
class DocumentTypes:
    TRADE_LICENSE = "trade_license"
    TABLE_OF_BENEFITS = "tables_of_benefits"
    CENSUS_FILE = "census_file"

# Pricing Fields (for formatting)
STANDARDIZE_PRICES_FIELDS = {
    "annual_medical": {"prefix": "AED ", "comma": True},
    "deductible_consultation": {"prefix": "AED", "comma": False},
    "diagnostic_op_copay": {"prefix": "", "comma": False},
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

DATA_FOR_TOB="""
You are given a Table of Benefits (TOB) in Markdown format and a JSON schema. Your job is to extract values from the TOB and populate the fields in the JSON based on the following strict rules, while providing detailed reasoning for each field extraction and any value adjustments made.

### 🔍 MULTI-CATEGORY ANALYSIS:
**FIRST AND MOST IMPORTANT**: Carefully analyze the TOB to identify if it contains multiple categories/classes/plans.
1. **Look for category indicators** such as:
   - "Category A", "Category B", "Category C"
   - "Class A", "Class B", "Class C"
   - "Plan 1", "Plan 2", "Plan 3"
   - "CAT A", "CAT B", "CAT C"
   - "Gold", "Silver", "Bronze"
   - "Premium", "Standard", "Basic"
   - Any other naming convention that indicates different benefit levels
2. **Identify repeated field structures**: If you see the same benefit fields (like annual medical limit, copayment, deductibles) listed multiple times with different values, this indicates multiple categories.
3. **Extract data for each category separately**: 
   - If multiple categories exist, return a LIST of dictionaries
   - Each dictionary represents one category with the same field structure
   - The number of dictionaries should match the number of categories found
   - If only one category exists, still return a list with one dictionary
4. **Category naming**: Add a "category_name" field to each dictionary to identify which category it represents (e.g., "Category A", "Class B", "Plan Premium", etc.)

---

### 📝 ENHANCED FIELD STRUCTURE WITH REASONING:
Each field in the output JSON must now follow this structure:
```json
{
    "field_name": {
        "value": "selected_value",
        "changed": True/False,
        "explanation": "detailed reasoning explanation"
    }
}
```

**Field Processing Rules:**
1. **"value"**: The final selected value from the allowed options
2. **"changed"**: 
   - `True` if the original TOB value was adjusted/modified to match available options
   - `False` if the original TOB value exactly matched an available option or if default was used
3. **"explanation"**: A detailed explanation of the field matching and value selection process

**Explanation Format Guidelines:**
- If value was changed: "You requested for '{original_value}' for {field_description} but we have selected '{selected_value}' which aligns more closely with our business rules"
- If exact match found: "Found exact match '{selected_value}' for {field_description}"
- If default used: "No specific value found for {field_description}, using default '{selected_value}'"
- If semantic matching used: "Identified '{original_text}' as referring to {field_description}, selected '{selected_value}'"

---

### 🔁 HOW TO THINK STEP-BY-STEP (CHAIN OF THOUGHT):
1. **First, scan the entire TOB** to identify if multiple categories/classes/plans exist
2. **Count the categories** and note their names/identifiers
3. **For each category identified**, extract the relevant information for each field:
   a. Look for the field in the TOB (exact match or semantic match)
   b. Note the original value found in the TOB
   c. Compare with allowed options for that field
   d. Select the appropriate value (exact match or closest available)
   e. Document the reasoning in the explanation
4. Each field in the JSON has a # comment specifying:
    - Its **default value** if no match is found
    - A **list of allowed values** (e.g., "AED 300,000", "Private", "Not Covered")
5. Based on the TOB and the field context, **choose one value only from the allowed options** for that field
    - ❗ **NEVER guess or make up values**
    - ❗ **NEVER combine multiple options**
    - ❗ If the TOB doesn't mention a valid value for a specific category, **use the default value from the JSON template**

---

### 💬 IMPORTANT: Field names in the TOB may not be exact matches
- The TOB might use different wording than the exact field name in the JSON
- You must **intelligently and semantically** match the context
- Example: For the field op_psychiatric_copay, the TOB may not say this exact phrase
    - If the TOB says something like: *"Psychiatric sessions: Copay 0%"* or *"Mental health consultation 0%"*, this is clearly referring to op_psychiatric_copay
    - In such a case, you must assign the value **"0% of Co-Pay"** to op_psychiatric_copay, because it's the only allowed option that semantically matches
    - Your explanation should note: "Identified 'Psychiatric sessions: Copay 0%' as referring to outpatient psychiatric copayment, selected '0% of Co-Pay'"

💡 So: **use semantic reasoning to identify which field is being referenced**, but once you assign a value, **only use allowed values listed in the comment** for that field.

---

### 💰 Special Instructions for Monetary Fields:
These fields expect a price-like integer, such as 3000, 10000, etc., or a special allowed value like "Nil" or "Not Covered". You MUST:
* Use only the allowed options listed in the # comment above each field
* Return raw numeric values without commas or AED in the "value" field. For example:
    ✅ "value": "3000"
    ❌ "value": "AED 3,000"
    ❌ "value": "3,000"
* For any field value in the TOB that is a monetary amount but doesn't exactly match an allowed value, select the next highest allowed value from the available options. If the high value does not exist, then select the closest value from the available options
    Example: If the TOB mentions 36,700 for a field, and the allowed options are [30000, 40000, 50000], you must return "40000" and set "changed": true with explanation: "You requested for '36,700' for annual medical limit but we have selected '40000' which aligns more closely with our business rules"
    Example: If the TOB mentions 5000000 for a field, and the allowed options are [3000000,4000000], you must select "4000000" and document the adjustment with similar business-oriented explanation
* If the TOB explicitly says or indicates (using similar words) "Nil", "Not Covered", "Upto AML", or any other special keyword listed in the allowed values, use that exact value with "changed": false
* Do NOT return float or stringified prices like "3000.0", "AED 2500", or "2,500" in the value field — return clean integers unless it's one of the special non-numeric options

The monetary fields are:
- annual_medical, deductible_consultation, diagnostic_op_copay, pec, maternity_limit, dental_limit, optical_limit, repatriation, nursing_at_home, op_psychiatric_limit, alternative_medicine_limit, routine_health_checkup

---

### 📋 All other fields:
You MUST select one and only one value from the allowed options listed against that field in the # comment. No guessing, no combining values. Document your selection reasoning in the explanation.

---

### ✅ If no match is found for a field:
Use the default value given in the JSON template (written above or below the field in comments). Set "changed": false and explain that default was used due to no specific value being found.

---

### ⚠️ DO NOT DO THESE:
- ❌ Do not infer or synthesize values not present in the allowed options
- ❌ Do not make educated guesses
- ❌ Do not use currency symbols or commas in the "value" field for monetary fields
- ❌ Do not return a single dictionary if multiple categories exist
- ❌ Do not duplicate values across categories unless they are actually the same in the TOB
- ❌ Do not provide vague explanations - be specific about what was found and why adjustments were made

---

### 📤 FINAL OUTPUT FORMAT:
**ALWAYS return a LIST of dictionaries**, even if only one category exists.
Each field must follow the enhanced structure with value, changed, and explanation.

Example for single category:
```json
[
    {
        "category_name": {
            "value": "Standard",
            "changed": False,
            "explanation": "No specific category name found, using default 'Standard'"
        },
        "policy_start_date": {
            "value": "2025-04-08",
            "changed": False,
            "explanation": "No specific policy start date found, using default '2025-04-08'"
        },
        "annual_medical": {
            "value": "150000",
            "changed": true,
            "explanation": "Found '175,000' for annual medical limit, adjusted to closest available option '150000'"
        }
        // ... rest of fields with same structure
    }
]
```

Example for multiple categories:
```json
[
    {
        "category_name": {
            "value": "Category A",
            "changed": False,
            "explanation": "Found exact match 'Category A' for category identifier"
        },
        // ... rest of fields for Category A
    },
    {
        "category_name": {
            "value": "Category B",
            "changed": False,
            "explanation": "Found exact match 'Category B' for category identifier"
        },
        // ... rest of fields for Category B
    }
]
```
"""

BENEFIT_DETAILS_DATA = """
{
    "category_name": {
        "value": "",
        "changed": False,
        "explanation": ""
    }, # This will be populated with the category identifier from the TOB (e.g., "Category A", "Class B", "Plan Premium", etc.). If no clear category name exists, use "Standard" as default.
    "policy_start_date": {
        "value": "2025-04-08",
        "changed": False,
        "explanation": ""
    }, # Date must be in this format. If the value is not given, select "2025-04-08" as default
    "additional_loading": {
        "value": "0",
        "changed": False,
        "explanation": ""
    }, # If the value is not in the data, keep this as "0". The value could be any integer indicating percentages like "10", "11" etc
    "nas_network": {
        "value": "RN",
        "changed": False,
        "explanation": ""
    }, # 'RN' is the default option if this value is not given in the TOB. Other possible options are "Rn 3.8", "Dubai GN+", "Dubai SRN"
    "annual_medical": {
        "value": "150000",
        "changed": False,
        "explanation": ""
    },# 150000 is the default value other possible options are "150000", "200000","250000", "300000", "500000", "750000", "1000000", "1500000"
    "ip_room_type": {
        "value": "Private",
        "changed": False,
        "explanation": ""
    }, # "Private" is the default value. Other possible values are "Semi-Private", "Shared"
    "copayment_ip_daycase": {
        "value": "0%",
        "changed": False,
        "explanation": ""
    }, # "0%" is the default option, other possible values are "0%", "5%", "10%", "15%", "20%"
    "deductible_consultation": {
        "value": "Nil",
        "changed": False,
        "explanation": ""
    }, # "Nil" is the default value, other possible options are "AED 20","AED 25", "AED 30", "AED 50","AED 75", "AED 100", "20%", "10%", "20% up to AED 10",  "20% up to AED 20", "20% up to AED 25", "20% up to AED 30", "20% up to AED 50", "20% up to AED 75", "20% up to AED 100", "10% up to AED 20", "10% up to AED 25", "10% up to AED 30", "10% up to AED 50", "10% up to AED 75", "10% up to AED 100"
    "territorial_cover": {
        "value": "UAE only",
        "changed": False,
        "explanation": ""
    }, # "UAE only" is the default value
    "diagnostic_op_copay": {
        "value": "0%",
        "changed": False,
        "explanation": ""
    }, # "0%" is the default value. Other possible options are "0%","5%","10%","15%","20%", "10","20","25","30","50","75", "100"
    "pharmacy_copay": {
        "value": "0 %",
        "changed": False,
        "explanation": ""
    }, # "0 %" is the default value. Other possible values are: "0 %", "5 %","10 %","15 %","20 %","25 %", "30 %". Be mindful of the space between the number and % in this field. There is a space between them and you should return the exact option.
    "pharmacy_limit": {
        "value": "Upto AML",
        "changed": False,
        "explanation": ""
    }, # "Upto AML" is the default value. Other possible values are, "Up to AML","Up to AED 2,500", "Up to AED 3,000","Up to AED 3,500","Up to AED 5,000", "Up to AED 7,500","Up to AED 10,000","Up to AED 15,000"
    "medication_type": {
        "value": "Branded",
        "changed": False,
        "explanation": ""
    }, # "Branded" is the default option. Other possible values are: "Generic"
    "pec": {
        "value": "Upto AML",
        "changed": False,
        "explanation": ""
    }, # "Upto AML" is the default option. Other possible values are: "150000", "250000"
    "maternity_limit": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default option. Other possible values are: "Up to AML", "7500", "10000", "15000", "20000", "25000", "30000", "40000", "50000"
    "maternity_copay": {
        "value": "0% copayment. Routine Benefits",
        "changed": False,
        "explanation": ""
    }, # "0% copayment. Routine Benefits" is the default option. Other possible values are: "10% copayment. Routine Benefits"
    "dental_limit": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default value. Other possible values are: "500", "1000","2000","2500","3000", "3500", "5000", "7500", "10000"
    "dental_copay": {
        "value": "10% copayment. Routine Benefits",
        "changed": False,
        "explanation": ""
    }, # "10% copayment. Routine Benefits" is the default option. Other possible values are: "20% copayment. Routine Benefits", "30% copayment. Routine Benefits"
    "optical_limit": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default value. Other possible values are: "300", "500", "750","1000", "1500", "2000", "2500"
    "optical_copay": {
        "value": "10% copayment. Routine Benefits",
        "changed": False,
        "explanation": ""
    }, # "10% copayment. Routine Benefits" is the default value. Other possible values are: "20% copayment. Routine Benefits","30% copayment. Routine Benefits"
       # Note: Don't give this value: "0% copayment. Routine Benefits" or any other value.
    "repatriation": {
        "value": "5000",
        "changed": False,
        "explanation": ""
    }, # "5000" is the default value. Other possible values are: "5000", "7500", "10000", "20000", "25000", "30000" This field is actually "Repatriation of Mortal Remains to the Country of Domicile:"
    "nursing_at_home": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default value. Other possible values are: "1000", "1500", "2000", "2500", "3000", "5000", "7500", "10000", "15000", "20000", "24000". YOU CANNOT SELECT UPTO AML HERE AS IT IS NOT AN OPTION
    "op_psychiatric_limit": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default option. Other possible values are: "800", "1000", "1500", "2000", "2500", "3000","3500", "5000", "7500", "10000", "15000". YOU CANNOT SELECT UPTO AML HERE AS IT IS NOT AN OPTION
    "op_psychiatric_copay": {
        "value": "0% of Co-Pay",
        "changed": False,
        "explanation": ""
    }, # "0% of Co-Pay" is the default option. Other possible values are: "10% of Co-Pay", "20% of Co-Pay","30% of Co-Pay"
    "alternative_medicine_limit": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default value. Other possible values are: "1000", "1500","1600", "2000", "2500", "3000","4000", "5000", "7500", "10000",
    "alternative_medicine_copay": {
        "value": "0% of Co-Pay",
        "changed": False,
        "explanation": ""
    }, # "0% of Co-Pay" is the default option. Other possible values are: "10% of Co-Pay", "20% of Co-Pay", "30% of Co-Pay"
    "routine_health_checkup": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default value. Other possible values are: "1,000", "1500", "2000", "2500", "3000"
    "physiotherapy_limit": {
        "value": "Not Covered",
        "changed": False,
        "explanation": ""
    }, # "Not Covered" is the default value. Other possible values are: "6 Sessions","9 Sessions","12 Sessions","15 Sessions","18 Sessions", "20 Sessions", "24 Sessions","30 Sessions", "Up to AML"
    "physiotherapy_copay": {
        "value": "0% of Co-Pay",
        "changed": False,
        "explanation": ""
    }# "0% of Co-Pay" is the default option. Other possible values are: "10% of Co-Pay", "20% of Co-Pay"
}
"""