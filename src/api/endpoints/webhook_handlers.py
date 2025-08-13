"""
Webhook request handlers for Microsoft Graph email notifications.
"""

import time
import asyncio
import aiohttp
import json
from typing import Dict, Any
from fastapi import Request, Response, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse

from src.services.storage.redis_manager import redis_manager, EmailTask
from src.services.auth.token_manager import refresh_access_token
from src.services.communication.email_service import email_service
from src.services.storage.gcs_manager import gcs_manager
from src.utils.email_processing import EmailProcessor
from src.core.config import settings
from src.core.constants import APIEndpoints

class WebhookHandlers:
    """Handles webhook-related API endpoints."""
    
    def __init__(self):
        self.email_processor = EmailProcessor()
    
    async def handle_subscription(self, request: Request, background_tasks: BackgroundTasks):
        """Handle Microsoft Graph webhook subscription"""
        # Case 1: Validation POST with query param
        token = request.query_params.get("validationToken")
        if token:
            print(f"✅ Received validationToken (POST): {token}")
            return PlainTextResponse(content=token, status_code=200)
        
        # Case 2: Actual email notification
        try:
            start_time = time.time()
            data = await request.json()
            print("📥 Email notification received")
            
            # Get access token
            access_token = refresh_access_token()
            
            # Process notifications in background
            background_tasks.add_task(self.process_notifications, data, access_token)
            
            print(f"Webhook handler took {time.time()-start_time:.3f} seconds")
            return Response(status_code=202)
            
        except Exception as e:
            print(f"Error in webhook handler: {e}")
            return Response(status_code=202)
    
    async def process_notifications(self, data: Dict[str, Any], access_token: str):
        """Process Microsoft Graph notifications"""
        try:
            for event in data.get("value", []):
                if event["changeType"] == "created" and event.get("clientState") == settings.WEBHOOK_CLIENT_STATE:
                    resource = event["resource"]
                    message_id = resource.split("/")[-1] if "/" in resource else "unknown"
                    
                    # Check if already processed
                    if await redis_manager.is_message_processed(message_id):
                        print(f"⚠️ Message already processed: {message_id[:8]}...")
                        continue
                    
                    # Get email details
                    email_data = await self.email_processor.get_email_details(resource, access_token)
                    if not email_data:
                        continue
                    
                    # Check for business duplicates
                    cached_data = await redis_manager.get_cached_email_data(message_id)
                    if cached_data:
                        cached_key = self.email_processor.generate_business_key(cached_data)
                        new_key = self.email_processor.generate_business_key(email_data)
                        
                        if cached_key == new_key:
                            print(f"⚠️ Skipping business duplicate: {message_id[:8]}...")
                            await redis_manager.mark_message_processed(message_id)
                            continue
                    
                    # Cache email data
                    await redis_manager.cache_email_data(message_id, email_data)
                    
                    # Add to processing queue
                    await redis_manager.add_email_to_queue(email_data)
                    
                    # Mark as processed to prevent duplicates
                    await redis_manager.mark_message_processed(message_id)
                    
        except Exception as e:
            print(f"Error processing notifications: {e}")
    
    async def process_email_and_complete(self, task: EmailTask):
        """Process email and handle completion"""
        try:
            # Send to process_email API and wait for completion
            result = await self.send_to_process_email_api(task.email_data, task.task_id)
            
            if result.get("success"):
                await redis_manager.complete_task(task.task_id, result.get("result"))
            else:
                await redis_manager.complete_task(task.task_id, error=result.get("error", "Unknown error"))
                
        except Exception as e:
            await redis_manager.complete_task(task.task_id, error=str(e))
    
    async def send_to_process_email_api(self, email_payload: Dict[str, Any], task_id: str):
        """Send email data to process_email API and wait for completion"""
        try:
            email_id = email_payload.get("email_id", "unknown")[:8]
            print(f"📤 Sending email {email_id}... to process_email API")
            
            email_payload["redis_task_id"] = task_id
            timeout = aiohttp.ClientTimeout(total=7200)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    APIEndpoints.PROCESS_EMAIL,
                    json=email_payload,
                ) as response:
                    response_text = await response.text()
                    
                    if response.status not in [200, 202]:
                        print(f"❌ Failed to process email {email_id}...: {response.status}. Error: {response_text}")
                        return {"success": False, "error": response_text}
                    
                    try:
                        result = json.loads(response_text)
                    except:
                        result = {"raw_response": response_text}
                    
                    print(f"✅ Successfully processed email {email_id}...")
                    return {"success": True, "result": result}
                    
        except asyncio.TimeoutError:
            print(f"⏰ Timeout processing email {email_id}...")
            return {"success": False, "error": "Processing timeout"}
        except Exception as e:
            print(f"Error sending to process_email API: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_queue_status(self):
        """Get current queue and processing status"""
        try:
            stats = await redis_manager.get_processing_stats()
            processing_details = await redis_manager.get_processing_details()
            
            return JSONResponse(content={
                "queue_stats": stats.dict(),
                "currently_processing": processing_details,
                "max_concurrent": settings.MAX_CONCURRENT_PROCESSING,
                "queue_type": "REDIS_MANAGED_QUEUE"
            })
            
        except Exception as e:
            print(f"Error getting queue status: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    async def clear_queue(self):
        """Clear all queues (for debugging)"""
        try:
            await redis_manager.clear_all_queues()
            return JSONResponse(content={"message": "All queues cleared"})
            
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)