from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import uuid

class MedicalHistory(BaseModel):
    condition: str
    diagnosis_date: Optional[datetime] = None
    notes: Optional[str] = None

class Patient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    name: str
    age: int
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    initial_weight_kg: Optional[float] = None
    current_weight_kg: Optional[float] = None
    medical_history: List[MedicalHistory] = []
    treatment_phase: str = "pre_treatment"  # e.g., pre_treatment, initiation, adaptation, maintenance, withdrawal
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "Maria Rodriguez",
                "age": 45,
                "gender": "female",
                "height_cm": 165.5,
                "initial_weight_kg": 85.2,
                "current_weight_kg": 80.1,
                "medical_history": [
                    {"condition": "Type 2 Diabetes", "diagnosis_date": "2020-01-15"},
                    {"condition": "Hypertension"}
                ],
                "treatment_phase": "maintenance"
            }
        }
    )

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    current_weight_kg: Optional[float] = None
    medical_history: Optional[List[MedicalHistory]] = None
    treatment_phase: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)
