"""
Streamlit web interface for Heroku Audit Events Logger
Displays and manages audit events log records (processing status)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
import os

from models import DatabaseManager, AuditEventsLog

# Configure Streamlit page
st.set_page_config(
    page_title="Heroku Audit Events Logger",
    page_icon="🔍",
    layout="wide"
)

# Initialize database manager
@st.cache_resource
def get_db_manager():
    return DatabaseManager()

@st.cache_data
def get_version_info():
    """Get version information from build-time file and runtime environment variables"""
    version_info = {
        'git_hash': 'unknown',
        'git_hash_full': 'unknown',
        'build_time': 'unknown',
        'stack': 'unknown'
    }
    
    # Get build-time information from version.json file
    try:
        with open('version.json', 'r') as f:
            file_version_info = json.load(f)
            version_info.update(file_version_info)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback: get build-time info from environment variables
        version_info['git_hash'] = os.environ.get('SOURCE_VERSION', 'unknown')[:8] if os.environ.get('SOURCE_VERSION') else 'unknown'
        version_info['git_hash_full'] = os.environ.get('SOURCE_VERSION', 'unknown')
        version_info['stack'] = os.environ.get('STACK', 'unknown')
    
    # Get runtime information from Heroku dyno metadata (available only at runtime)
    version_info['heroku_release'] = os.environ.get('HEROKU_RELEASE_VERSION', 'unknown')
    version_info['heroku_slug'] = os.environ.get('HEROKU_SLUG_COMMIT', 'unknown')
    version_info['deployment_time'] = os.environ.get('HEROKU_RELEASE_CREATED_AT', 'unknown')
    version_info['app_name'] = os.environ.get('HEROKU_APP_NAME', 'unknown')
    version_info['dyno_id'] = os.environ.get('HEROKU_DYNO_ID', 'unknown')
    
    return version_info

def get_audit_events_logs(filters=None, limit=1000):
    """Get audit events log records with optional filters"""
    db_manager = get_db_manager()
    
    with db_manager.get_session() as session:
        query = session.query(AuditEventsLog)
        
        if filters:
            if filters.get('status'):
                query = query.filter(AuditEventsLog.status == filters['status'])
            if filters.get('date_from'):
                query = query.filter(AuditEventsLog.process_date >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(AuditEventsLog.process_date <= filters['date_to'])
        
        # Order by process_date descending (newest first)
        query = query.order_by(AuditEventsLog.process_date.desc())
        
        # Apply limit
        query = query.limit(limit)
        
        return query.all()

def delete_audit_events_logs(record_ids):
    """Delete audit events log records by IDs"""
    db_manager = get_db_manager()
    
    with db_manager.get_session() as session:
        deleted_count = session.query(AuditEventsLog).filter(
            AuditEventsLog.id.in_(record_ids)
        ).delete(synchronize_session=False)
        
        session.commit()
        return deleted_count

def main():
    st.title("🔍 Heroku Audit Events Logger")
    st.markdown("View, filter, and manage audit events processing logs")
    
    # Display version information
    version_info = get_version_info()
    
    # Create expandable version info section
    with st.expander("ℹ️ Version Information", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Git Commit:** `{version_info['git_hash']}`")
            if version_info['heroku_release'] != 'unknown':
                st.write(f"**Heroku Release:** `{version_info['heroku_release']}`")
            if version_info['stack'] != 'unknown':
                st.write(f"**Heroku Stack:** `{version_info['stack']}`")
            if version_info['app_name'] != 'unknown':
                st.write(f"**App Name:** `{version_info['app_name']}`")
        
        with col2:
            if version_info.get('build_time', 'unknown') != 'unknown':
                st.write(f"**Build Time:** {version_info['build_time']}")
            if version_info.get('deployment_time', 'unknown') != 'unknown':
                st.write(f"**Deployed At:** {version_info['deployment_time']}")
            if version_info.get('heroku_slug', 'unknown') != 'unknown' and len(version_info.get('heroku_slug', '')) > 8:
                st.write(f"**Slug Commit:** `{version_info['heroku_slug'][:8]}`")
            if version_info['dyno_id'] != 'unknown':
                st.write(f"**Dyno ID:** `{version_info['dyno_id'][:8]}...`")
        
        # Show full commit hash if available
        if version_info['git_hash_full'] != 'unknown' and len(version_info['git_hash_full']) > 8:
            st.code(f"Full commit hash: {version_info['git_hash_full']}", language=None)
    
    # Sidebar for filters
    st.sidebar.header("Filters")
    
    # Date range filter
    col1, col2 = st.sidebar.columns(2)
    with col1:
        date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
    with col2:
        date_to = st.date_input("To Date", value=date.today())
    
    # Status filter
    status_options = ["All", "SUCCESS", "FAILED", "ERROR", "PROCESSING"]
    status = st.sidebar.selectbox("Status", status_options)
    
    # Build filters
    filters = {}
    if status != "All":
        filters['status'] = status
    if date_from:
        filters['date_from'] = date_from
    if date_to:
        filters['date_to'] = date_to
    
    # Main content area
    st.header("Audit Events Processing Logs")
    
    # Get log records
    log_records = get_audit_events_logs(filters)
    
    if not log_records:
        st.info("No log records found matching the selected filters.")
    else:
        st.success(f"Found {len(log_records)} log records")
        
        # Convert to DataFrame for display
        logs_data = []
        for record in log_records:
            logs_data.append({
                'ID': record.id,
                'Process Date': record.process_date.strftime('%Y-%m-%d'),
                'Status': record.status,
                'Events Count': record.events_count,
                'Error Message': record.error_message or '',
                'Created At': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Updated At': record.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(logs_data)
        
        # Display records with selection
        selected_indices = st.multiselect(
            "Select log records to delete:",
            options=df.index,
            format_func=lambda x: f"Date: {df.iloc[x]['Process Date']} - Status: {df.iloc[x]['Status']} - Events: {df.iloc[x]['Events Count']}"
        )
        
        # Delete button
        if selected_indices:
            if st.button("🗑️ Delete Selected Records", type="primary"):
                selected_ids = [df.iloc[idx]['ID'] for idx in selected_indices]
                deleted_count = delete_audit_events_logs(selected_ids)
                st.success(f"Deleted {deleted_count} log records")
                st.rerun()
        
        # Display table with color coding
        def color_status(val):
            if val == 'SUCCESS':
                return 'background-color: #d4edda; color: #155724'
            elif val == 'FAILED':
                return 'background-color: #f8d7da; color: #721c24'
            elif val == 'ERROR':
                return 'background-color: #f8d7da; color: #721c24'
            elif val == 'PROCESSING':
                return 'background-color: #fff3cd; color: #856404'
            return ''
        
        styled_df = df.style.applymap(color_status, subset=['Status'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Process Date": st.column_config.DateColumn("Process Date", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Events Count": st.column_config.NumberColumn("Events Count", width="small"),
                "Error Message": st.column_config.TextColumn("Error Message", width="large"),
                "Created At": st.column_config.DatetimeColumn("Created At", width="medium"),
                "Updated At": st.column_config.DatetimeColumn("Updated At", width="medium")
            }
        )
        
        # Summary statistics
        st.subheader("Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_records = len(log_records)
            st.metric("Total Records", total_records)
        
        with col2:
            successful_records = len([r for r in log_records if r.status == 'SUCCESS'])
            st.metric("Successful", successful_records)
        
        with col3:
            failed_records = len([r for r in log_records if r.status in ['FAILED', 'ERROR']])
            st.metric("Failed", failed_records)
        
        with col4:
            total_events = sum([r.events_count for r in log_records if r.events_count])
            st.metric("Total Events", total_events)
        
        # Show detailed information for selected record
        if selected_indices and len(selected_indices) == 1:
            selected_record = log_records[selected_indices[0]]
            st.subheader("Selected Record Details")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**ID:** {selected_record.id}")
                st.write(f"**Process Date:** {selected_record.process_date}")
                st.write(f"**Status:** {selected_record.status}")
                st.write(f"**Events Count:** {selected_record.events_count}")
            
            with col2:
                st.write(f"**Created At:** {selected_record.created_at}")
                st.write(f"**Updated At:** {selected_record.updated_at}")
                if selected_record.error_message:
                    st.write(f"**Error Message:** {selected_record.error_message}")

if __name__ == "__main__":
    main()
