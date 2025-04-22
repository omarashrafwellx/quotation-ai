import pandas as pd
import os
import datetime
import re

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
                    else:
                        found_column = column
                        break
        
        # Store the found column if not a date (dates are handled above)
        if found_column and col_type != 'date_columns':
            found_columns[col_type] = found_column
            
    return found_columns

def find_dataframe_with_columns(file_path, column_patterns):
    """
    Tries to find the best DataFrame from a file that contains the specified columns.
    
    Args:
        file_path (str): Path to the CSV or Excel file
        column_patterns (dict): Dictionary with column types as keys and patterns as values
        
    Returns:
        tuple: (DataFrame, header_row, found_columns)
    """
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
    """Standardize relation values"""
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
    """Standardize gender values"""
    if pd.isna(value):
        return value
    
    value = str(value).lower().strip()
    
    if value in ['male', 'm']:
        return 'M'
    elif value in ['female', 'f']:
        return 'F'
    
    return value  # Return original if not matching

def standardize_date(value):
    """Standardize date values to Excel serial numbers"""
    if pd.isna(value):
        return value

    value = str(value).strip()

    # Remove time component if present
    value = re.sub(r'\s+\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?', '', value, flags=re.IGNORECASE)

    try:
        # Attempt to parse the date
        date_obj = pd.to_datetime(value, dayfirst=True, errors='coerce')
        if pd.isna(date_obj):
            return value  # Return original if parsing fails

        # Convert to Excel serial number
        excel_start_date = datetime.datetime(1899, 12, 30)
        delta = date_obj - excel_start_date
        serial_number = delta.days + delta.seconds / 86400
        return round(serial_number, 2)  # Rounded to 2 decimal places
    except Exception:
        return value  # Return original if any error occurs

def standardize_data(file_path):
    """
    Reads a CSV or Excel file, and standardizes:
    1. Relation column values (if exists)
    2. Date formats (if date columns exist)
    3. Gender values (Male->M, Female->F) (if gender column exists)
    
    Args:
        file_path (str): Path to the input CSV or Excel file
    
    Returns:
        pd.DataFrame: DataFrame with standardized values
        dict: Information about changes made
    """
    # Define column patterns to search for
    column_patterns = {
    'relation_column': re.compile(r'relation|relationship|dependent|status|role|type', re.IGNORECASE),
    'gender_column': re.compile(r'gender|sex|male\/female', re.IGNORECASE),
    'date_columns': re.compile(r'date|birth|dob|born|age', re.IGNORECASE)
}
    
    # Find dataframe and columns
    df, header_row, found_columns = find_dataframe_with_columns(file_path, column_patterns)
    
    # Extract found columns
    relation_column = found_columns.get('relation_column')
    gender_column = found_columns.get('gender_column')
    date_columns = found_columns.get('date_columns', [])
    
    # Prepare changes info
    changes_info = {
        'relation_column': relation_column,
        'gender_column': gender_column,
        'date_columns': date_columns
    }
    
    # 1. Standardize relation values if found
    if relation_column:
        df[relation_column] = df[relation_column].apply(standardize_relation)
    
    # 2. Standardize gender values if found
    if gender_column:
        df[gender_column] = df[gender_column].apply(standardize_gender)
    
    # 3. Standardize date formats
    for date_col in date_columns:
        df[date_col] = df[date_col].apply(standardize_date)
    
    return df, changes_info

def main():    
    input_file = "MemberCensusDataTemplate.xls"
    
    base_name, ext = os.path.splitext(input_file)
    output_file = f"{base_name}_standardized{ext}"
    
    try:
        # Process the file
        df, changes_info = standardize_data(input_file)
        
        # Display info about what was processed
        print(f"File processed: {input_file}")
        
        # Display relation column changes if applicable
        relation_column = changes_info.get('relation_column')
        if relation_column:
            print(f"\nRelation column: '{relation_column}'")
            print("Sample of standardized relation values:")
            sample = df[relation_column].head(5)
            for i, val in enumerate(sample):
                print(f"  {i+1}. {val}")
        else:
            print("\nNo relation column found. Skipping relation standardization.")
        
        # Display gender column changes if applicable
        gender_column = changes_info.get('gender_column')
        if gender_column:
            print(f"\nGender column: '{gender_column}'")
            print("Sample of standardized gender values:")
            sample = df[gender_column].head(5)
            for i, val in enumerate(sample):
                print(f"  {i+1}. {val}")
        else:
            print("\nNo gender column found. Skipping gender standardization.")
        
        # Display date column changes
        date_columns = changes_info.get('date_columns', [])
        if date_columns:
            # print(f"\nStandardized Date columns: {', '.join(f"'{c}'" for c in date_columns)}")
            for date_col in date_columns[:1]:  # Show sample for first date column only
                print(f"Sample of standardized dates from '{date_col}':")
                sample = df[date_col].head(5)
                for i, val in enumerate(sample):
                    print(f"  {i+1}. {val}")
        else:
            print("\nNo date columns found. Skipping date standardization.")
        
        # Save the result
        if output_file.endswith('.csv'):
            df.to_csv(output_file, index=False)
        else:
            # For Excel files, maintain the original formatting and structure
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Standardized')
        
        print(f"\nSuccessfully standardized data")
        print(f"Output saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()