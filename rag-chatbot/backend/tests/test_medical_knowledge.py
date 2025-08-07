"""
Tests for Medical Knowledge Base

Tests the medical knowledge retrieval and accuracy
for obesity treatment information.
"""

import pytest
from app.services.medical_knowledge import MedicalKnowledgeBase


class TestMedicalKnowledgeBase:
    """Test cases for medical knowledge base."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.kb = MedicalKnowledgeBase()
    
    def test_knowledge_base_loaded(self):
        """Test that knowledge base loads successfully."""
        assert self.kb.is_loaded()
        assert len(self.kb.knowledge_es) > 0
        assert len(self.kb.knowledge_en) > 0
    
    def test_get_relevant_knowledge_spanish(self):
        """Test knowledge retrieval in Spanish."""
        results = self.kb.get_relevant_knowledge("náuseas", language="es")
        
        assert len(results) > 0
        # Should find side effects information
        assert any("náuseas" in item["content"].lower() for item in results)
    
    def test_get_relevant_knowledge_english(self):
        """Test knowledge retrieval in English."""
        results = self.kb.get_relevant_knowledge("nausea", language="en")
        
        assert len(results) > 0
        # Should find side effects information
        assert any("nausea" in item["content"].lower() for item in results)
    
    def test_injection_technique_query(self):
        """Test injection technique queries."""
        # Spanish
        results_es = self.kb.get_relevant_knowledge("inyección", language="es")
        assert len(results_es) > 0
        assert any("inyección" in item["content"].lower() for item in results_es)
        
        # English
        results_en = self.kb.get_relevant_knowledge("injection", language="en")
        assert len(results_en) > 0
        assert any("injection" in item["content"].lower() for item in results_en)
    
    def test_emergency_knowledge(self):
        """Test emergency medical knowledge retrieval."""
        # Spanish
        emergency_es = self.kb.get_emergency_knowledge(language="es")
        assert len(emergency_es) > 0
        
        # English
        emergency_en = self.kb.get_emergency_knowledge(language="en")
        assert len(emergency_en) > 0
    
    def test_weight_loss_expectations(self):
        """Test weight loss information queries."""
        results = self.kb.get_relevant_knowledge("pérdida de peso", language="es")
        assert len(results) > 0
        
        # Should contain realistic expectations
        content = " ".join(item["content"] for item in results).lower()
        assert "5-15%" in content or "gradual" in content
    
    def test_knowledge_categories(self):
        """Test knowledge categorization."""
        stats = self.kb.get_stats()
        
        assert "categories_es" in stats
        assert "categories_en" in stats
        assert len(stats["categories_es"]) > 0
        assert len(stats["categories_en"]) > 0
    
    def test_max_results_limit(self):
        """Test that max_results parameter is respected."""
        results = self.kb.get_relevant_knowledge("ozempic", language="es", max_results=3)
        assert len(results) <= 3
    
    def test_no_results_for_irrelevant_query(self):
        """Test handling of irrelevant queries."""
        results = self.kb.get_relevant_knowledge("astronauts on mars", language="es")
        assert len(results) == 0
    
    @pytest.mark.medical
    def test_medical_accuracy_spanish(self):
        """Test medical accuracy of Spanish content."""
        # Test that serious side effects are properly categorized
        emergency_items = self.kb.get_emergency_knowledge(language="es")
        
        for item in emergency_items:
            content = item["content"].lower()
            # Should mention seeking medical attention
            assert ("médica" in content or "doctor" in content or 
                   "atención" in content or "consulte" in content)
    
    @pytest.mark.medical  
    def test_medical_accuracy_english(self):
        """Test medical accuracy of English content."""
        # Test that serious side effects are properly categorized
        emergency_items = self.kb.get_emergency_knowledge(language="en")
        
        for item in emergency_items:
            content = item["content"].lower()
            # Should mention seeking medical attention
            assert ("medical" in content or "doctor" in content or 
                   "attention" in content or "consult" in content)