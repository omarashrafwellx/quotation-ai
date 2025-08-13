"""
Email processing handlers - extracted from the original process_email.py
This file contains the core email processing logic.
"""
import asyncio
import os
import uuid
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from fastapi.responses import JSONResponse
from pathlib import Path
from src.services.ai.company_extractor import extract_company_data
from src.services.ai.tob_processor import process_tob
from src.services.ai.email_parser import extract_structured_data_from_email
from src.services.ai.llm_classifier import classify_pdfs_with_llm
from src.services.data.census_processor import standardize_census_file
from src.services.data.validator import validate_category_consistency, get_excel_categories
from src.services.automation.browser_manager import generate_quote_automation
from src.services.communication.email_service import email_service, reply_to_email
from src.services.communication.slack_service import slack_service
from src.services.storage.gcs_manager import gcs_manager
from src.utils.file_utils import create_unique_email_folder, is_excel_file, get_pdf_files
from src.utils.date_utils import get_today_date
from src.database.database import get_db_session
from src.database import crud, models
from src.core.config import settings
from src.core.constants import EmailTemplates, Defaults
from src.core.exceptions import ValidationError, DocumentProcessingError

def compare_dates(policy_date: str):
    date_str1 = policy_date
    date_str2 = get_today_date()
    # The format code that matches the strings
    date_format = "%Y-%m-%d"
    try:
        date_obj1 = datetime.strptime(date_str1, date_format).date()
        date_obj2 = datetime.strptime(date_str2, date_format).date()

        # Now you can compare them directly
        if date_obj1 > date_obj2:
            return True
        else:
            return False
    except ValueError as e:
        print(f"Error: One of the date strings is not in the correct format. {e}")

def evaluate_date(email_json , all_tob_data):
    date_missing_data = False
    date_missing_reason = ''
    try:
        print("================================TOB File Policy Date=========================================")
        print(f"TOB File Start Policy Date: {all_tob_data[0]['policy_start_date']['value']}")
        if len(all_tob_data) > 1:
            print(f"TOB File Start Policy Date: {all_tob_data[1]['policy_start_date']['value']}")
            print(f"TOB File Start Policy Date: {all_tob_data[2]['policy_start_date']['value']}")
        print("====================================Email Json Start Policy Date===================================")
        print(f"Email Extracted Start Policy Date: {email_json['policy_start_date']}")
        
        if all_tob_data[0]['policy_start_date']['value'] in ['', None, 'null', 'Null', 'NULL']:
            # date_missing_data.append('TOB file has no Date in it.')
            if email_json['policy_start_date'] in ['', None, 'null', 'Null', 'NULL']:
                date_missing_reason = date_missing_reason + "\n Email and TOB file does not contain Start Policy Date"
                date_missing_data = True
            else:
                if compare_dates(email_json['policy_start_date']):
                    return {'success': True,
                            'date':email_json['policy_start_date']} 
                else:
                    date_missing_reason = date_missing_reason + "TOB File does not have Policy Date and Emails Start Policy date is out dated or The policy has a backdated start date, prior to today's date. "
                    date_missing_data = True
                
        elif email_json['policy_start_date'] in ['', None, 'null', 'Null', 'NULL']:
            if all_tob_data[0]['policy_start_date']['value'] in ['', None, 'null', 'Null', 'NULL']:
                date_missing_reason = date_missing_reason + "\n Email and TOB file does not contain Start Policy Date"
                date_missing_data = True
            else:
                if compare_dates(all_tob_data[0]['policy_start_date']['value']):
                    return {'success': True,
                            'date':email_json['policy_start_date']} 
                else:
                    date_missing_reason = date_missing_reason + "\nEmail does not have Policy Date and TOB File Start Policy date is out dated or The policy has a backdated start date, prior to today's date. "
                    date_missing_data = True
        else:
            if compare_dates(email_json['policy_start_date']):
                    return {'success': True,
                            'date':email_json['policy_start_date']} 
            elif compare_dates(all_tob_data[0]['policy_start_date']['value']):
                    return {'success': True,
                            'date':email_json['policy_start_date']} 
            else: 
                date_missing_reason = date_missing_reason + "\nEmail and TOB File Start Policy date is out dated or The policy has a backdated start date, prior to today's date."
                date_missing_data = True
                
        return {'success': False,
                'date_missing_data': date_missing_data,
                'date_missing_reason': date_missing_reason
                }
    except Exception as e:
        print('Error in Evaluate Date Function.', str(e))
        return {'success': False,
                'date_missing_data': date_missing_data,
                'date_missing_reason': date_missing_reason
                }

class EmailHandlers:
    """Handles email processing requests."""
    
    def __init__(self):
        # Thread pool for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # Semaphore to limit concurrent browser sessions
        self.browser_semaphore = asyncio.Semaphore(3)
        
    async def process_email(self, payload: dict) -> JSONResponse:
        """
        Main email processing function.
        This is the core logic extracted from the original process_email.py
        """
        processing_id = str(uuid.uuid4())
        print(f"🚀 Started processing email (ID: {processing_id[:8]})")
        
        # Use semaphore to limit concurrent processing
        async with self.browser_semaphore:
            db = None
            quotation_id = None
            
            try:
                # Initialize database session in thread pool
                loop = asyncio.get_event_loop()
                db = await loop.run_in_executor(self.thread_pool, get_db_session)
                
                # Extract email data
                email_data = self._extract_email_data(payload)
                
                quotation_start_body = f"""
Hello {email_data["from_email"].split('@')[0].capitalize()},

This is to inform you that your quote PDF is currently being processed. You will receive an email notification as soon as the processing is complete.

Best regards,  
Wellx AI Quotation Engine
"""
                
                email_service.send_text_email(email_data["from_email"], "Quote PDF Processing in Progress", quotation_start_body)
                
                self.slack_message_respone = slack_service.reply_to_the_message(settings.SLACK_CHANNEL_NAME, text=quotation_start_body)
                
                # Validate email has required attachments
                excel_attachments = self._get_excel_attachments(email_data["attachments"])
                print(excel_attachments,'excel attachments')
                if not excel_attachments:
                    await self._send_missing_census_email(email_data["from_email"])
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Missing Excel/census attachment required for quote generation."}
                    )
                
                # Classify PDF documents
                pdf_classification = await self._classify_documents(email_data["attachments"])
                if not self._validate_required_documents(pdf_classification):
                    await self._send_missing_documents_email(email_data["from_email"])
                    return JSONResponse(
                        status_code=400, 
                        content={"error": "Missing required inputs for quote generation"}
                    )
                
                # Create unique processing folder
                email_folder = create_unique_email_folder(email_data["email_id"])
                
                # Download and validate documents
                downloaded_files = await self._download_attachments(email_data["attachments"], email_folder)
                
                # Category validation
                excel_categories = await self._get_excel_categories(downloaded_files, excel_attachments[0]['filename'])
                tob_count = len(pdf_classification['tables_of_benefits'])
                
                # Initial validation
                is_valid, error_message = await self._validate_categories(tob_count, excel_categories)
                if not is_valid:
                    await email_service.send_category_mismatch_email(email_data["from_email"], error_message)
                    return JSONResponse(status_code=400, content={"error": error_message})
                
                # Process email content and create database records
                email_json = await self._process_email_content(email_data)
                broker, relationship_manager = await self._create_db_entities(db, email_json, email_data["from_email"])
                quotation = await self._create_quotation_record(db, email_json, broker, relationship_manager, email_data)
                quotation_id = quotation.id
                
                # Log processing start
                await self._log_quotation_event(
                    quotation_id, "PROCESSING_STARTED",
                    "Email received, documents processed, quotation created",
                    request_data={
                        "sender": email_data["from_email"],
                        "subject": email_data["subject"],
                        "attachments_count": len(email_data["attachments"]),
                        "tob_files_count": tob_count,
                        "excel_categories": excel_categories
                    }
                )
                
                # Process documents concurrently
                company_json, tob_data_list, excel_file_path = await self._process_documents_concurrent(
                    downloaded_files, pdf_classification
                )
                print(tob_data_list,'tob data list')
                # Final category validation after TOB processing
                is_valid, error_message = await self._validate_categories(
                    tob_count, excel_categories, tob_data_list
                )
                if not is_valid:
                    await email_service.send_category_mismatch_email(email_data["from_email"], error_message)
                    return JSONResponse(status_code=400, content={"error": error_message})
                
                # Validate all required data is present
                if not all([company_json, tob_data_list, excel_file_path]):
                    missing = []
                    if not company_json: missing.append("company data")
                    if not tob_data_list: missing.append("TOB data")
                    if not excel_file_path: missing.append("census file")
                    
                    error_msg = f"Missing required inputs: {', '.join(missing)}"
                    await self._log_quotation_event(quotation_id, "PROCESSING_FAILED", error_msg)
                    return JSONResponse(status_code=400, content={"error": error_msg})
                
                # Update quotation status to processing
                await self._update_quotation_status(db, quotation_id, models.QuotationStatus.PROCESSING)
                
                # Generate quote using browser automation
                quote_data = self._prepare_quote_data(company_json, email_json)
                
                res = evaluate_date(email_json , tob_data_list)
                
            
                if res["success"]:
                    quote_data["policy_start_date"] = res["date"]
                else:
                    date_missing_data = res["date_missing_data"]
                    date_missing_reason = res["date_missing_reason"]
                
                    if date_missing_data :
                        missing_date_subject = "Quote pdf cannot be generated"
                        missing_date_body = f"""
    Hello {email_data["from_email"]},

    We regret to inform you that we are unable to generate the quote PDF you requested at this time.

    This is because {date_missing_reason}

    Kindly resend your request with all required documents attached so we can proceed accordingly.

    Best regards,  
    Wellx AI Quotation Engine
                    """

                        email_service.send_text_email(email_data["from_email"], missing_date_subject, missing_date_body)
                        return JSONResponse(status_code=500, content={
                    "status": date_missing_reason,
                    "error": date_missing_reason,
                    "processing_id": processing_id
                        })
                
                with open("Combined_Data_ToBe_Filled.json",'w') as f:
                    json.dump({"quote_data": quote_data,
                                    "tob_data_list": tob_data_list,
                                    "excel_file_path": excel_file_path
                                }, f, indent=4)
                
                quote_result = await self._generate_quote_automation(quote_data, tob_data_list, excel_file_path)
                
                if not quote_result.get("success") or not quote_result.get("pdf_path"):
                    await self._update_quotation_status(db, quotation_id, models.QuotationStatus.FAILED)
                    await self._log_quotation_event(quotation_id, "GENERATION_FAILED", "Quote PDF generation failed")
                    return JSONResponse(status_code=500, content={"error": "Quote PDF not generated"})
                
                # Upload PDF to GCS and send notifications
                pdf_url = await self._upload_and_notify(
                    quote_result["pdf_path"], email_data, company_json, email_json, 
                    quotation, tob_data_list, db, quotation_id
                )
                
                # Clean up
                self._cleanup_files(quote_result["pdf_path"])
                
                print(f"✅ FULLY completed processing email (ID: {processing_id[:8]})")
                
                return JSONResponse(status_code=200, content={
                    "status": "success",
                    "quotation_id": quotation.external_id,
                    "quote": quote_result,
                    "quote_pdf_url": pdf_url,
                    "email_sent": True,
                    "processing_id": processing_id,
                    "total_categories": len(tob_data_list),
                    "validation_passed": True
                })
                
            except Exception as e:
                print(f"❌ Error in process_email: {e}")
                
                if quotation_id:
                    try:
                        await self._update_quotation_status(db, quotation_id, models.QuotationStatus.FAILED)
                        await self._log_quotation_event(quotation_id, "SYSTEM_ERROR", f"System error: {str(e)}")
                    except:
                        pass
                        
                return JSONResponse(status_code=500, content={
                    "status": "error",
                    "error": str(e),
                    "processing_id": processing_id
                })
            
            finally:
                if db:
                    await asyncio.get_event_loop().run_in_executor(self.thread_pool, db.close)
    
    def _extract_email_data(self, payload: dict) -> dict:
        """Extract email data from payload."""
        return {
            "from_email": payload.get("from_email", ""),
            "original_sender_email": payload.get("original_sender_email", ""),
            "to": payload.get("to", []),
            "subject": payload.get("subject", ""),
            "body": payload.get("body", ""),
            "attachments": payload.get("attachments", []),
            "email_id": payload.get("email_id", str(uuid.uuid4()))
        }
    
    def _get_excel_attachments(self, attachments: List[dict]) -> List[dict]:
        """Get Excel attachments from attachment list."""
        return [att for att in attachments if is_excel_file(att["filename"])]
    
    async def _classify_documents(self, attachments: List[dict]) -> dict:
        """Classify PDF documents using LLM."""
        pdf_filenames = [att["filename"] for att in attachments if att["filename"].lower().endswith(".pdf")]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, classify_pdfs_with_llm, pdf_filenames)
    
    def _validate_required_documents(self, classification: dict) -> bool:
        """Validate that required documents are present."""
        return bool(classification.get('tables_of_benefits') and classification.get('trade_license'))
    
    async def _download_attachments(self, attachments: List[dict], email_folder: str) -> dict:
        """Download all attachments concurrently."""
        download_tasks = []
        for attachment in attachments:
            filename = attachment["filename"]
            gcs_path = attachment["gcs_path"]
            local_path = os.path.join(email_folder, filename)
            task = gcs_manager.download_file(gcs_path, local_path)
            download_tasks.append((task, filename, local_path))
        
        downloaded_files = {}
        for task, filename, local_path in download_tasks:
            success = await task
            if success:
                downloaded_files[filename] = local_path
                print(f"📎 Downloaded: {filename}")
            else:
                print(f"❌ Failed to download {filename}")
        
        return downloaded_files
    
    async def _get_excel_categories(self, downloaded_files: dict, excel_filename: str) -> List[str]:
        """Get categories from Excel file."""
        excel_path = downloaded_files.get(excel_filename)
        if excel_path:
            return await get_excel_categories(excel_path)
        return ["A"]  # Default
    
    async def _validate_categories(self, tob_count: int, excel_categories: List[str], 
                                 tob_data_list: List[dict] = None) -> tuple:
        """Validate category consistency."""
        return await validate_category_consistency(tob_count, excel_categories, tob_data_list)
    
    async def _process_email_content(self, email_data: dict) -> dict:
        """Process email content to extract broker and RM info."""
        combined_email = f"From: {email_data['from_email']}\nTo: {', '.join(email_data['to'])}\nSubject: {email_data['subject']}\n\n{email_data['body']}"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, extract_structured_data_from_email, combined_email)
    
    async def _create_db_entities(self, db, email_json: dict, sender_email: str):
        """Create/get broker and relationship manager."""
        def create_entities():
            broker = crud.get_or_create_broker(
                db=db, 
                name=email_json['broker_name'], 
                email=sender_email
            )
            relationship_manager = crud.get_or_create_relationship_manager(
                db=db,
                name=email_json['relationship_manager']
            )
            return broker, relationship_manager
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, create_entities)
    
    async def _create_quotation_record(self, db, email_json: dict, broker, relationship_manager, email_data: dict):
        """Create quotation record in database."""
        def create_quotation():
            policy_start_date = datetime.strptime(get_today_date(), "%Y-%m-%d").date()
            return crud.create_quotation(
                db=db,
                client_name="",  # Will be updated after company extraction
                broker_id=broker.id,
                relationship_manager_id=relationship_manager.id,
                request_email_id=email_data["email_id"],
                policy_start_date=policy_start_date
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, create_quotation)
    
    async def _process_documents_concurrent(self, downloaded_files: dict, classification: dict):
        """Process documents concurrently."""
        company_json = None
        tob_data_list = []
        excel_file_path = None
        
        for filename, local_path in downloaded_files.items():
            fname_lower = filename.lower()   
            if filename in classification["tables_of_benefits"]:
                # Create a task for each TOB file
                tob_data = process_tob(local_path)
                if tob_data:
                    tob_data_list.extend(tob_data if isinstance(tob_data, list) else [tob_data])
                
            elif fname_lower == classification["trade_license"].lower():
                company_json = extract_company_data(local_path)
                
            elif Path(filename).suffix.lower() in [".xlsx", ".xls", ".csv"]:
                data_census = standardize_census_file(local_path)
        
        return company_json, tob_data_list, data_census['output_file_path']
    
    def _prepare_quote_data(self, company_json: dict, email_json: dict) -> dict:
        """Prepare quote data for browser automation."""
        return {
            "client_name": company_json['company_name'],
            "policy_start_date": get_today_date(),
            "broker_name": email_json['broker_name'],
            "broker_contact_person": email_json['broker_contact_person'],
            "relationship_manager": email_json['relationship_manager'],
            "adjustments_discount": Defaults.ADJUSTMENTS_DISCOUNT,
            "brokerage_fees": Defaults.BROKERAGE_FEES,
            "healthx": Defaults.HEALTHX,
            "tpa": Defaults.TPA,
            "insurer": Defaults.INSURER
        }
    
    async def _generate_quote_automation(self, quote_data: dict, tob_data_list: List[dict], excel_file_path: str):
        """Generate quote using browser automation."""
        return await generate_quote_automation(quote_data, tob_data_list, excel_file_path)
    
    async def _upload_and_notify(self, pdf_path: str, email_data: dict, company_json: dict, 
                            email_json: dict, quotation, tob_data_list: List[dict], 
                            db, quotation_id: int) -> str:
        """Upload PDF and send notifications."""
        try:
            # Determine GCS folder based on email data
            if email_data.get("attachments"):
                first_gcs_path = email_data["attachments"][0]["gcs_path"]
                gcs_folder = os.path.dirname(first_gcs_path) + "/"
            else:
                original_sender = email_data.get("original_sender_email", "")
                sender = email_data["from_email"]
                gcs_folder = f"quote/{sender}-{original_sender}/" if original_sender else f"quote/{sender}/"
                
            # Upload PDF to GCS
            pdf_filename = os.path.basename(pdf_path)
            quote_pdf_gcs_path = gcs_folder + pdf_filename
            quote_pdf_url = await gcs_manager.upload_file(pdf_path, quote_pdf_gcs_path)
            
            if not quote_pdf_url:
                await self._update_quotation_status(db, quotation_id, models.QuotationStatus.FAILED)
                await self._log_quotation_event(
                    quotation_id, "UPLOAD_FAILED",
                    "Failed to upload PDF to GCS"
                )
                raise Exception("Failed to upload quote PDF to GCS")
                
            # Update database with PDF URL and status
            loop = asyncio.get_event_loop()
            
            def update_completion():
                crud.update_quotation_pdf(db, quotation_id, quote_pdf_url)
                crud.update_quotation_status(db, quotation_id, models.QuotationStatus.COMPLETED)
            
            await loop.run_in_executor(self.thread_pool, update_completion)
            
            # Log completion
            await self._log_quotation_event(
                quotation_id, "GENERATION_COMPLETED",
                "Quote PDF generated and uploaded successfully",
                response_data={
                    "pdf_url": quote_pdf_url,
                    "pdf_path": quote_pdf_gcs_path,
                    "total_categories_processed": len(tob_data_list)
                }
            )
            
            # Send notifications concurrently
            await asyncio.gather(
                self._send_email_notification(
                    email_data, email_json, company_json, quotation, 
                    tob_data_list, pdf_path, db, quotation_id
                ),
                self._send_slack_notification(
                    email_json, company_json, quotation, 
                    tob_data_list, pdf_path, quotation_id
                ),
                return_exceptions=True
            )
            
            return quote_pdf_url
            
        except Exception as e:
            print(f"❌ Error in upload and notify: {e}")
            await self._update_quotation_status(db, quotation_id, models.QuotationStatus.FAILED)
            await self._log_quotation_event(
                quotation_id, "UPLOAD_NOTIFY_FAILED",
                f"Upload and notify failed: {str(e)}"
            )
            raise

    async def _send_email_notification(self, email_data: dict, email_json: dict, 
                                     company_json: dict, quotation, tob_data_list: List[dict], 
                                     pdf_path: str, db, quotation_id: int):
        """Send email notification with PDF attachment."""
        try:
            sender = email_data["from_email"]
            subject = email_data["subject"]
            reply_subject = f"Re: {subject}"
            
            # Extract value adjustments (skip certain keys as per original logic)
            SKIP_CHANGED_KEYS = {"policy_start_date", "nas_network", "territorial_cover"}
            explanations = self._extract_changed_explanations(tob_data_list, skip_keys=SKIP_CHANGED_KEYS)
            
            # explanation_intro = ""
            # if explanations:
            #     explanation_intro = "\n\nHowever, please note the following value adjustments based on your submission:\n\n"
            #     explanation_intro += "\n\n".join(f"- {exp}" for exp in explanations)

            starting = f"""
<html>
<head>
<style>
    body {{ font-family: Arial, sans-serif; font-size: 14px; color: #333; }}
    h2 {{ color: #2E6EB6; }}
    ul {{ margin-top: 0; padding-left: 18px; }}
    li {{ margin-bottom: 10px; }}
    .section-title {{ font-weight: bold; margin-top: 20px; }}
</style>
</head>
<body>
<p>Hi {email_json['relationship_manager']},</p>

<p>We are pleased to inform you that the quote PDF has been successfully generated with the following details:</p>

<ul>
    <li><strong>Company</strong>: {company_json['company_name']}</li>
    <li><strong>Broker</strong>: {email_json['broker_name']}</li>
    <li><strong>Broker Contact Person</strong>: {email_json['broker_contact_person']}</li>
    <li><strong>Quotation ID</strong>: {quotation.external_id}</li>
    <li><strong>Categories Processed</strong>: {len(tob_data_list)}</li>
</ul>

<p class="section-title">Value Adjustments</p>
<p>Please note the following adjustments were applied to ensure compliance with our business rules and product constraints:</p>
<ul>
                    """

            # Fix the loop to handle dictionary unpacking correctly
            for res in explanations:
                k, v = next(iter(res.items()))  # Unpack the only key-value pair

                starting += f"""
<li><strong>{k}</strong>:
    <ul>"""
                for i in v:
                    starting += f"""
        <li>{i}</li>"""
            starting += """
    </ul>
</li>"""  # Added closing li

            ending = """
</ul>
<p>If you have any questions or need further clarification, please don’t hesitate to contact us.</p>

<p>Best regards,<br/>
<strong>Wellx AI Quotation Engine</strong></p>
</body>
</html>"""

            starting += '\n' + ending

            reply_body = starting
            
            # Send email using the email service
            loop = asyncio.get_event_loop()
            # await loop.run_in_executor(
            #     self.thread_pool, 
            #     email_service.send_pdf_email, 
            #     sender, reply_subject, reply_body, pdf_path
            # )
            await loop.run_in_executor(
                self.thread_pool, 
                reply_to_email, 
                email_data['email_id'], reply_body, pdf_path
            )
            
            # Update status to DELIVERED
            await self._update_quotation_status(db, quotation_id, models.QuotationStatus.DELIVERED)
            await self._log_quotation_event(
                quotation_id, "EMAIL_SENT",
                f"Quote PDF sent to {sender}",
                response_data={"recipient": sender, "subject": reply_subject}
            )
            
            print(f"✅ Quotation PDF sent to {sender}")
            
        except Exception as email_err:
            print(f"❌ Error sending email with quotation PDF: {email_err}")
            await self._log_quotation_event(
                quotation_id, "EMAIL_FAILED",
                f"Failed to send email: {str(email_err)}"
            )

    async def _send_slack_notification(self, email_json: dict, company_json: dict, 
                                     quotation, tob_data_list: List[dict], 
                                     pdf_path: str, quotation_id: int):
        """Send Slack notification with PDF."""
        try:           
            slack_channel_name = settings.SLACK_CHANNEL_NAME
            
            # Extract value adjustments
            SKIP_CHANGED_KEYS = {"policy_start_date", "nas_network", "territorial_cover"}
            explanations = self._extract_changed_explanations(tob_data_list, skip_keys=SKIP_CHANGED_KEYS)
            
                    # Start Slack message in markdown
            slack_message = f"""
Hi {email_json['relationship_manager']},

We are pleased to inform you that the quote PDF has been successfully generated with the following details:

*Company*: {company_json['company_name']}
*Broker*: {email_json['broker_name']}
*Broker Contact Person*: {email_json['broker_contact_person']}
*Quotation ID*: {quotation.external_id}
*Categories Processed*: {len(tob_data_list)}
"""
            if explanations:
                # slack_message += explanation_intro + "\n"

                for res in explanations:
                    k, v = next(iter(res.items()))  # Unpack the only key-value pair

                    slack_message += f"\n• *{k}*:\n"
                    for i in v:
                        slack_message += f"   - {i}\n"

            slack_message += """
If you have any questions or need further clarification, please don’t hesitate to contact us.

Best regards,  
*Wellx AI Quotation Engine*
"""
            
            def send_slack():
                slack_channel_id = slack_service.get_channel_id(slack_channel_name)
                if not slack_channel_id:
                    print(f"Slack channel '{slack_channel_name}' not found. Creating it...")
                    slack_channel_id = slack_service.create_channel(slack_channel_name)
                
                if slack_channel_id:
                    status, slack_response = slack_service.send_pdf_with_retry(
                        slack_channel_id, pdf_path, slack_message, ts=self.slack_message_respone['ts']
                    )
                    return status, slack_response
                return False, "Channel not found"
            
            loop = asyncio.get_event_loop()
            status, slack_response = await loop.run_in_executor(self.thread_pool, send_slack)
            
            if not status:
                print(f"❌ Slack upload failed: {slack_response}")
                await self._log_quotation_event(
                    quotation_id, "SLACK_FAILED",
                    f"Slack upload failed: {slack_response}"
                )
            else:
                print(f"{slack_response} to '{slack_channel_name}'")
                await self._log_quotation_event(
                    quotation_id, "SLACK_SENT",
                    f"PDF sent to Slack channel: {slack_channel_name}"
                )
                
        except Exception as slack_err:
            print(f"❌ Error sending PDF to Slack: {slack_err}")
            await self._log_quotation_event(
                quotation_id, "SLACK_ERROR",
                f"Slack error: {str(slack_err)}"
            )

    def _extract_changed_explanations(self, tob_json: List[dict], skip_keys=None) -> List[str]:
        """Extract explanations for changed values from TOB data."""
        skip_keys = skip_keys or set()
        explanation_with_category = []
        explanations = []

        if isinstance(tob_json, list):  # Handle multi-category TOB
            for category in tob_json:
                category_name = category.get("category_name", {}).get("value", "Unknown")
                for key, val in category.items():
                    if key in skip_keys or not isinstance(val, dict):
                        continue
                    if val.get("changed"):
                        explanation = val.get("explanation", "")
                        if explanation:
                            explanations.append(f"{explanation}")
                explanation_with_category.append({category_name: explanations})
        elif isinstance(tob_json, dict):  # Single dictionary case (fail-safe)
            category_name = tob_json.get("category_name", {}).get("value", "Unknown")
            for key, val in tob_json.items():
                if key in skip_keys or not isinstance(val, dict):
                    continue
                if val.get("changed"):
                    explanation = val.get("explanation", "")
                    if explanation:
                        explanations.append(f"{explanation}")
            explanation_with_category.append({category_name: explanations})

        return explanation_with_category
    
    async def _send_missing_census_email(self, sender_email: str):
        """Send email for missing census file."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.thread_pool,
            email_service.send_missing_census_email,
            sender_email
        )
    
    async def _send_missing_documents_email(self, sender_email: str):
        """Send email for missing documents."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.thread_pool,
            email_service.send_insufficient_attachments_email,
            sender_email
        )
    
    async def _log_quotation_event(self, quotation_id: int, event_type: str, 
                                  description: str = None, request_data: dict = None, 
                                  response_data: dict = None):
        """Log quotation event."""
        def log_event():
            try:
                db = get_db_session()
                crud.create_log(
                    db=db, 
                    quotation_id=quotation_id, 
                    event_type=event_type,
                    description=description,
                    request_data=request_data,
                    response_data=response_data
                )
                db.close()
            except Exception as e:
                print(f"Error logging event: {e}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.thread_pool, log_event)
    
    async def _update_quotation_status(self, db, quotation_id: int, status):
        """Update quotation status."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.thread_pool, 
            crud.update_quotation_status, 
            db, quotation_id, status
        )
    
    def _cleanup_files(self, *file_paths):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up {file_path}: {e}")