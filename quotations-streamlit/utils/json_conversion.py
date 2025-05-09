import pandas as pd
import json

def dataframe_to_json(df):
    """
    Convert a DataFrame to JSON in the specified format.
    
    Args:
        df: DataFrame with standardized census data
        
    Returns:
        dict: JSON-ready dictionary with census data grouped by category
    """
    # Make a copy to avoid modifying the original DataFrame
    df_copy = df.copy()
    
    # Convert gender to lowercase
    if 'gender' in df_copy.columns:
        df_copy['gender'] = df_copy['gender'].str.lower()
    
    # Initialize result dictionary
    result = {"census_list": {}}
    
    # For numeric columns, convert integers stored as floats to actual integers
    for col in ['age', 'dob']:
        if col in df_copy.columns:
            mask = df_copy[col].notna() & df_copy[col].apply(
                lambda x: float(x).is_integer() if isinstance(x, (int, float)) else False
            )
            df_copy.loc[mask, col] = df_copy.loc[mask, col].astype(int)
    
    # Check if category column exists
    if 'category' in df_copy.columns:
        # Group by category and convert to dictionary
        for category, group in df_copy.groupby('category'):
            # Convert to records (list of dictionaries) and replace NaN with appropriate values
            records = group.replace({pd.NA: None, pd.NaT: None}).to_dict(orient='records')
            result["census_list"][category] = records
    else:
        # If no category exists, put all records in a single "all" category
        records = df_copy.replace({pd.NA: None, pd.NaT: None}).to_dict(orient='records')
        result["census_list"]["all"] = records
    
    return result

def to_json_string(df):
    """
    Convert DataFrame to JSON string in the specified format.
    
    Args:
        df: DataFrame with standardized census data
        
    Returns:
        str: JSON string with census data grouped by category
    """
    json_data = dataframe_to_json(df)
    return json.dumps(json_data, indent=4, ensure_ascii=False)