import xlwings as xw

json_data = {
  "company_name": "wellx",
  "AUH_POLICY":"No",
  "broker_details": {
    "broker_name": "Assist Us",
    "relationship_manager": "Sabina N",
    "broker_fee": None
  },
  "benefits": {
    "annual_medical": "AED 5,000,000",
    "territorial_cover": "World wide excluding US",
    "deductible_for_consultation": "20% Max AED 50",
    "ip_room_type": "Standard Private Room",
    "maternity": "AED 36,700 (Inpatient Covered, Outpatient NIL Coinsurance/Deductible)",
    "dental": "AED 3,670 (0% Coinsurance, except 50% for Orthodontics)",
    "optical": "AED 2,750 (Nil Coinsurance)",
    "diagnostic_investigation_op_copay": "Nil",
    "pharmacy_copay": "Nil",
    "pharmacy_limit": "Nil",
    "benefits_company_name": "GIG GULF"
  },
  "census_list": {
    "B":[
             {
        "age": 41.4,
        "dob": 30671.0,
        "name": "Helena Zulfikhar",
        "gender": "female",
        "rawGender": "F",
        "category": "B",
        "relation": "primary",
        "relationType": "Spouse",
        "marital_status": "married",
        "rawMarital_status": "Married"
      }
      
      ],
    
    "A": [
      {
        "age": 30.6,
        "dob": 34587.0,
        "name": "Shilpi Kamleshbhai Shethwala",
        "gender": "female",
        "rawGender": "F",
        "category": "A",
        "relation": "primary",
        "relationType": "Principal",
        "marital_status": "married",
        "rawMarital_status": "Married"
      },
      {
        "age": 37.4,
        "dob": 32131.0,
        "name": "Deepak Joe Mathew",
        "gender": "male",
        "rawGender": "M",
        "category": "A",
        "relation": "primary",
        "relationType": "Principal",
        "marital_status": "married",
        "rawMarital_status": "Married"
      }
    ]
  }
}

file_path = "files/excel/V4 Opt1 RGA Tool v4.5 - QHX-2503535 - Alshaiba Advocates & Legal Consultants 19.3.25.xlsm"
output_file_path = "Filled_RGA_Tool_with_Members.xlsx"

app = xw.App(visible=True)
wb = app.books.open(file_path)

ws_info = wb.sheets['General Information']

ws_info.range('D8').value = json_data['company_name']
# ws_info.range('D10').value = "Fresh Scheme"
ws_info.range('D42').value = json_data['broker_details']['broker_name']
ws_info.range('D20').value = json_data["AUH_POLICY"]
ws_info.range("D22").value="7"

# 3. Fill Benefit Selection
ws_benefits = wb.sheets['Benefit Selection - Group']
ws_benefits.range('B9').value = "Dubai"
# Coverage percentage selections
ws_benefits.range('B62').value = "10%"  
ws_benefits.range('G62').value = "10%" 


# Activate Member Data sheet
ws_member = wb.sheets['Member Data']

# 1. Read headers from row 5
header_row = 5
headers = ws_member.range(f"A{header_row}").expand('right').value

# 2. Map headers to column numbers
header_map = {}
for idx, header in enumerate(headers):
    if header:
        header_map[header.strip().lower()] = idx + 1  # Excel is 1-indexed

# 3. Identify target columns
dob_col = header_map.get('date of birth')
gender_col = header_map.get('gender')
benefits_cat_col = header_map.get("benefit 'category'")
relationship_col = header_map.get('relationship')
name_col = header_map.get('first name / full name')

if not all([dob_col, gender_col, benefits_cat_col, relationship_col, name_col]):
    raise Exception("One or more required fields not found in header row.")

# 4. Clear old member data (below the header row)
# Select all rows starting from start_row
start_row = header_row + 1
used_range = ws_member.range(f"A{start_row}").expand('table')

used_range.clear_contents()

# 5. Fill fresh data from all categories
row = start_row

for category_members in json_data['census_list'].values():
    for member in category_members:
        ws_member.range((row, dob_col)).value = member['dob']  # Excel serial DOB
        ws_member.range((row, gender_col)).value = member['rawGender']  # 'M' or 'F'
        ws_member.range((row, benefits_cat_col)).value = member['category']  # 'A', 'B', etc.
        ws_member.range((row, relationship_col)).value = member['relationType']  # Principal, Dependent, etc.
        ws_member.range((row, name_col)).value = member['name']  # Full name
        row += 1  # Move to next row after each member
        
wb.save(output_file_path)
wb.close()
app.quit()

print(f"✅ Successfully cleared old data and filled new Member Data for all categories into {output_file_path}")