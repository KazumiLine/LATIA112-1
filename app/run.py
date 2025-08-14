#!/usr/bin/env python3
"""
Main entry point for the intelligent e-commerce platform
Supports running web API, LINE bot, or both services
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_web_api():
    """Run the Flask web API"""
    from .web_api import app
    print("🚀 Starting Flask Web API...")
    print(f"📱 Web Interface: http://localhost:5000")
    print(f"🔧 Admin Panel: http://localhost:5000/admin")
    print(f"📊 API Endpoints: http://localhost:5000/api/*")
    app.run(debug=True, host='0.0.0.0', port=5000)

def run_line_bot():
    """Run the LINE Bot service"""
    from .line_bot import create_line_app
    app = create_line_app()
    print("🤖 Starting LINE Bot...")
    print(f"📡 Webhook URL: http://localhost:5001/callback")
    print(f"💚 Health Check: http://localhost:5001/health")
    app.run(debug=True, host='0.0.0.0', port=5001)

def run_both():
    """Run both web API and LINE bot"""
    import threading
    import time
    
    print("🚀 Starting both services...")
    
    # Start web API in a separate thread
    web_thread = threading.Thread(target=run_web_api, daemon=True)
    web_thread.start()
    
    # Give web API time to start
    time.sleep(2)
    
    # Start LINE bot in main thread
    run_line_bot()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = []
    
    # Check LINE Bot variables (optional)
    line_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    line_secret = os.environ.get('LINE_CHANNEL_SECRET')
    
    if not line_token or not line_secret:
        print("⚠️  LINE Bot variables not set (optional):")
        print("   LINE_CHANNEL_ACCESS_TOKEN")
        print("   LINE_CHANNEL_SECRET")
        print("   LINE Bot will run in demo mode\n")
    else:
        print("✅ LINE Bot environment variables configured")
    
    # Check OpenAI variables (optional)
    openai_key = os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        print("⚠️  OpenAI API key not set (optional):")
        print("   OPENAI_API_KEY")
        print("   Will use mock LLM for development\n")
    else:
        print("✅ OpenAI API key configured")
    
    # Check database variables
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("ℹ️  Using default SQLite database: storage/app.db")
    else:
        print("✅ Custom database URL configured")
    
    print()

def main():
    parser = argparse.ArgumentParser(description='Intelligent E-commerce Platform')
    parser.add_argument('--service', choices=['web', 'line', 'both'], default='web',
                       help='Service to run (default: web)')
    parser.add_argument('--init-db', action='store_true',
                       help='Initialize database before starting')
    parser.add_argument('--check-env', action='store_true',
                       help='Check environment variables and exit')
    
    args = parser.parse_args()
    
    # Check environment if requested
    if args.check_env:
        check_environment()
        return
    
    # Initialize database if requested
    if args.init_db:
        print("🗄️  Initializing database...")
        try:
            from .web_api import init_db
            init_db()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            return
    
    # Check environment
    check_environment()
    
    # Run selected service
    try:
        if args.service == 'web':
            run_web_api()
        elif args.service == 'line':
            run_line_bot()
        elif args.service == 'both':
            run_both()
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Service failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()