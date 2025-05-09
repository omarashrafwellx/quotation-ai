import pandas as pd
import io
import os
import datetime
import re
import numpy as np
from .file_processing import find_dataframe_with_columns, find_columns
from .download_utils import to_excel_bytes

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
        return 'Male'
    elif value in ['female', 'f']:
        return 'Female'
    
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

def extract_age(df, dob_column=None, age_column=None, current_date=None):
    """Extract age from either direct age column or calculate from DOB"""
    if current_date is None:
        current_date = datetime.datetime.now()
    
    if age_column and age_column in df.columns:
        # Try to convert age column to numeric
        return pd.to_numeric(df[age_column], errors='coerce')
    
    elif dob_column and dob_column in df.columns:
        # Calculate age from date of birth
        try:
            # Convert DOB to datetime
            dob = pd.to_datetime(df[dob_column], errors='coerce')
            
            # If many NaT values, try different formats
            if dob.isna().sum() > len(df) / 2:
                # Try European format (DD.MM.YYYY)
                dob = pd.to_datetime(df[dob_column], format='%d.%m.%Y', errors='coerce')
                
                # If still many NaT values, try other common formats
                if dob.isna().sum() > len(df) / 2:
                    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                        temp_dob = pd.to_datetime(df[dob_column], format=fmt, errors='coerce')
                        if temp_dob.isna().sum() < dob.isna().sum():
                            dob = temp_dob
                            break
            
            # Calculate age in years
            age = ((current_date - dob).dt.days / 365.25).round(1)
            return age
            
        except Exception as e:
            print(f"Error calculating age from date of birth: {e}")
            return pd.Series([np.nan] * len(df))
    
    return pd.Series([np.nan] * len(df))

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

def standardize_data(file):
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
    df, header_row, found_columns = find_dataframe_with_columns(file, column_patterns)
    
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
    standardized_df['relationType'] = 'primary'  # As requested, this is fixed
    
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
        'relation_column': "relationType",
        'gender_column': "rawGender",
        'date_columns': date_columns,
        'age_column': age_column,
        'dob_column': dob_column,
        'marital_column': marital_column,
        'name_columns': name_columns,
        'category_column': category_column,
        
    }
    
    return standardized_df, changes_info

def analyze_census(df):
    """
    Analyzes census data and calculates statistics.
    
    Args:
        df: DataFrame with standardized census data
        
    Returns:
        dict: Dictionary containing census statistics
    """
    # Census count (total records)
    census_count = len(df)
    
    # Extract age values
    age_values = df['age'] if 'age' in df.columns else pd.Series([np.nan] * len(df))
    
    # Calculate statistics
    # 1. Over 64 years
    over_64_count = sum(age_values > 64)
    pct_elderly = round((over_64_count / census_count) * 100, 1) if census_count > 0 else 0
    
    # 2. Gender breakdown
    gender_stats = {'M': 0, 'F': 0}
    gender_pct = {'M': 0, 'F': 0}
    
    # Count gender values if rawGender column exists
    if 'rawGender' in df.columns:
        gender_stats['M'] = sum(df['rawGender'] == 'M')
        gender_stats['F'] = sum(df['rawGender'] == 'F')
    
    # Calculate percentages
    gender_pct['M'] = round((gender_stats['M'] / census_count) * 100, 1) if census_count > 0 else 0
    gender_pct['F'] = round((gender_stats['F'] / census_count) * 100, 1) if census_count > 0 else 0
    
    # 3. Married F (<45 y.o.)
    married_f_under_45 = 0
    pct_married_f_under_45 = 0
    
    # Calculate married females under 45 if required columns exist
    if 'rawGender' in df.columns and 'Marital Status' in df.columns and 'age' in df.columns:
        married_f_mask = (df['rawGender'] == 'F') & (df['Marital Status'] == 'married') & (df['age'] < 45)
        married_f_under_45 = sum(married_f_mask)
        pct_married_f_under_45 = round((married_f_under_45 / gender_stats['F']) * 100, 1) if gender_stats['F'] > 0 else 0
    
    # 4. Average Adult Age
    adult_mask = age_values >= 18
    avg_adult_age = round(age_values[adult_mask].mean(), 1) if sum(adult_mask) > 0 else 0
    
    # 5. Principal/Dependents counts
    principal_count = 0
    dependent_count = 0
    
    # Calculate principal and dependent counts if relationType column exists
    if 'relationType' in df.columns:
        principal_count = sum(df['relationType'] == 'Principal')
        dependent_count = sum((df['relationType'] != 'Principal') & (df['relationType'] != 'Unknown'))
    
    # Calculate percentages
    pct_principal = round((principal_count / census_count) * 100, 1) if census_count > 0 else 0
    pct_dependent = round((dependent_count / census_count) * 100, 1) if census_count > 0 else 0
    
    # Compile results
    analysis_results = {
        'census_count': census_count,
        'over_64_count': over_64_count,
        'pct_elderly': pct_elderly,
        'male_count': gender_stats['M'],
        'male_pct': gender_pct['M'],
        'female_count': gender_stats['F'],
        'female_pct': gender_pct['F'],
        'married_f_under_45': married_f_under_45,
        'pct_married_f_under_45': pct_married_f_under_45,
        'avg_adult_age': avg_adult_age,
        'principal_count': principal_count,
        'principal_pct': pct_principal,
        'dependent_count': dependent_count,
        'dependent_pct': pct_dependent
    }
    
    return analysis_results

def create_excel_analysis_bytes(df):
    """
    Creates an Excel analysis report for the standardized data.
    
    Args:
        df: DataFrame with standardized census data
        
    Returns:
        bytes: Excel file as bytes
    """
    # Generate analysis results
    results = analyze_census(df)
    
    # Create a DataFrame for the report
    report_data = {
        'Census Analysis': [
            'Census count',
            'Over 64 years',
            '% Elderly',
            '',
            'Census Analysis',
            'Census count',
            'M',
            'F',
            'Married F (<45 y.o.)',
            'Ave. Adult Age',
            '',
            'Principal',
            'Dependents'
        ],
        'Value': [
            results['census_count'],
            results['over_64_count'],
            f"{results['pct_elderly']}%",
            '',
            '',
            results['census_count'],
            results['male_count'],
            results['female_count'],
            results['married_f_under_45'],
            results['avg_adult_age'],
            '',
            results['principal_count'],
            results['dependent_count']
        ],
        'Percentage': [
            '',
            '',
            '',
            '',
            '',
            '',
            f"{results['male_pct']}%",
            f"{results['female_pct']}%",
            f"{results['pct_married_f_under_45']}%",
            '',
            '',
            f"{results['principal_pct']}%",
            f"{results['dependent_pct']}%"
        ]
    }
    
    # Create DataFrame
    report_df = pd.DataFrame(report_data)
    
    # Create Excel bytes
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        report_df.to_excel(writer, index=False, sheet_name='Census Analysis')
        df.to_excel(writer, index=False, sheet_name='Standardized')
    
    output.seek(0)
    return output.getvalue()