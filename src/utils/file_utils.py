"""
File utility functions for handling various file operations.
""" 
 
import os
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from src.core.config import settings
from src.core.constants import FileExtensions

# Global lock for file operations
file_lock = threading.Lock()

def create_unique_folder(base_path: str, prefix: str = "") -> str:
    """
    Create a unique folder with timestamp and UUID.
    
    Args:
        base_path: Base directory path
        prefix: Optional prefix for folder name
        
    Returns:
        Path to the created unique folder
    """
    with file_lock:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_id = str(uuid.uuid4())[:8]
        
        if prefix:
            folder_name = f"{prefix}_{timestamp}_{unique_id}"
        else:
            folder_name = f"{timestamp}_{unique_id}"
        
        folder_path = os.path.join(base_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

def create_unique_email_folder(email_id: str) -> str:
    """
    Create a unique folder for email processing.
    
    Args:
        email_id: Email identifier
        
    Returns:
        Path to the created folder
    """
    return create_unique_folder(settings.ATTACHMENTS_DIR, f"email_{email_id}")

def ensure_directories_exist() -> None:
    """Ensure all required directories exist."""
    directories = [
        settings.ATTACHMENTS_DIR,
        settings.TEMP_ATTACHMENTS_DIR,
        settings.EMAIL_CACHE_DIR
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def get_file_extension(filename: str) -> str:
    """
    Get file extension in lowercase.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension in lowercase (including the dot)
    """
    return Path(filename).suffix.lower()

def is_excel_file(filename: str) -> bool:
    """
    Check if file is an Excel file.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if file is Excel format, False otherwise
    """
    return get_file_extension(filename) in FileExtensions.EXCEL_EXTENSIONS

def is_pdf_file(filename: str) -> bool:
    """
    Check if file is a PDF file.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if file is PDF, False otherwise
    """
    return get_file_extension(filename) == FileExtensions.PDF_EXTENSION

def is_supported_file(filename: str) -> bool:
    """
    Check if file format is supported.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if file format is supported, False otherwise
    """
    return get_file_extension(filename) in FileExtensions.SUPPORTED_EXTENSIONS

def filter_files_by_extension(filenames: List[str], extensions: set) -> List[str]:
    """
    Filter files by extensions.
    
    Args:
        filenames: List of filenames
        extensions: Set of extensions to filter by
        
    Returns:
        List of filenames with matching extensions
    """
    return [f for f in filenames if get_file_extension(f) in extensions]

def get_pdf_files(filenames: List[str]) -> List[str]:
    """Get PDF files from list of filenames."""
    return filter_files_by_extension(filenames, {FileExtensions.PDF_EXTENSION})

def get_excel_files(filenames: List[str]) -> List[str]:
    """Get Excel files from list of filenames."""
    return filter_files_by_extension(filenames, FileExtensions.EXCEL_EXTENSIONS)

def clean_filename(filename: str) -> str:
    """
    Clean filename by removing unwanted text.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove 'signed' text (case insensitive)
    filename = re.sub(r'(?i)signed', '', filename)
    # Replace 'PDF' with 'pdf'
    filename = filename.replace("PDF", "pdf")
    return filename

def safe_delete_file(file_path: str) -> bool:
    """
    Safely delete a file.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        True if file was deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False

def get_file_size(file_path: str) -> Optional[int]:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes, None if file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return None
    except Exception as e:
        print(f"Error getting file size for {file_path}: {e}")
        return None

def create_temp_filename(prefix: str = "temp", suffix: str = "") -> str:
    """
    Create a unique temporary filename.
    
    Args:
        prefix: Prefix for the filename
        suffix: Suffix for the filename (including extension)
        
    Returns:
        Unique temporary filename
    """
    temp_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{temp_id}{suffix}"

def validate_file_exists(file_path: str, raise_error: bool = True) -> bool:
    """
    Validate that a file exists.
    
    Args:
        file_path: Path to the file
        raise_error: Whether to raise an exception if file doesn't exist
        
    Returns:
        True if file exists, False otherwise
        
    Raises:
        FileNotFoundError: If file doesn't exist and raise_error is True
    """
    exists = os.path.exists(file_path)
    if not exists and raise_error:
        raise FileNotFoundError(f"File not found: {file_path}")
    return exists

def cleanup_folder(folder_path: str, keep_folder: bool = True) -> bool:
    """
    Clean up a folder by removing all its contents.
    
    Args:
        folder_path: Path to the folder to clean up
        keep_folder: Whether to keep the folder itself
        
    Returns:
        True if cleanup was successful, False otherwise
    """
    try:
        if not os.path.exists(folder_path):
            return True
        
        # Remove all files in the folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Remove the folder itself if requested
        if not keep_folder:
            os.rmdir(folder_path)
        
        return True
    except Exception as e:
        print(f"Error cleaning up folder {folder_path}: {e}")
        return False

import re  # Add this import at the top of the file