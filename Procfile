# Web interface for viewing audit events log records
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0

# One-off dyno commands for database management
db-init: python db_manager.py init
db-cleanup: python db_manager.py cleanup
