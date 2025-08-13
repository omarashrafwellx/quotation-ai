"""
Email processing FastAPI application.
Refactored from the original process_email.py
"""

import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.api.endpoints.email_handlers import EmailHandlers
from src.utils.file_utils import ensure_directories_exist
from src.core.config import settings

# Initialize FastAPI app
app = FastAPI(
    title="Quotation AI Email Processor",
    description="Processes emails and generates insurance quotes",
    version="1.0.0"
)

# Initialize email handlers
email_handlers = EmailHandlers()

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print("🚀 Starting Email Processing Server...")
    
    # Ensure required directories exist
    ensure_directories_exist()
    
    # Validate configuration
    try:
        settings.validate_required_settings()
        print("✅ Configuration validated")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        raise

@app.post("/process-email")
async def process_email(payload: dict):
    """
    Process email and generate quote.
    
    This endpoint receives email data from the webhook server
    and processes it to generate insurance quotes.
    """
    return await email_handlers.process_email(payload)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "email_processor"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Quotation AI Email Processor",
        "status": "running",
        "endpoints": {
            "process_email": "/process-email",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.process_email:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )