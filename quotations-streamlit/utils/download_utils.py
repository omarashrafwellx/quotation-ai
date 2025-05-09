import pandas as pd
import io
import json
import base64

def to_excel_bytes(df):
    """
    Convert DataFrame to Excel bytes for download.
    
    Args:
        df: DataFrame to convert
        
    Returns:
        bytes: Excel file as bytes
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    
    output.seek(0)
    return output.getvalue()

def to_json_bytes(data):
    """
    Convert data to JSON bytes for download.
    
    Args:
        data: Data to convert to JSON
        
    Returns:
        bytes: JSON file as bytes
    """
    json_str = json.dumps(data, indent=4)
    return json_str.encode('utf-8')

def to_csv_bytes(df):
    """
    Convert DataFrame to CSV bytes for download.
    
    Args:
        df: DataFrame to convert
        
    Returns:
        bytes: CSV file as bytes
    """
    return df.to_csv(index=False).encode('utf-8')

def get_pdf_bytes(file_path):
    """
    Read PDF file and return its bytes.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        bytes: PDF file as bytes
    """
    with open(file_path, 'rb') as f:
        return f.read()

def get_download_link(content, filename, text):
    """
    Generate a download link for binary content.
    
    Args:
        content: Binary content
        filename: Name of the file
        text: Text to display for the link
        
    Returns:
        str: HTML for download link
    """
    b64 = base64.b64encode(content).decode()
    href = f'<a href="data:file/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href