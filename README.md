# Heroku Audit Events Logger

A Python script that runs on Heroku via the Heroku Scheduler addon to retrieve and log audit trail events from the Heroku Platform API on a daily basis.

## Features

- **Daily Processing**: Retrieves audit events from the previous day when triggered
- **Duplicate Prevention**: Checks if events for a date have already been processed
- **Concurrency Safety**: Atomic database locking prevents multiple processes from processing the same date
- **Database Logging**: Stores processing status and results in PostgreSQL
- **External Scheduling**: Designed to run via Heroku Scheduler addon
- **Error Handling**: Comprehensive error handling and logging
- **Simple Execution**: Single command-line script with no web server
- **Stuck Process Cleanup**: Automatically cleans up stuck processing records

## Setup

### 1. Environment Variables

Set the following environment variables in your Heroku app:

```bash
# Required: Heroku API Token
HEROKU_API_TOKEN=your_heroku_api_token_here

# Optional: Port (automatically set by Heroku)
PORT=5000
```

The `DATABASE_URL` is automatically provided when you add the Heroku Postgres addon.

### 2. Getting a Heroku API Token

1. Go to your Heroku account settings
2. Navigate to the "API Key" section
3. Generate a new API key or copy your existing one
4. Set it as the `HEROKU_API_TOKEN` environment variable

### 3. Deploy to Heroku

```bash
# Initialize git repository (if not already done)
git init

# Add Heroku remote
heroku create your-app-name

# Add Heroku Postgres addon
heroku addons:create heroku-postgresql:mini

# Add Heroku Scheduler addon
heroku addons:create scheduler:standard

# Set environment variables
heroku config:set HEROKU_API_TOKEN=your_actual_token_here

# Deploy
git add .
git commit -m "Initial commit"
git push heroku main
```

### 4. Configure Heroku Scheduler

After deployment, configure the Heroku Scheduler addon:

1. Go to your Heroku app dashboard
2. Click on the "Heroku Scheduler" addon
3. Create a new job with:
   - **Command**: `python app.py`
   - **Frequency**: Daily at your preferred time (e.g., 2:00 AM UTC)
   - **Dyno Size**: Basic or Standard (depending on your needs)

## Manual Execution

You can also run the script manually for testing or one-off processing:

```bash
# Run via Heroku CLI
heroku run python app.py

# Or run locally (with proper environment variables set)
python app.py
```

### Database Management Commands

The application includes one-off dyno commands for database management:

```bash
# Initialize database tables and indexes
heroku run db-init

# Clean up stuck processes
heroku run db-cleanup

# Show processing status
heroku run python db_manager.py status

# Reset processing for a specific date
heroku run python db_manager.py reset 2024-09-28
```

**Note**: The `db-init` and `db-cleanup` commands are defined in the Procfile as one-off dyno processes, making them easy to run via the Heroku CLI.

## Database Management

The application uses **SQLAlchemy ORM** and **Alembic** for database management, providing:

- **Object-Relational Mapping**: Clean, Pythonic database operations
- **Automatic Migrations**: Version-controlled database schema changes
- **Type Safety**: Strong typing for database operations
- **Connection Management**: Proper connection pooling and cleanup

### Database Schema

The application creates a `audit_events_log` table with the following structure:

```python
class AuditEventsLog(Base):
    __tablename__ = 'audit_events_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    process_date = Column(Date, nullable=False, unique=True)
    status = Column(String(20), nullable=False)
    events_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Database Indexes

The application automatically creates indexes to optimize query performance:

- **`idx_audit_events_log_status`**: Optimizes status-based queries (cleanup operations)
- **`idx_audit_events_log_process_date_status`**: Composite index for lock release operations

Note: The `process_date` column has a UNIQUE constraint which automatically creates an index, so no additional index is needed for that column.

### Database Migrations

The application uses Alembic for database migrations:

```bash
# Run migrations (automatically handled by the application)
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# View migration history
alembic history

# Rollback to previous version
alembic downgrade -1
```

## Scheduling

The application is designed to run via the Heroku Scheduler addon. When triggered, it automatically processes audit events from the previous day. The script reads the current date and calculates the previous day's date for processing.

## Error Handling

The application handles various error scenarios:

- **API Authentication Errors**: Invalid or missing API token
- **Network Errors**: Connection timeouts or network issues
- **Database Errors**: Connection or query failures
- **Duplicate Processing**: Prevents processing the same date twice
- **Concurrent Execution**: Atomic database locking prevents race conditions
- **Stuck Processes**: Automatic cleanup of processes that didn't complete properly

## Logging

All operations are logged with appropriate log levels:
- `INFO`: Normal operations and successful processing
- `WARNING`: Non-critical issues (e.g., skipped scheduled job)
- `ERROR`: Failed operations and exceptions

## Monitoring

You can monitor the application through:

1. **Heroku Logs**: `heroku logs --tail`
2. **Heroku Scheduler**: Check job execution history in the Scheduler addon
3. **Database**: Query the `audit_events_log` table directly
4. **Manual Execution**: Run `heroku run python app.py` to test manually

## Development

To run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export HEROKU_API_TOKEN=your_token_here
export DATABASE_URL=your_local_postgres_url

# Run database migrations (if needed)
alembic upgrade head

# Run the application
python app.py
```

### Database Development

For database development and migrations:

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "Add new field to model"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1

# View migration history
alembic history --verbose
```

## Requirements

- Python 3.11.6
- Heroku API token with appropriate permissions
- Heroku Postgres database
- Internet connectivity for API calls
