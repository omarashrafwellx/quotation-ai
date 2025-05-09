import google.generativeai as genai
import os
import json
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))



def extract_structured_data_from_email(email_content):
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
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
                    
                    * The `broker_name` value MUST only be from these available optons (case incensitive) given below.
                        * If any broker name provided in the email closely matches with any one of the options listed below, select from only the given exact values. 
                        * If the broker name mentioned in the email does not match with any of the names mentioned in the options above, select the default option "AES"
                    
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
    response = model.generate_content(prompt)
    response_text = response.text.strip().replace("```", "").replace("json", "")
    return json.loads(response_text)


email_content="""
**Rhea Wagas [rhea.w@vivainsurance.ae](mailto:rhea.w@vivainsurance.ae)**
**To:** Sabina N; Quotation Healthx
**Cc:** Suzy Jimmy George [suzy.g@vivainsurance.ae](mailto:suzy.g@vivainsurance.ae); Rozemin Apple Santiago [rozemin.s@vivainsurance.ae](mailto:rozemin.s@vivainsurance.ae); GROUP EB [viva-eb@vivainsurance.ae](mailto:viva-eb@vivainsurance.ae)
**Date:** Fri 25 Apr 2025 10:30 AM
**Subject:** \[High Importance]

📎 **Attachments:**

* Census List - Viva.xlsx
* TOB-CAT A.pdf
* TOB-CAT B.pdf
* TOB-CAT C.pdf

---

**Hi Team,**

Good morning

Can you please share with us your best terms for the group?

**Existing with Methaq**
**Expiry Date:** 31/05/2025
**Target Rate:** AED 250,000

---

**Attachments:**

* Census List
* TOB – benefits should be as per the TOB
* TL

---

**Required Hospitals:**

* **Category A:** American Hospital, Dr. Sulaiman Al Habib Hospital, Al Zahra Hospital, Medeor Hospital, Medcare Group, Zulekha Hospital, Prime Hospital, Garhoud Private Hospital and Mediclinic Hospitals – **GN level of Network**
* **Category B:** Garhoud Private Hospital, Prime Hospital, Aster Group, NMC Group, Medeor Hospital, Medcare Group, Zulekha Hospital, Al Zahra Group
* **Category C:** Aster Group, NMC Group, Medeor Hospital, Medcare Hospital - Opposite Al Safa Branch (only)

---

Looking forward to receiving your terms at the earliest.


"""

print(extract_structured_data_from_email(email_content))