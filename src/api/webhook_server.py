"""
Main webhook server for handling Microsoft Graph email notifications.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse

from src.services.storage.redis_manager import redis_manager
from src.api.endpoints.webhook_handlers import WebhookHandlers
from src.utils.file_utils import ensure_directories_exist
from src.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events"""
    # Startup
    print("🚀 Starting up webhook server...")
    
    # Ensure required directories exist
    ensure_directories_exist()
    
    # Initialize Redis connection
    await redis_manager.connect()
    
    # Start queue processor
    asyncio.create_task(start_queue_processor())
    
    print(f"🚀 Redis-based webhook server started with max {settings.MAX_CONCURRENT_PROCESSING} concurrent processes")
    
    yield  # This is where the application runs
    
    # Shutdown
    print("🛑 Shutting down webhook server...")
    await redis_manager.disconnect()
    print("🛑 Redis connections closed")

# Initialize FastAPI app
app = FastAPI(
    title="Quotation AI Webhook Server",
    description="Handles Microsoft Graph email notifications for automated quote processing",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize webhook handlers
webhook_handlers = WebhookHandlers()

async def start_queue_processor():
    """Main queue processor that maintains MAX_CONCURRENT_PROCESSING"""
    print(f"🚀 Starting queue processor with max {settings.MAX_CONCURRENT_PROCESSING} concurrent processes")
    
    while True:
        try:
            # Check current processing count
            processing_count = await redis_manager.redis_client.hlen("emails_in_processing")
            
            # If we have capacity, process next email
            if processing_count < settings.MAX_CONCURRENT_PROCESSING:
                task = await redis_manager.get_next_email_from_queue()
                
                if task:
                    # Move to processing state
                    await redis_manager.move_task_to_processing(task)
                    
                    # Start processing in background (don't await)
                    asyncio.create_task(webhook_handlers.process_email_and_complete(task))
                    
                    # Print current status
                    queue_size = await redis_manager.redis_client.llen("email_processing_queue")
                    processing_count = await redis_manager.redis_client.hlen("emails_in_processing")
                    print(f"📊 Queue: {queue_size} waiting, {processing_count} processing")
            else:
                # Wait a bit before checking again
                await asyncio.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Error in queue processor: {e}")
            await asyncio.sleep(1)

@app.post("/email-sub")
async def handle_subscription(request: Request, background_tasks: BackgroundTasks):
    """Handle Microsoft Graph webhook subscription"""
    return await webhook_handlers.handle_subscription(request, background_tasks)

@app.get("/queue-status")
async def get_queue_status():
    """Get current queue and processing status"""
    return await webhook_handlers.get_queue_status()

@app.get("/clear-queue")
async def clear_queue():
    """Clear all queues (for debugging)"""
    return await webhook_handlers.clear_queue()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "webhook_server"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Quotation AI Webhook Server",
        "status": "running",
        "endpoints": {
            "webhook": "/email-sub",
            "queue_status": "/queue-status",
            "clear_queue": "/clear-queue",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.webhook_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )