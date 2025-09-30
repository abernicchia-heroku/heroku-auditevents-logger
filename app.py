import os
import logging
import sys
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import DatabaseManager, AuditEventsLog

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuditEventsLogger:
    def __init__(self):
        self.heroku_api_token = os.getenv('HEROKU_API_TOKEN')
        self.heroku_account_id = os.getenv('HEROKU_ACCOUNT_ID_OR_NAME')
        
        # Optional filtering parameters
        self.filter_type = os.getenv('FILTER_TYPE')
        self.filter_action = os.getenv('FILTER_ACTION')
        self.filter_actor_email = os.getenv('FILTER_ACTOR_EMAIL')
        
        if not self.heroku_api_token:
            raise ValueError("HEROKU_API_TOKEN environment variable is required")
        if not self.heroku_account_id:
            raise ValueError("HEROKU_ACCOUNT_ID_OR_NAME environment variable is required")
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
    
    def init_database(self):
        """Initialize database tables using SQLAlchemy"""
        try:
            # Create all tables (this will also create indexes defined in the model)
            self.db_manager.create_tables()
            logger.info("Database tables and indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def check_existing_process(self, target_date: date) -> Optional[AuditEventsLog]:
        """Check if there's already a record for the given date"""
        try:
            with self.db_manager.get_session() as session:
                return session.query(AuditEventsLog).filter(
                    AuditEventsLog.process_date == target_date
                ).first()
        except Exception as e:
            logger.error(f"Failed to check existing process: {e}")
            raise
    
    def acquire_processing_lock(self, target_date: date) -> bool:
        """Atomically acquire a processing lock for the given date"""
        try:
            with self.db_manager.get_session() as session:
                # Try to insert a "PROCESSING" record atomically
                new_record = AuditEventsLog(
                    process_date=target_date,
                    status='PROCESSING',
                    events_count=0
                )
                
                try:
                    session.add(new_record)
                    session.commit()
                    logger.info(f"Acquired processing lock for {target_date}")
                    return True
                except IntegrityError:
                    # Record already exists
                    session.rollback()
                    logger.info(f"Could not acquire processing lock for {target_date} - already exists")
                    return False
        except Exception as e:
            logger.error(f"Failed to acquire processing lock: {e}")
            raise
    
    def release_processing_lock(self, target_date: date, final_status: str, events_count: int = 0, error_message: str = None):
        """Update the processing record with final status"""
        try:
            with self.db_manager.get_session() as session:
                # Find the record with PROCESSING status
                record = session.query(AuditEventsLog).filter(
                    AuditEventsLog.process_date == target_date,
                    AuditEventsLog.status == 'PROCESSING'
                ).first()
                
                if record:
                    record.status = final_status
                    record.events_count = events_count
                    record.error_message = error_message
                    record.updated_at = datetime.utcnow()
                    session.commit()
                    logger.info(f"Released processing lock for {target_date} with status: {final_status}")
                else:
                    logger.warning(f"No processing record found to update for {target_date}")
        except Exception as e:
            logger.error(f"Failed to release processing lock: {e}")
            raise
    
    def cleanup_stuck_processes(self, hours_threshold: int = 24):
        """Clean up any stuck PROCESSING records older than the threshold"""
        try:
            with self.db_manager.get_session() as session:
                from sqlalchemy import and_
                
                # Calculate the cutoff time
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
                
                # Find stuck PROCESSING records
                stuck_records = session.query(AuditEventsLog).filter(
                    and_(
                        AuditEventsLog.status == 'PROCESSING',
                        AuditEventsLog.created_at < cutoff_time
                    )
                ).all()
                
                # Update them to ERROR status
                for record in stuck_records:
                    record.status = 'ERROR'
                    record.error_message = 'Process was stuck and cleaned up'
                    record.updated_at = datetime.utcnow()
                
                session.commit()
                
                if stuck_records:
                    logger.info(f"Cleaned up {len(stuck_records)} stuck processing records")
                else:
                    logger.info("No stuck processing records found")
        except Exception as e:
            logger.error(f"Failed to cleanup stuck processes: {e}")
            raise
    
    def _parse_heroku_api_error(self, response) -> str:
        """Parse Heroku API error response according to their documentation"""
        # Check if response has content
        response_text = response.text.strip() if response.text else ""
        
        if not response_text:
            # Empty response - provide generic error based on status code
            status_messages = {
                400: "Bad Request",
                401: "Unauthorized - Invalid or missing API token",
                403: "Forbidden - Insufficient permissions",
                404: "Not Found - Resource not found (check account ID/name)",
                429: "Too Many Requests - Rate limit exceeded",
                500: "Internal Server Error",
                502: "Bad Gateway",
                503: "Service Unavailable"
            }
            return status_messages.get(response.status_code, f"HTTP {response.status_code} error")
        
        try:
            # Try to parse JSON error response
            error_data = response.json()
            
            # Heroku API errors have this structure:
            # {
            #   "id": "not_found",
            #   "message": "Couldn't find that resource."
            # }
            error_id = error_data.get('id', 'unknown_error')
            error_message = error_data.get('message', 'No error message provided')
            
            # Also check for additional error details if available
            error_details = []
            if 'details' in error_data:
                error_details.append(f"Details: {error_data['details']}")
            if 'url' in error_data:
                error_details.append(f"URL: {error_data['url']}")
            
            # Build comprehensive error message
            full_error = f"{error_id}: {error_message}"
            if error_details:
                full_error += f" ({'; '.join(error_details)})"
                
            return full_error
            
        except (ValueError, KeyError) as e:
            # If JSON parsing fails, fall back to raw response text
            logger.warning(f"Failed to parse Heroku API error response: {e}")
            return response_text or f"Unknown error (status {response.status_code})"

    def log_audit_events(self, events: list):
        """Log the required attributes of audit events"""
        for event in events:
            # Extract and log the required attributes
            event_created_at = event.get('created_at')
            actor_email = event.get('actor', {}).get('email') if event.get('actor') else None
            event_type = event.get('type')
            event_action = event.get('action')
            
            # Log the required attributes
            logger.info(f"Event: created_at={event_created_at}, actor.email={actor_email}, type={event_type}, action={event_action}")
    
    def get_audit_events(self, target_date: date) -> Dict[str, Any]:
        """Retrieve audit events from Heroku API for the given date"""
        # Format date for API (YYYY-MM-DD format)
        day_param = target_date.strftime('%Y-%m-%d')
        
        headers = {
            'Authorization': f'Bearer {self.heroku_api_token}',
            'Accept': 'application/vnd.heroku+json; version=3',
            'Content-Type': 'application/json'
        }
        
        # Get account ID or name from environment variable
        account_id = os.getenv('HEROKU_ACCOUNT_ID_OR_NAME')
        if not account_id:
            raise ValueError("HEROKU_ACCOUNT_ID_OR_NAME environment variable is required")
        
        logger.info(f"Using Heroku Account ID/Name: {account_id}")
        
        # API endpoint for audit trail events
        url = f'https://api.heroku.com/enterprise-accounts/{account_id}/events'
        
        # Parameters for the API call
        params = {
            'day': day_param,
            'order': 'asc'
        }
        
        # Add optional filters
        if self.filter_type:
            params['type'] = self.filter_type
        if self.filter_action:
            params['action'] = self.filter_action
        if self.filter_actor_email:
            params['actor'] = self.filter_actor_email
        
        try:
            logger.info(f"Fetching audit events for day {day_param}")
            logger.info(f"API Endpoint: {url}")
            logger.info(f"Request Parameters: {params}")
            
            # Log headers with masked Authorization token for security
            safe_headers = dict(headers)
            if 'Authorization' in safe_headers:
                safe_headers['Authorization'] = 'Bearer [MASKED]'
            logger.info(f"Request Headers: {safe_headers}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Log response details for debugging
            logger.info(f"Response Status Code: {response.status_code}")
            # to avoid logging the token
            #logger.info(f"Response Headers: {dict(response.headers)}")
            
            # Log the complete response body for debugging
            logger.info(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('data', [])
                logger.info(f"Successfully retrieved {len(events)} audit events for {target_date}")
                
                # Log the required attributes of each event
                if events:
                    self.log_audit_events(events)
                
                return {
                    'success': True,
                    'events': events,
                    'count': len(events)
                }
            else:
                # Parse Heroku API error response according to their documentation
                error_details = self._parse_heroku_api_error(response)
                error_msg = f"API request failed with status {response.status_code}: {error_details}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'events': [],
                    'count': 0
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'events': [],
                'count': 0
            }
    
    def process_audit_events(self, target_date: date = None):
        """Main process to retrieve and log audit events"""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"Starting audit events processing for {target_date}")
        
        # Check if there's already a completed record for this date
        existing_record = self.check_existing_process(target_date)
        if existing_record and existing_record.status in ['SUCCESS', 'FAILED', 'ERROR']:
            logger.info(f"Process already completed for {target_date} with status: {existing_record.status}")
            return False
        
        # Try to acquire processing lock atomically
        if not self.acquire_processing_lock(target_date):
            logger.info(f"Another process is already handling {target_date} or it's already completed")
            return False
        
        try:
            # Retrieve audit events
            result = self.get_audit_events(target_date)
            
            if result['success']:
                # Update with successful processing
                self.release_processing_lock(
                    target_date=target_date,
                    final_status='SUCCESS',
                    events_count=result['count']
                )
                logger.info(f"Successfully processed {result['count']} audit events for {target_date}")
                return True
            else:
                # Update with failed processing
                self.release_processing_lock(
                    target_date=target_date,
                    final_status='FAILED',
                    events_count=0,
                    error_message=result['error']
                )
                logger.error(f"Failed to process audit events for {target_date}: {result['error']}")
                return False
                
        except Exception as e:
            # Update with unexpected error
            error_msg = f"Unexpected error: {e}"
            self.release_processing_lock(
                target_date=target_date,
                final_status='ERROR',
                events_count=0,
                error_message=error_msg
            )
            logger.error(f"Unexpected error processing audit events for {target_date}: {e}")
            return False

def main():
    """Main function to run the audit events processing"""
    audit_logger = None
    try:
        # Initialize the logger
        audit_logger = AuditEventsLogger()
        
        # Initialize database
        audit_logger.init_database()
        
        # Clean up any stuck processes from previous runs
        audit_logger.cleanup_stuck_processes()
        
        # Process audit events for previous day
        success = audit_logger.process_audit_events()
        
        if success:
            logger.info("Audit events processing completed successfully")
            sys.exit(0)
        else:
            logger.error("Audit events processing failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Clean up database connections
        if audit_logger and audit_logger.db_manager:
            audit_logger.db_manager.close()

if __name__ == '__main__':
    main()
