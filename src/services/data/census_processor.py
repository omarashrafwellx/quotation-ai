"""
Census file processing and standardization.
Refactored from replace_entities.py
"""

import pandas as pd
import os
import re
from typing import Dict, Any
from src.core.exceptions import DocumentProcessingError
import datetime



def find_columns(df, column_patterns):
    """
    Find columns in DataFrame based on patterns.
    
    Args:
        df (pd.DataFrame): DataFrame to search in
        column_patterns (dict): Dictionary with key as column type and value as regex pattern or list of keywords
        
    Returns:
        dict: Dictionary with column types as keys and found column names as values
    """
    found_columns = {}
    
    for col_type, pattern in column_patterns.items():
        found_column = None
        
        # If pattern is a list (keywords), search for any match
        if isinstance(pattern, list):
            for column in df.columns:
                if isinstance(column, str):
                    column_lower = column.lower()
                    if any(keyword in column_lower for keyword in pattern):
                        found_column = column
                        break
        # If pattern is a regex pattern
        elif isinstance(pattern, re.Pattern):
            for column in df.columns:
                if isinstance(column, str) and pattern.search(str(column)):
                    if col_type == 'date_columns':
                        if 'date_columns' not in found_columns:
                            found_columns['date_columns'] = []
                        found_columns['date_columns'].append(column)
                    elif col_type == 'name_columns':
                        if 'name_columns' not in found_columns:
                            found_columns['name_columns'] = []
                        found_columns['name_columns'].append(column)
                    else:
                        found_column = column
                        break
        
        # Store the found column if not a date or name (dates and names are handled above)
        if found_column and col_type not in ['date_columns', 'name_columns']:
            found_columns[col_type] = found_column
            
    return found_columns

def find_dataframe_with_columns(file_path, column_patterns):
    file_extension = os.path.splitext(file_path)[1].lower()
    df = None
    header_row = 0
    found_columns = {}
    
    if file_extension == '.csv':
        # Try with different header positions
        for i in range(5):  # Try first 5 rows as potential headers
            try:
                temp_df = pd.read_csv(file_path, header=i)
                # Look for all columns using patterns
                temp_found = find_columns(temp_df, column_patterns)
                
                # If we found any of the columns we're looking for, use this dataframe
                if temp_found:
                    df = temp_df
                    header_row = i
                    found_columns = temp_found
                    break
                # If we haven't found a dataframe yet, use this one as a fallback
                elif df is None:
                    df = temp_df
                    header_row = i
            except Exception:
                continue
        
        # If no dataframe found, try with no header
        if df is None:
            df = pd.read_csv(file_path, header=None)
            
    elif file_extension in ['.xlsx', '.xls']:
        # Try with different header positions
        for i in range(5):  # Try first 5 rows as potential headers
            try:
                temp_df = pd.read_excel(file_path, header=i)
                # Look for all columns using patterns
                temp_found = find_columns(temp_df, column_patterns)
                
                # If we found any of the columns we're looking for, use this dataframe
                if temp_found:
                    df = temp_df
                    header_row = i
                    found_columns = temp_found
                    break
                # If we haven't found a dataframe yet, use this one as a fallback
                elif df is None:
                    df = temp_df
                    header_row = i
            except Exception:
                continue
        
        # If still no success, try reading all sheets
        if df is None:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                for i in range(5):
                    try:
                        temp_df = pd.read_excel(file_path, sheet_name=sheet_name, header=i)
                        
                        # First check if this looks like valid data
                        if len(temp_df.columns) > 1:
                            # Look for all columns using patterns
                            temp_found = find_columns(temp_df, column_patterns)
                            
                            # If we found any of the columns we're looking for, use this dataframe
                            if temp_found:
                                df = temp_df
                                header_row = i
                                found_columns = temp_found
                                break
                            # If we haven't found a dataframe yet, use this one as a fallback
                            elif df is None:
                                df = temp_df
                                header_row = i
                    except Exception:
                        continue
                if df is not None:
                    break
    
    if df is None:
        raise ValueError(f"Could not read {file_path} with any header configuration.")
        
    # If we found a dataframe but haven't found all columns, search again
    if df is not None and len(found_columns) < len(column_patterns):
        found_columns = find_columns(df, column_patterns)
    
    return df, header_row, found_columns

def standardize_relation(value):
    if pd.isna(value):
        return value
    
    value = str(value).lower().strip()
    
    # Handle Employee/Subscriber -> Principal
    if value in ['employee', 'subscriber','self','owner','staff']:
        return 'Principal'
    
    # Handle Son/Daughter -> Child
    if value in ['son', 'daughter']:
        return 'Child'
    
    # Handle Wife/Husband -> Spouse
    if value in ['wife', 'husband','partner']:
        return 'Spouse'
    
    # Return original value if no match
    return value.capitalize()  # Capitalize first letter for consistency

def standardize_gender(value):
    """Standardize gender values to consistent format"""
    if pd.isna(value):
        return 'Unknown'
    
    value = str(value).lower().strip()
    
    if value in ['male', 'm']:
        return 'M'
    elif value in ['female', 'f']:
        return 'F'
    
    return value.capitalize()  # Return original if not matching, but capitalized

def get_raw_gender(value):
    """Get raw gender value (M/F)"""
    if pd.isna(value):
        return ''
    
    value = str(value).lower().strip()
    
    if value in ['male', 'm']:
        return 'M'
    elif value in ['female', 'f']:
        return 'F'
    
    return value  # Return original if not matching

def standardize_marital_status(value):
    """Standardize marital status values"""
    if pd.isna(value):
        return 'unknown'
    
    value = str(value).lower().strip()
    
    if value in ['married', 'marriage', 'spouse', 'm', 'yes', 'y']:
        return 'married'
    elif value in ['single', 'unmarried', 'not married', 'n', 'no']:
        return 'unmarried'
    
    return value  # Return original if not matching, keep lowercase



def standardize_date(value):
    """Standardize date values to Excel serial numbers"""
    if pd.isna(value):
        return value

    value = str(value).strip()

    # Remove time component if present
    value = re.sub(r'\s+\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?', '', value, flags=re.IGNORECASE)

    try:
        # Attempt to parse the date
        date_obj = pd.to_datetime(value, dayfirst=False, errors='coerce')
        if pd.isna(date_obj):
            return value  # Return original if parsing fails

        # Convert to Excel serial number
        excel_start_date = datetime.datetime(1899, 12, 30)
        delta = date_obj - excel_start_date
        serial_number = delta.days + delta.seconds / 86400
        return round(serial_number, 2)  # Rounded to 2 decimal places
    except Exception:
        return value  # Return original if any error occurs


def combine_names(df, name_columns):
    """Combine multiple name columns into a single full name"""
    if not name_columns:
        return pd.Series([''] * len(df))
    
    # Filter out columns that don't exist in the dataframe
    valid_columns = [col for col in name_columns if col in df.columns]
    
    if not valid_columns:
        return pd.Series([''] * len(df))
    
    # Start with the first valid column
    combined_names = df[valid_columns[0]].astype(str).fillna('')
    
    # Add remaining columns with a space in between
    for col in valid_columns[1:]:
        # Only add a space if both values are non-empty
        combined_names = combined_names.str.strip() + ' ' + df[col].astype(str).fillna('').str.strip()
        combined_names = combined_names.str.strip()
    
    # Clean up extra spaces
    combined_names = combined_names.str.replace(r'\s+', ' ', regex=True).str.strip()
    
    return combined_names

def get_raw_marital_status(value):
    """Get raw marital status value"""
    if pd.isna(value):
        return ''
    
    value = str(value).lower().strip()
    
    if value in ['married', 'marriage', 'spouse', 'm', 'yes', 'y']:
        return 'Married'
    elif value in ['single', 'unmarried', 'not married', 'n', 'no']:
        return 'Unmarried'
    
    return value.capitalize()  # Return original if not matching, but capitalized

def standardize_data(file_path):
    """
    Standardize and rename columns in a census file.
    
    Args:
        file: Streamlit uploaded file
        
    Returns:
        tuple: (standardized_df, changes_info)
    """
    # Define column patterns to search for
    column_patterns = {
        'relation_column': re.compile(r'relation|relationship|dependent|role|type', re.IGNORECASE),
        'gender_column': re.compile(r'gender|sex|male\/female', re.IGNORECASE),
        'age_column': re.compile(r'^age$|^ages$|old', re.IGNORECASE),
        'dob_column': re.compile(r'birth|dob|born|birthday|date of birth', re.IGNORECASE),
        'marital_column': re.compile(r'marital|married|marriage|spouse|maritarial|status', re.IGNORECASE),
        'name_columns': re.compile(r'name|first|last|fname|lname|surname', re.IGNORECASE),
        'date_columns': re.compile(r'date', re.IGNORECASE),
        'category_column': re.compile(r'category|class|tier', re.IGNORECASE)
    }
    
    # Find dataframe and columns
    df, header_row, found_columns = find_dataframe_with_columns(file_path, column_patterns)
    
    print(found_columns)
    # Extract found columns
    relation_column = found_columns.get('relation_column')
    gender_column = found_columns.get('gender_column')
    age_column = found_columns.get('age_column')
    dob_column = found_columns.get('dob_column')
    marital_column = found_columns.get('marital_column')
    name_columns = found_columns.get('name_columns', [])
    date_columns = found_columns.get('date_columns', [])
    category_column = found_columns.get('category_column')
    
    # Create a new DataFrame with the fixed column names
    standardized_df = pd.DataFrame()
    
    # 1. Extract and standardize age
    # age_values = extract_age(df, dob_column, age_column)
    # standardized_df['age'] = age_values
    
    # 1. If age column exists, ensure that it's values are integers
    for col in date_columns:
        if col in df.columns:
            # Remove non-numeric characters if necessary, then convert to int
            standardized_df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # 2. Standardize date of birth
    if dob_column and dob_column in df.columns:
        standardized_df['Date of Birth (DD/MM/YYYY)'] = df[dob_column].apply(standardize_date)
    else:
        standardized_df['Date of Birth (DD/MM/YYYY)'] = ''
    
    # 3. Combine names
    standardized_df['First Name'] = combine_names(df, name_columns)
    
    # 4. Standardize gender
    if gender_column and gender_column in df.columns:
        standardized_df['gender'] = df[gender_column].apply(standardize_gender)
        standardized_df['rawGender'] = df[gender_column].apply(get_raw_gender)
    else:
        standardized_df['gender'] = 'Unknown'
        standardized_df['rawGender'] = ''
    
    if category_column and category_column in df.columns:
        standardized_df['category'] = df[category_column]
    else:
        # Fill all entries with "A"
        standardized_df['category'] = pd.Series(['A'] * len(df))
    
    # 6. Set fixed relation value
    # standardized_df['relationType'] = 'primary'  # As requested, this is fixed
    
    # 7. Standardize relation type
    if relation_column and relation_column in df.columns:
        standardized_df['relation'] = df[relation_column].apply(standardize_relation)
    else:
        standardized_df['relation'] = 'Unknown'
    
    # 8. Standardize marital status
    if marital_column and marital_column in df.columns:
        standardized_df['Marital Status'] = df[marital_column].apply(standardize_marital_status)
        standardized_df['rawMarital_status'] = df[marital_column].apply(get_raw_marital_status)
    else:
        standardized_df['Marital Status'] = 'unknown'
        standardized_df['rawMarital_status'] = ''
    
    # Prepare changes info to return to the user
    changes_info = {
        'relation_column':relation_column,
        'gender_column':gender_column,
        'date_columns': date_columns,
        'age_column': age_column,
        'dob_column': dob_column,
        'marital_column': marital_column,
        'name_columns': name_columns,
        'category_column': category_column,
        
    }
    
    return standardized_df, changes_info

def standardize_census_file(input_file_path: str) -> Dict[str, Any]:
    """
    Standardize census file and return result.
    
    Args:
        input_file_path: Path to the input census file
        
    Returns:
        Dictionary with success status and output file path
        
    Raises:
        DocumentProcessingError: If processing fails
    """
    try:
        base_name, ext = os.path.splitext(input_file_path)
        output_file = f"{base_name}_standardized{ext}"
        
        # Process the file
        df, changes_info = standardize_data(input_file_path)
        
        # Save the result
        if output_file.endswith('.csv'):
            df.to_csv(output_file, index=False)
        else:
            # For Excel files, maintain the original formatting and structure
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Standardized')
        
        print(f"\nSuccessfully standardized data")
        print(f"Output saved to: {output_file}")
        return {"success":True, "output_file_path":output_file}
        
    except Exception as e:
        raise DocumentProcessingError(f"Failed to standardize census file: {e}")