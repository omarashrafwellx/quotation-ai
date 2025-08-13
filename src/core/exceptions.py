"""
Custom exceptions for the Quotation AI system.
"""

class QuotationAIException(Exception):
    """Base exception for Quotation AI system."""
    pass

class AuthenticationError(QuotationAIException):
    """Raised when authentication fails."""
    pass

class DocumentProcessingError(QuotationAIException):
    """Raised when document processing fails."""
    pass

class ValidationError(QuotationAIException):
    """Raised when data validation fails."""
    pass

class StorageError(QuotationAIException):
    """Raised when storage operations fail."""
    pass

class BrowserAutomationError(QuotationAIException):
    """Raised when browser automation fails."""
    pass

class EmailProcessingError(QuotationAIException):
    """Raised when email processing fails."""
    pass

class AIServiceError(QuotationAIException):
    """Raised when AI service operations fail."""
    pass

class CategoryMismatchError(ValidationError):
    """Raised when document categories don't match."""
    pass

class InsufficientAttachmentsError(ValidationError):
    """Raised when required attachments are missing."""
    pass