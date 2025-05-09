import pandas as pd
import os
import re
import io

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

import pandas as pd
import io
import os

def find_dataframe_with_columns(file, column_patterns):
    """
    Tries to find the best DataFrame from a file that contains the specified columns.
    
    Args:
        file (file-like object): File upload from Streamlit
        column_patterns (dict): Dictionary with column types as keys and patterns as values
        
    Returns:
        tuple: (DataFrame, header_row, found_columns)
    """
    # Get file extension
    file_extension = os.path.splitext(file.name)[1].lower()
    
    # Read the file content
    file_content = file.read()
    file.seek(0)  # Reset file pointer
    
    df = None
    header_row = None
    found_columns = {}
    
    if file_extension in ['.csv', '.xlsx', '.xls', '.xlsm']:
        # Read raw without header
        if file_extension == '.csv':
            raw_df = pd.read_csv(io.BytesIO(file_content), header=None, dtype=str)
        elif file_extension == '.xls':
            raw_df = pd.read_excel(io.BytesIO(file_content), header=None, dtype=str, engine="xlrd")
        else:
            raw_df = pd.read_excel(io.BytesIO(file_content), header=None, dtype=str, engine="openpyxl")
        
        # Search for header row by matching column patterns
        for i in range(len(raw_df)):
            row = raw_df.iloc[i]
            matches = 0
            for col in row:
                if isinstance(col, str):
                    col_lower = col.lower()
                    if any(
                        any(keyword in col_lower for keyword in keywords)
                        for keywords in column_patterns.values() if isinstance(keywords, list)
                    ):
                        matches += 1
                    elif any(
                        isinstance(keywords, re.Pattern) and keywords.search(col)
                        for keywords in column_patterns.values()
                    ):
                        matches += 1
            if matches >= 2:  # Good enough match: found likely header
                header_row = i
                break
        
        if header_row is not None:
            # Re-read the file properly with detected header
            if file_extension == '.csv':
                df = pd.read_csv(io.BytesIO(file_content), header=header_row, dtype=str)
            elif file_extension == '.xls':
                df = pd.read_excel(io.BytesIO(file_content), header=header_row, dtype=str, engine="xlrd")
            else:
                df = pd.read_excel(io.BytesIO(file_content), header=header_row, dtype=str, engine="openpyxl")
        else:
            raise ValueError("Could not automatically find a valid header row.")
        
        found_columns = find_columns(df, column_patterns)

        # If missing some columns, re-scan
        if len(found_columns) < len(column_patterns):
            found_columns = find_columns(df, column_patterns)

    else:
        raise ValueError(f"Unsupported file extension: {file_extension}")
    
    if df is None:
        raise ValueError(f"Could not read {file.name} with any header configuration.")
    
    return df, header_row, found_columns
