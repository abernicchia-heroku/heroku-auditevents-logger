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
    page_icon="🟣",
    layout="wide"
)

# Custom CSS for Heroku-inspired purple theme
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --heroku-purple: #6762A6;
        --heroku-dark-purple: #5A4FCF;
        --heroku-light-purple: #8B7ED8;
        --heroku-accent: #E8E6FF;
        --heroku-success: #00D924;
        --heroku-warning: #FFB000;
        --heroku-error: #FF6B6B;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, var(--heroku-purple) 0%, var(--heroku-dark-purple) 100%);
        padding: 2rem 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(103, 98, 166, 0.3);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: var(--heroku-accent);
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid var(--heroku-purple);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Status badges */
    .status-success {
        background-color: var(--heroku-success);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-failed {
        background-color: var(--heroku-error);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-processing {
        background-color: var(--heroku-warning);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, var(--heroku-purple) 0%, var(--heroku-dark-purple) 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(103, 98, 166, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(103, 98, 166, 0.4);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: var(--heroku-accent);
        border-radius: 8px;
        border: 1px solid var(--heroku-light-purple);
    }
    
    /* Data table styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Version info styling */
    .version-info {
        background: linear-gradient(135deg, #f8f9ff 0%, var(--heroku-accent) 100%);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--heroku-light-purple);
        margin: 1rem 0;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: var(--heroku-purple);
        border-top: 1px solid var(--heroku-accent);
        margin-top: 3rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize database manager
@st.cache_resource
def get_db_manager():
    return DatabaseManager()

@st.cache_data
def get_version_info():
    """Get version information from build-time file and runtime environment variables"""
    version_info = {
        'git_hash': 'unknown',
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
        version_info['git_hash'] = os.environ.get('SOURCE_VERSION', 'unknown')
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
    # Custom header with Heroku styling
    st.markdown("""
    <div class="main-header">
        <h1>🟣 Heroku Audit Events Logger</h1>
        <p>Monitor, filter, and manage your audit events processing logs</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display version information
    version_info = get_version_info()
    
    # Create expandable version info section with custom styling
    with st.expander("🔧 Version & Deployment Information", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # Show short version of git hash (first 8 characters)
            git_hash_short = version_info['git_hash'][:8] if version_info['git_hash'] != 'unknown' and len(version_info['git_hash']) > 8 else version_info['git_hash']
            st.write(f"**Git Commit:** `{git_hash_short}`")
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
        
        # Show full commit hash if available and longer than 8 characters
        if version_info['git_hash'] != 'unknown' and len(version_info['git_hash']) > 8:
            st.code(f"Full commit hash: {version_info['git_hash']}", language=None)
    
    # Sidebar for filters with enhanced styling
    st.sidebar.markdown("""
    <div style="background: linear-gradient(135deg, var(--heroku-purple) 0%, var(--heroku-dark-purple) 100%); 
                padding: 1rem; border-radius: 8px; margin-bottom: 1rem; text-align: center;">
        <h2 style="color: white; margin: 0; font-size: 1.5rem;">🔍 Filters</h2>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        # Display table with enhanced Heroku-style color coding
        def color_status(val):
            if val == 'SUCCESS':
                return 'background-color: #e8f5e8; color: #00D924; font-weight: 600; border-radius: 4px; padding: 2px 8px;'
            elif val == 'FAILED':
                return 'background-color: #ffe8e8; color: #FF6B6B; font-weight: 600; border-radius: 4px; padding: 2px 8px;'
            elif val == 'ERROR':
                return 'background-color: #ffe8e8; color: #FF6B6B; font-weight: 600; border-radius: 4px; padding: 2px 8px;'
            elif val == 'PROCESSING':
                return 'background-color: #fff8e1; color: #FFB000; font-weight: 600; border-radius: 4px; padding: 2px 8px;'
            return ''
        
        # Apply Heroku-inspired styling to the dataframe
        styled_df = df.style.applymap(color_status, subset=['Status']).set_table_styles([
            {'selector': 'thead th', 'props': [
                ('background-color', 'var(--heroku-purple)'),
                ('color', 'white'),
                ('font-weight', '600'),
                ('text-align', 'center'),
                ('padding', '12px'),
                ('border', 'none')
            ]},
            {'selector': 'tbody td', 'props': [
                ('padding', '10px'),
                ('border-bottom', '1px solid #E8E6FF'),
                ('text-align', 'center')
            ]},
            {'selector': 'tbody tr:hover', 'props': [
                ('background-color', '#f8f9ff')
            ]}
        ])
        
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
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: var(--heroku-purple); margin: 0;">📊 Total Records</h3>
                <h2 style="margin: 0.5rem 0 0 0; color: #333;">{total_records}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            successful_records = len([r for r in log_records if r.status == 'SUCCESS'])
            success_rate = (successful_records / total_records * 100) if total_records > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: var(--heroku-success); margin: 0;">✅ Successful</h3>
                <h2 style="margin: 0.5rem 0 0 0; color: #333;">{successful_records}</h2>
                <p style="margin: 0; color: #666; font-size: 0.9rem;">{success_rate:.1f}% success rate</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            failed_records = len([r for r in log_records if r.status in ['FAILED', 'ERROR']])
            failure_rate = (failed_records / total_records * 100) if total_records > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: var(--heroku-error); margin: 0;">❌ Failed</h3>
                <h2 style="margin: 0.5rem 0 0 0; color: #333;">{failed_records}</h2>
                <p style="margin: 0; color: #666; font-size: 0.9rem;">{failure_rate:.1f}% failure rate</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            total_events = sum([r.events_count for r in log_records if r.events_count])
            avg_events = (total_events / successful_records) if successful_records > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: var(--heroku-dark-purple); margin: 0;">🎯 Total Events</h3>
                <h2 style="margin: 0.5rem 0 0 0; color: #333;">{total_events:,}</h2>
                <p style="margin: 0; color: #666; font-size: 0.9rem;">{avg_events:.1f} avg per success</p>
            </div>
            """, unsafe_allow_html=True)
        
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
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>🟣 Powered by Heroku • Built with Streamlit • Audit Events Logger v1.0</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
