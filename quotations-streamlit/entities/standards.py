import pandas as pd
import re
import datetime

def standardize_relation(value):
    """
    Standardize relation values
    
    Args:
        value: Original relation value
        
    Returns:
        str: Standardized relation value
    """
    if pd.isna(value):
        return value
    
    value = str(value).lower().strip()
    
    # Handle Employee/Subscriber -> Principal
    if value in ['employee', 'subscriber', 'self', 'owner', 'staff', 'principal']:
        return 'Principal'
    
    # Handle Son/Daughter -> Child
    if value in ['son', 'daughter', 'child']:
        return 'Child'
    
    # Handle Wife/Husband -> Spouse
    if value in ['wife', 'husband', 'partner', 'spouse']:
        return 'Spouse'
    
    # Handle dependent
    if value in ['dependent']:
        return 'Dependent'
    
    # Return original value if no match
    return value.capitalize()  # Capitalize first letter for consistency

def standardize_gender(value):
    """
    Standardize gender values
    
    Args:
        value: Original gender value
        
    Returns:
        str: Standardized gender value (M/F)
    """
    if pd.isna(value):
        return value
    
    value = str(value).lower().strip()
    
    if value in ['male', 'm']:
        return 'M'
    elif value in ['female', 'f']:
        return 'F'
    
    return value  # Return original if not matching

def standardize_date(value):
    """
    Standardize date values to Excel serial numbers
    
    Args:
        value: Original date value
        
    Returns:
        float: Excel serial number representation of date
    """
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
