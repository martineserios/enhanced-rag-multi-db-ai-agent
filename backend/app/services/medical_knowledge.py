"""
Medical Knowledge Base for Obesity Treatment

Static knowledge base containing GLP-1 treatment information,
side effects, injection techniques, and medical protocols.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class MedicalKnowledgeBase:
    """Medical knowledge base for obesity treatment with GLP-1."""
    
    def __init__(self):
        self.knowledge_es: List[Dict[str, str]] = []
        self.knowledge_en: List[Dict[str, str]] = []
        self._load_knowledge()
    
    def _load_knowledge(self):
        """Load medical knowledge in both languages."""
        
        # Spanish medical knowledge
        self.knowledge_es = [
            {
                "id": "glp1_basics_es",
                "title": "¿Qué es Ozempic (Semaglutide)?",
                "category": "medicamento",
                "content": "Ozempic (semaglutide) es un medicamento GLP-1 que ayuda a controlar la diabetes tipo 2 y facilita la pérdida de peso. Funciona imitando una hormona natural que regula el azúcar en sangre y ralentiza el vaciado gástrico, lo que ayuda a sentirse satisfecho por más tiempo."
            },
            {
                "id": "injection_technique_es",
                "title": "Técnica de inyección de Ozempic",
                "category": "administracion",
                "content": "Inyecte Ozempic subcutáneamente en el muslo, abdomen o brazo superior. Rote los sitios de inyección. Limpie el área con alcohol. Inserte la aguja a 90 grados, inyecte lentamente y mantenga presionado 6 segundos antes de retirar. Use una aguja nueva cada vez."
            },
            {
                "id": "common_side_effects_es", 
                "title": "Efectos secundarios comunes",
                "category": "efectos_secundarios",
                "content": "Los efectos secundarios más comunes incluyen náuseas (especialmente las primeras semanas), vómitos, diarrea, estreñimiento, dolor abdominal y fatiga. Estos suelen mejorar después de 4-8 semanas. Coma porciones más pequeñas y evite alimentos grasos para reducir las náuseas."
            },
            {
                "id": "serious_side_effects_es",
                "title": "Efectos secundarios graves - Busque atención médica",
                "category": "emergencia",
                "content": "Busque atención médica inmediata si experimenta: pancreatitis (dolor abdominal severo), síntomas de tiroides (bulto en el cuello), reacciones alérgicas graves, problemas renales, o problemas de vesícula biliar. También si tiene náuseas/vómitos severos que impiden mantener líquidos."
            },
            {
                "id": "weight_loss_expectations_es",
                "title": "Expectativas de pérdida de peso",
                "category": "resultados",
                "content": "La pérdida de peso con Ozempic es gradual. Puede esperar perder 5-15% de su peso corporal durante 6-12 meses. La pérdida de peso más rápida ocurre en los primeros 3-6 meses. Una pérdida de 0.5-1 kg por semana es normal y saludable."
            },
            {
                "id": "diet_recommendations_es",
                "title": "Recomendaciones dietéticas con Ozempic",
                "category": "nutricion", 
                "content": "Coma porciones más pequeñas y mastique lentamente. Enfóquese en proteínas magras, vegetales y carbohidratos complejos. Evite alimentos muy grasos, picantes o dulces que pueden empeorar las náuseas. Manténgase hidratado bebiendo agua regularmente."
            },
            {
                "id": "missed_dose_es",
                "title": "¿Qué hacer si olvida una dosis?",
                "category": "administracion",
                "content": "Si olvida una dosis y han pasado menos de 5 días, inyéctese tan pronto como recuerde. Si han pasado más de 5 días, omita la dosis olvidada y continúe con su horario regular. Nunca se inyecte dos dosis al mismo tiempo."
            },
            {
                "id": "exercise_recommendations_es",
                "title": "Ejercicio durante el tratamiento",
                "category": "ejercicio",
                "content": "El ejercicio regular mejora los resultados del tratamiento. Comience gradualmente con caminatas de 15-30 minutos. Incluya ejercicios de resistencia 2-3 veces por semana para mantener masa muscular durante la pérdida de peso. Consulte con su médico antes de comenzar un programa de ejercicios intenso."
            }
        ]
        
        # English medical knowledge
        self.knowledge_en = [
            {
                "id": "glp1_basics_en",
                "title": "What is Ozempic (Semaglutide)?",
                "category": "medication",
                "content": "Ozempic (semaglutide) is a GLP-1 medication that helps control type 2 diabetes and facilitates weight loss. It works by mimicking a natural hormone that regulates blood sugar and slows gastric emptying, helping you feel satisfied longer."
            },
            {
                "id": "injection_technique_en",
                "title": "Ozempic injection technique",
                "category": "administration",
                "content": "Inject Ozempic subcutaneously in thigh, abdomen, or upper arm. Rotate injection sites. Clean area with alcohol. Insert needle at 90 degrees, inject slowly and hold for 6 seconds before removing. Use a new needle each time."
            },
            {
                "id": "common_side_effects_en",
                "title": "Common side effects",
                "category": "side_effects",
                "content": "Most common side effects include nausea (especially first weeks), vomiting, diarrhea, constipation, abdominal pain, and fatigue. These usually improve after 4-8 weeks. Eat smaller portions and avoid fatty foods to reduce nausea."
            },
            {
                "id": "serious_side_effects_en",
                "title": "Serious side effects - Seek medical attention",
                "category": "emergency",
                "content": "Seek immediate medical attention if you experience: pancreatitis (severe abdominal pain), thyroid symptoms (neck lump), severe allergic reactions, kidney problems, or gallbladder issues. Also if you have severe nausea/vomiting preventing fluid retention."
            },
            {
                "id": "weight_loss_expectations_en",
                "title": "Weight loss expectations",
                "category": "results",
                "content": "Weight loss with Ozempic is gradual. You can expect to lose 5-15% of your body weight over 6-12 months. Fastest weight loss occurs in the first 3-6 months. A loss of 0.5-1 kg per week is normal and healthy."
            },
            {
                "id": "diet_recommendations_en",
                "title": "Dietary recommendations with Ozempic",
                "category": "nutrition",
                "content": "Eat smaller portions and chew slowly. Focus on lean proteins, vegetables, and complex carbohydrates. Avoid very fatty, spicy, or sweet foods that may worsen nausea. Stay hydrated by drinking water regularly."
            },
            {
                "id": "missed_dose_en",
                "title": "What to do if you miss a dose?",
                "category": "administration",
                "content": "If you miss a dose and less than 5 days have passed, inject as soon as you remember. If more than 5 days have passed, skip the missed dose and continue with your regular schedule. Never inject two doses at the same time."
            },
            {
                "id": "exercise_recommendations_en",
                "title": "Exercise during treatment",
                "category": "exercise",
                "content": "Regular exercise improves treatment outcomes. Start gradually with 15-30 minute walks. Include resistance exercises 2-3 times per week to maintain muscle mass during weight loss. Consult your doctor before starting an intense exercise program."
            }
        ]
        
        logger.info(f"Loaded {len(self.knowledge_es)} Spanish and {len(self.knowledge_en)} English knowledge items")
    
    def get_relevant_knowledge(self, query: str, language: str = "es", max_results: int = 5) -> List[Dict[str, str]]:
        """
        Get relevant knowledge based on query.
        
        Simple keyword matching for MVP 1.
        In future versions, this will use vector similarity.
        """
        knowledge_base = self.knowledge_es if language == "es" else self.knowledge_en
        query_lower = query.lower()
        
        # Score each knowledge item based on keyword matches
        scored_items = []
        
        for item in knowledge_base:
            score = 0
            item_text = (item["title"] + " " + item["content"]).lower()
            
            # Simple keyword scoring
            keywords = {
                # Spanish keywords
                "náuseas": ["nausea", "náuseas", "vomit", "vómito"],
                "inyección": ["inyección", "injection", "inject", "inyectar"],
                "dosis": ["dosis", "dose", "missed", "olvida"],
                "efectos": ["efectos", "effects", "side", "secundarios"],
                "peso": ["peso", "weight", "loss", "pérdida"],
                "ozempic": ["ozempic", "semaglutide"],
                "ejercicio": ["ejercicio", "exercise", "physical"],
                "dieta": ["dieta", "diet", "food", "comida"],
                "dolor": ["dolor", "pain", "abdominal"],
                
                # English keywords  
                "nausea": ["nausea", "náuseas", "vomit", "vómito"],
                "injection": ["inyección", "injection", "inject", "inyectar"],
                "dose": ["dosis", "dose", "missed", "olvida"],
                "effects": ["efectos", "effects", "side", "secundarios"],
                "weight": ["peso", "weight", "loss", "pérdida"],
                "exercise": ["ejercicio", "exercise", "physical"],
                "diet": ["dieta", "diet", "food", "comida"],
                "pain": ["dolor", "pain", "abdominal"]
            }
            
            # Check for keyword matches
            for keyword, variations in keywords.items():
                for variation in variations:
                    if variation in query_lower:
                        if variation in item_text:
                            score += 2
                        elif keyword in item_text:
                            score += 1
            
            # Boost emergency-related content
            if "emergency" in item.get("category", "") or "emergencia" in item.get("category", ""):
                emergency_keywords = ["severe", "severo", "grave", "emergency", "emergencia", "inmediata"]
                if any(word in query_lower for word in emergency_keywords):
                    score += 5
            
            if score > 0:
                scored_items.append((score, item))
        
        # Sort by score and return top results
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_items[:max_results]]
    
    def get_knowledge_by_category(self, category: str, language: str = "es") -> List[Dict[str, str]]:
        """Get all knowledge items for a specific category."""
        knowledge_base = self.knowledge_es if language == "es" else self.knowledge_en
        return [item for item in knowledge_base if item.get("category") == category]
    
    def get_emergency_knowledge(self, language: str = "es") -> List[Dict[str, str]]:
        """Get emergency/serious medical information."""
        return self.get_knowledge_by_category("emergency" if language == "en" else "emergencia", language)
    
    def is_loaded(self) -> bool:
        """Check if knowledge base is loaded."""
        return len(self.knowledge_es) > 0 and len(self.knowledge_en) > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return {
            "spanish_items": len(self.knowledge_es),
            "english_items": len(self.knowledge_en),
            "categories_es": list(set(item.get("category", "unknown") for item in self.knowledge_es)),
            "categories_en": list(set(item.get("category", "unknown") for item in self.knowledge_en)),
            "loaded": self.is_loaded()
        }