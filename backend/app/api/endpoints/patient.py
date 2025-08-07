from fastapi import APIRouter, HTTPException, status, Body, Depends
from typing import List

from app.models.patient import Patient, PatientUpdate
from app.services.patient_service import PatientService

router = APIRouter()

async def get_patient_service():
    return PatientService()

@router.post("/patients", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: Patient = Body(...), patient_service: PatientService = Depends(get_patient_service)):
    """Create a new patient record."""
    try:
        created_patient = await patient_service.create_patient(patient)
        return created_patient
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create patient: {e}")

@router.get("/patients/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str, patient_service: PatientService = Depends(get_patient_service)):
    """Retrieve a single patient record by ID."""
    patient = await patient_service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient

@router.put("/patients/{patient_id}", response_model=Patient)
async def update_patient(patient_id: str, patient_update: PatientUpdate = Body(...), patient_service: PatientService = Depends(get_patient_service)):
    """Update an existing patient record."""
    updated_patient = await patient_service.update_patient(patient_id, patient_update)
    if not updated_patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or no changes applied")
    return updated_patient

@router.delete("/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: str, patient_service: PatientService = Depends(get_patient_service)):
    """Delete a patient record by ID."""
    if not await patient_service.delete_patient(patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

@router.get("/patients", response_model=List[Patient])
async def get_all_patients(skip: int = 0, limit: int = 100, patient_service: PatientService = Depends(get_patient_service)):
    """Retrieve all patient records with pagination."""
    return await patient_service.get_all_patients(skip=skip, limit=limit)
