"""
Test script for the Clinical Agent and its medication lookup tool.
"""
import asyncio
import logging
from app.config import get_settings
from app.services.agents.clinical_agent.service import ClinicalAgent
from app.services.agents.clinical_agent.tools import MedicationLookupTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_medication_lookup():
    """Test the medication lookup tool directly."""
    logger.info("Testing MedicationLookupTool...")
    
    # Create an instance of the tool
    tool = MedicationLookupTool()
    
    # Test with a known medication
    result = tool._run("paracetamol", language="es")
    logger.info(f"Medication lookup result for 'paracetamol':\n{result}")
    
    # Test with an unknown medication
    result = tool._run("unknown_med", language="es")
    logger.info(f"Medication lookup result for 'unknown_med':\n{result}")

async def test_clinical_agent():
    """Test the clinical agent with medication-related queries."""
    logger.info("Testing ClinicalAgent...")
    
    # Initialize the agent
    settings = get_settings()
    agent = ClinicalAgent(settings)
    
    # Test with a medication query
    test_queries = [
        "¿Qué sabes sobre el paracetamol?",
        "Dime sobre el ibuprofeno",
        "No tengo información sobre este medicamento"
    ]
    
    for query in test_queries:
        logger.info(f"\nTesting query: {query}")
        response = await agent.process_chat_request(
            chat_request={"message": query, "conversation_id": "test_conv_123"},
            provider="groq"  # or any other supported provider
        )
        logger.info(f"Agent response: {response}")

if __name__ == "__main__":
    # Run the tests
    logger.info("Starting Clinical Agent tests...")
    
    # Test the tool directly
    asyncio.run(test_medication_lookup())
    
    # Test the full agent (uncomment to test)
    # asyncio.run(test_clinical_agent())
    
    logger.info("Tests completed.")
