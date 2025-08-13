"""
Date utility functions.
"""

from datetime import date, datetime
from src.core.constants import Defaults

def get_today_date() -> str:
    """
    Get today's date formatted as YYYY-MM-DD.
    
    Returns:
        Today's date as string in YYYY-MM-DD format
    """
    today = date.today()
    formatted_date = today.strftime(Defaults.POLICY_START_DATE_FORMAT)
    return formatted_date

def format_date(date_obj: date, format_str: str = None) -> str:
    """
    Format a date object to string.
    
    Args:
        date_obj: Date object to format
        format_str: Format string (defaults to YYYY-MM-DD)
        
    Returns:
        Formatted date string
    """
    if format_str is None:
        format_str = Defaults.POLICY_START_DATE_FORMAT
    
    return date_obj.strftime(format_str)

def parse_date(date_str: str, format_str: str = None) -> date:
    """
    Parse a date string to date object.
    
    Args:
        date_str: Date string to parse
        format_str: Format string (defaults to YYYY-MM-DD)
        
    Returns:
        Date object
        
    Raises:
        ValueError: If date string cannot be parsed
    """
    if format_str is None:
        format_str = Defaults.POLICY_START_DATE_FORMAT
    
    return datetime.strptime(date_str, format_str).date()

def is_valid_date_string(date_str: str, format_str: str = None) -> bool:
    """
    Check if a date string is valid.
    
    Args:
        date_str: Date string to validate
        format_str: Format string (defaults to YYYY-MM-DD)
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parse_date(date_str, format_str)
        return True
    except ValueError:
        return False