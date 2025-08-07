#!/usr/bin/env python3
"""
GlabitAI Backend Server Launcher

Convenient script to start the medical AI backend server
with proper configuration and environment setup.
"""

import sys
import subprocess
from pathlib import Path


def check_environment():
    """Check if environment is properly configured."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📋 Please copy .env.example to .env and configure your API keys:")
        print("   cp .env.example .env")
        print("   # Edit .env and add your OPENAI_API_KEY")
        return False
    
    # Check if OpenAI API key is configured
    from app.core.config import get_settings
    try:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            print("⚠️  OpenAI API key not configured!")
            print("📝 Please add your OpenAI API key to .env file:")
            print("   OPENAI_API_KEY=sk-your-openai-api-key-here")
            print("🔄 The server will start but medical AI features will be limited.")
        else:
            print("✅ OpenAI API key configured")
    except Exception as e:
        print(f"⚠️  Configuration error: {e}")
    
    return True


def create_logs_directory():
    """Create logs directory if it doesn't exist."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
        print("📁 Created logs directory")


def main():
    """Main server launcher."""
    print("🏥 GlabitAI Medical Backend - MVP 1")
    print("=" * 50)
    
    # Check environment setup
    if not check_environment():
        sys.exit(1)
    
    # Create logs directory
    create_logs_directory()
    
    # Get command line arguments for uvicorn
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Default uvicorn configuration
    uvicorn_args = [
        "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--log-level", "info"
    ]
    
    # Add any additional arguments
    uvicorn_args.extend(args)
    
    print("🚀 Starting GlabitAI Medical Backend...")
    print("📡 Server will be available at: http://localhost:8000")
    print("📖 API documentation: http://localhost:8000/docs")
    print("❤️  Health check: http://localhost:8000/health")
    print()
    print("💬 Test the medical chat API:")
    print('curl -X POST http://localhost:8000/api/v1/chat \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"message": "¿Cuáles son los efectos secundarios del Ozempic?", "language": "es"}\'')
    print()
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start the server
    try:
        subprocess.run(uvicorn_args)
    except KeyboardInterrupt:
        print("\n👋 GlabitAI Backend stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()