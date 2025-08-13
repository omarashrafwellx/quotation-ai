"""
Data validation services.
Extracted from process_email.py
"""

from typing import List, Dict, Any, Tuple, Optional
from src.services.data.census_processor import standardize_census_file, find_columns
from src.core.exceptions import ValidationError
import re
import os
import pandas as pd

async def get_excel_categories(file_path):
    """Extract unique categories from Excel/CSV file using the same logic as replace_entities.py"""
    def _get_categories():
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Use the same column finding logic as replace_entities.py
            column_patterns = {
                'category_column': re.compile(r'category|class|tier', re.IGNORECASE)
            }
            
            # Try different header positions like in replace_entities.py
            df = None
            found_columns = {}
            
            if file_extension == '.csv':
                for i in range(5):  # Try first 5 rows as potential headers
                    try:
                        temp_df = pd.read_csv(file_path, header=i)
                        temp_found = find_columns(temp_df, column_patterns)
                        if temp_found:
                            df = temp_df
                            found_columns = temp_found
                            break
                        elif df is None:
                            df = temp_df
                    except Exception:
                        continue
                if df is None:
                    df = pd.read_csv(file_path, header=None)
                    
            elif file_extension in ['.xlsx', '.xls', '.xlsm']:
                for i in range(5):
                    try:
                        temp_df = pd.read_excel(file_path, header=i)
                        temp_found = find_columns(temp_df, column_patterns)
                        if temp_found:
                            df = temp_df
                            found_columns = temp_found
                            break
                        elif df is None:
                            df = temp_df
                    except Exception:
                        continue
                        
                # Try all sheets if still no success
                if df is None:
                    excel_file = pd.ExcelFile(file_path)
                    for sheet_name in excel_file.sheet_names:
                        for i in range(5):
                            try:
                                temp_df = pd.read_excel(file_path, sheet_name=sheet_name, header=i)
                                if len(temp_df.columns) > 1:
                                    temp_found = find_columns(temp_df, column_patterns)
                                    if temp_found:
                                        df = temp_df
                                        found_columns = temp_found
                                        break
                                    elif df is None:
                                        df = temp_df
                            except Exception:
                                continue
                        if df is not None:
                            break
            else:
                return ["A"]  # Default for unsupported file types
            
            if df is None:
                print(f"⚠️ Could not read {file_path}")
                return ["A"]
            
            # Get category column from found columns
            category_column = found_columns.get('category_column')
            
            if not category_column:
                print(f"⚠️ No category column found in {file_path}, defaulting to ['A']")
                return ["A"]  # Default to Category A like in replace_entities.py
            
            # Get unique categories (excluding NaN/null values)
            unique_categories = df[category_column].dropna().unique().tolist()
            unique_categories = [str(cat).strip() for cat in unique_categories if str(cat).strip()]
            
            if not unique_categories:
                print(f"⚠️ Category column found but no valid categories in {file_path}, defaulting to ['A']")
                return ["A"]
            
            print(f"📊 Found categories in Excel: {unique_categories}")
            return unique_categories
            
        except Exception as e:
            print(f"❌ Error reading categories from {file_path}: {e}, defaulting to ['A']")
            return ["A"]  # Default to Category A on any error
    
    return _get_categories()

async def validate_category_consistency(tob_count: int, excel_categories: List[str], 
                                      tob_data_list: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate consistency between TOB count and Excel categories.
    
    Args:
        tob_count: Number of TOB files
        excel_categories: List of categories from Excel file
        tob_data_list: Optional list of processed TOB data
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    excel_category_count = len(excel_categories)
    
    # Determine the actual TOB category count if data is available
    tob_category_count = None
    if tob_data_list is not None:
        tob_category_count = len(tob_data_list) if isinstance(tob_data_list, list) else 1
    
    print(f"🔍 Validation - TOB files: {tob_count}, Excel categories: {excel_category_count} ({excel_categories}), TOB categories extracted: {tob_category_count}")
    
    # Case 1: Multiple TOBs but single category in Excel
    if tob_count > 1 and excel_category_count <= 1:
        error_msg = f"Mismatch detected: Found {tob_count} TOB files but only {excel_category_count} category in the census file. Please ensure the number of categories in your census file matches the number of TOB files provided."
        return False, error_msg
    
    # Case 2: Single TOB but multiple categories in Excel
    if tob_count == 1 and excel_category_count > 1:
        # Need to wait for TOB data extraction to check actual categories in the TOB
        if tob_data_list is None:
            print("🔍 Single TOB with multiple Excel categories - waiting for TOB data extraction...")
            return True, None
        else:
            # TOB data is available, check extracted categories
            if tob_category_count != excel_category_count:
                error_msg = f"Mismatch detected: Found {excel_category_count} categories in census file ({excel_categories}) but the TOB contains {tob_category_count} categories. Please ensure your TOB covers all categories present in the census file."
                return False, error_msg
    
    # Case 3: Single TOB and single category in Excel
    if tob_count == 1 and excel_category_count == 1:
        if tob_data_list is not None:
            if tob_category_count != excel_category_count:
                error_msg = f"Mismatch detected: Found {excel_category_count} category in census file ({excel_categories}) but the TOB contains {tob_category_count} categories. Please ensure consistency between your TOB and census file."
                return False, error_msg
    
    # Case 4: Multiple TOBs and multiple categories in Excel
    if tob_count > 1 and excel_category_count > 1:
        if tob_data_list is not None:
            if tob_category_count != excel_category_count:
                error_msg = f"Mismatch detected: Found {excel_category_count} categories in census file ({excel_categories}) but processed {tob_category_count} categories from TOB files. Please ensure the number of categories matches between your TOB files and census file."
                return False, error_msg
    
    # If we have both counts and they match, validation passes
    if tob_data_list is not None and tob_category_count == excel_category_count:
        print(f"✅ Category validation passed: {excel_category_count} Excel categories match {tob_category_count} TOB categories")
        return True, None
    
    # If we don't have TOB data yet but initial checks pass, continue
    if tob_data_list is None:
        print("🔍 Initial validation passed, waiting for TOB data extraction...")
        return True, None
    
    return True, None

def validate_required_attachments(attachments: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Validate that required attachments are present.
    
    Args:
        attachments: List of attachment dictionaries
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not attachments:
        return False, "No attachments found"
    
    if len(attachments) < 3:
        return False, f"Insufficient attachments: found {len(attachments)}, required 3"
    
    # Check for Excel files
    excel_files = [att for att in attachments if att["filename"].lower().endswith(('.xls', '.xlsx', '.csv'))]
    if not excel_files:
        return False, "Missing Excel/CSV census file"
    
    # Check for PDF files
    pdf_files = [att for att in attachments if att["filename"].lower().endswith('.pdf')]
    if len(pdf_files) < 2:
        return False, "Missing required PDF files (need trade license and TOB)"
    
    return True, "All required attachments present"

def validate_email_data(email_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate email data structure.
    
    Args:
        email_data: Email data dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["from_email", "subject", "attachments"]
    
    for field in required_fields:
        if field not in email_data or not email_data[field]:
            return False, f"Missing required field: {field}"
    
    return True, "Email data is valid"