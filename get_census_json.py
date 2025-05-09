import pandas as pd
import json

def excel_to_json(excel_file, output_json_file=None):
    # Read the Excel file
    df = pd.read_excel(excel_file)
    
    # Convert gender to lowercase
    if 'gender' in df.columns:
        df['gender'] = df['gender'].str.lower()
    
    # Initialize result dictionary
    result = {"census_list": {}}
    
    # For numeric columns, convert integers stored as floats to actual integers
    for col in ['age', 'dob']:
        if col in df.columns:
            mask = df[col].notna() & df[col].apply(lambda x: float(x).is_integer() if isinstance(x, (int, float)) else False)
            df.loc[mask, col] = df.loc[mask, col].astype(int)
    
    # Group by category and convert to dictionary
    for category, group in df.groupby('category'):
        # Convert to records (list of dictionaries) and replace NaN with appropriate values
        records = group.replace({pd.NA: None, pd.NaT: None}).to_dict(orient='records')
        result["census_list"][category] = records
    
    # Save to JSON file if output path is provided
    if output_json_file:
        with open(output_json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"JSON data saved to {output_json_file}")
    
    return result

if __name__ == "__main__":
    input_excel = "MemberCensusDataTemplate_standardized_v2.xlsx"
    output_json = "MemberCensusDataTemplate_categories.json"
    
    try:
        json_data = excel_to_json(input_excel, output_json)
        print("JSON file created successfully!")
        
        # Display total counts by category
        print("\nRecords count by category:")
        for category, records in json_data["census_list"].items():
            print(f"  {category}: {len(records)} records")
            
    except Exception as e:
        print(f"Error: {e}")