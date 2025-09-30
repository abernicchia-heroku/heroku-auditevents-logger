#!/usr/bin/env python3
"""
Test script for the Heroku Audit Events Logger
Run this script to test the application functionality locally
"""

import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test if required environment variables are set"""
    print("Testing environment variables...")
    
    required_vars = ['HEROKU_API_TOKEN', 'HEROKU_ACCOUNT_ID_OR_NAME', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import requests
        import psycopg2
        from psycopg2.extras import RealDictCursor
        print("✅ All required modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install required dependencies: pip install -r requirements.txt")
        return False

def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    
    try:
        from app import AuditEventsLogger
        logger = AuditEventsLogger()
        logger.init_database()
        print("✅ Database connection and initialization successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_api_connection():
    """Test Heroku API connection"""
    print("Testing Heroku API connection...")
    
    try:
        from app import AuditEventsLogger
        logger = AuditEventsLogger()
        
        # Test with yesterday's date
        test_date = date.today() - timedelta(days=1)
        result = logger.get_audit_events(test_date)
        
        if result['success']:
            print(f"✅ API connection successful, retrieved {result['count']} events for {test_date}")
            return True
        else:
            print(f"❌ API request failed: {result['error']}")
            return False
    except Exception as e:
        print(f"❌ API connection test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Heroku Audit Events Logger Tests\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("Module Imports", test_imports),
        ("Database Connection", test_database_connection),
        ("API Connection", test_api_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed! The application is ready to deploy.")
        print("📝 Next steps:")
        print("   1. Deploy to Heroku: git push heroku main")
        print("   2. Add Heroku Scheduler addon")
        print("   3. Configure daily job: python app.py")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix the issues before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
