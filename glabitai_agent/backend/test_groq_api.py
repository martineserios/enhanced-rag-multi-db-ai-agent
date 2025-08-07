#!/usr/bin/env python3
"""
Test script to verify Groq API configuration
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from app.core.llm_factory import create_groq_provider
from app.core.llm_providers import LLMRequest


async def test_groq_config():
    """Test Groq provider configuration and basic functionality."""
    
    print("🔍 Testing Groq Configuration...")
    
    # Test settings
    settings = get_settings()
    print(f"✅ Groq API Key configured: {'Yes' if settings.GROQ_API_KEY else 'No'}")
    print(f"✅ Groq Model: {settings.GROQ_MODEL}")
    
    # Test provider creation
    try:
        groq_provider = create_groq_provider()
        if groq_provider:
            print("✅ Groq provider created successfully")
            print(f"✅ Provider type: {groq_provider.provider_type.value}")
            
            # Test health check
            health = await groq_provider.health_check()
            print(f"✅ Health check: {health}")
            
            # Test basic API call (simple request)
            print("\n🧪 Testing basic Groq API call...")
            
            request = LLMRequest(
                messages=[{"role": "user", "content": "Say hello in Spanish"}],
                medical_context={
                    "patient_safety_level": "standard", 
                    "medical_domain": "test"
                }
            )
            
            response = await groq_provider.generate_response(request)
            print("✅ Response received:")
            print(f"   Content: {response.content[:100]}...")
            print(f"   Provider: {response.provider.value}")
            print(f"   Model: {response.model}")
            print(f"   Medical validated: {response.medical_validated}")
            
        else:
            print("❌ Failed to create Groq provider")
            
    except Exception as e:
        print(f"❌ Error testing Groq provider: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_groq_config())