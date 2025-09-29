#!/usr/bin/env python3
"""
Database management utility for Heroku Audit Events Logger.
Provides convenient commands for database operations.
"""

import sys
import argparse
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

from models import DatabaseManager, AuditEventsLog

# Load environment variables
load_dotenv()

def init_database():
    """Initialize database tables"""
    print("🔧 Initializing database...")
    db_manager = DatabaseManager()
    try:
        db_manager.create_tables()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        sys.exit(1)
    finally:
        db_manager.close()

def show_status():
    """Show recent processing status"""
    print("📊 Recent processing status:")
    db_manager = DatabaseManager()
    try:
        with db_manager.get_session() as session:
            # Get last 10 records
            records = session.query(AuditEventsLog).order_by(
                AuditEventsLog.process_date.desc()
            ).limit(10).all()
            
            if not records:
                print("No records found")
                return
            
            print(f"{'Date':<12} {'Status':<12} {'Events':<8} {'Created':<20}")
            print("-" * 60)
            
            for record in records:
                created_str = record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else 'N/A'
                print(f"{record.process_date} {record.status:<12} {record.events_count:<8} {created_str}")
                
    except Exception as e:
        print(f"❌ Failed to get status: {e}")
        sys.exit(1)
    finally:
        db_manager.close()

def cleanup_stuck():
    """Clean up stuck processes"""
    print("🧹 Cleaning up stuck processes...")
    db_manager = DatabaseManager()
    try:
        with db_manager.get_session() as session:
            from sqlalchemy import and_
            
            # Find stuck PROCESSING records older than 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            stuck_records = session.query(AuditEventsLog).filter(
                and_(
                    AuditEventsLog.status == 'PROCESSING',
                    AuditEventsLog.created_at < cutoff_time
                )
            ).all()
            
            if stuck_records:
                for record in stuck_records:
                    record.status = 'ERROR'
                    record.error_message = 'Process was stuck and cleaned up'
                    record.updated_at = datetime.utcnow()
                
                session.commit()
                print(f"✅ Cleaned up {len(stuck_records)} stuck processes")
            else:
                print("✅ No stuck processes found")
                
    except Exception as e:
        print(f"❌ Failed to cleanup stuck processes: {e}")
        sys.exit(1)
    finally:
        db_manager.close()

def reset_date(target_date_str):
    """Reset processing for a specific date"""
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    print(f"🔄 Resetting processing for {target_date}...")
    db_manager = DatabaseManager()
    try:
        with db_manager.get_session() as session:
            record = session.query(AuditEventsLog).filter(
                AuditEventsLog.process_date == target_date
            ).first()
            
            if record:
                session.delete(record)
                session.commit()
                print(f"✅ Deleted record for {target_date}")
            else:
                print(f"ℹ️  No record found for {target_date}")
                
    except Exception as e:
        print(f"❌ Failed to reset date: {e}")
        sys.exit(1)
    finally:
        db_manager.close()

def main():
    parser = argparse.ArgumentParser(description='Database management utility')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize database tables')
    
    # Status command
    subparsers.add_parser('status', help='Show recent processing status')
    
    # Cleanup command
    subparsers.add_parser('cleanup', help='Clean up stuck processes')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset processing for a specific date')
    reset_parser.add_argument('date', help='Date to reset (YYYY-MM-DD format)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'init':
        init_database()
    elif args.command == 'status':
        show_status()
    elif args.command == 'cleanup':
        cleanup_stuck()
    elif args.command == 'reset':
        reset_date(args.date)

if __name__ == '__main__':
    main()
