#!/usr/bin/env python3
"""
Comprehensive health check for Wellx Quotation AI
Can be used for monitoring and debugging
"""

import asyncio
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

async def check_redis():
    """Check Redis connection"""
    try:
        from src.services.storage.redis_manager import redis_manager
        await redis_manager.connect()
        await redis_manager.redis_client.ping()
        await redis_manager.disconnect()
        return True, "Redis connection successful"
    except Exception as e:
        return False, f"Redis connection failed: {e}"

async def check_database():
    """Check database connection"""
    try:
        from src.database.database import get_db_session
        from sqlalchemy import text
        
        db = get_db_session()
        result = db.execute(text("SELECT 1"))
        db.close()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {e}"

async def check_gcs():
    """Check Google Cloud Storage"""
    try:
        from src.services.storage.gcs_manager import GCSManager
        gcs = GCSManager()
        # Just initialize, don't actually upload
        return True, "GCS client initialized successfully"
    except Exception as e:
        return False, f"GCS initialization failed: {e}"

async def check_env_vars():
    """Check required environment variables"""
    required_vars = [
        'DB_HOST', 'DB_NAME', 'DB_USER',
        'REDIS_URL', 'GCS_BUCKET_NAME',
        'TENANT_ID', 'CLIENT_ID'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        return False, f"Missing environment variables: {', '.join(missing)}"
    return True, "All required environment variables present"

async def main():
    """Run comprehensive health check"""
    print("🏥 Wellx Quotation AI - Health Check")
    print("=" * 50)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    checks = [
        ("Environment Variables", check_env_vars()),
        ("Database", check_database()),
        ("Redis", check_redis()),
        ("Google Cloud Storage", check_gcs())
    ]
    
    all_passed = True
    
    for name, check_coro in checks:
        print(f"Checking {name}...")
        try:
            success, message = await check_coro
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {message}")
            if not success:
                all_passed = False
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            all_passed = False
        print()
    
    print("=" * 50)
    if all_passed:
        print("✅ All health checks passed!")
        sys.exit(0)
    else:
        print("❌ Some health checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())