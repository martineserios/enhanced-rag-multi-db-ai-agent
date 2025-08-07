from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import Depends
from datetime import datetime

from app.main import app
from app.models.patient import Patient, MedicalHistory, PatientUpdate
from app.api.endpoints.patient import get_patient_service
from app.services.patient_service import PatientService

client = TestClient(app)

@pytest.fixture
def mock_patient_service():
    with patch('app.services.patient_service.PatientService', autospec=True) as MockPatientService:
        mock_service = MockPatientService.return_value
        yield mock_service

@pytest.fixture(autouse=True)
def override_dependencies(mock_patient_service):
    app.dependency_overrides[get_patient_service] = lambda: mock_patient_service
    yield
    app.dependency_overrides = {}

@pytest.fixture(name="patient_data")
def patient_data_fixture():
    return {
        "name": "Test Patient",
        "age": 30,
        "gender": "male",
        "height_cm": 175.0,
        "initial_weight_kg": 80.0,
        "current_weight_kg": 75.0,
        "medical_history": [
            {"condition": "Hypertension", "diagnosis_date": "2020-01-01T00:00:00"}
        ],
        "treatment_phase": "initiation"
    }

@pytest.fixture
def sample_patient(patient_data):
    return Patient(
        id="test_id",
        name=patient_data["name"],
        age=patient_data["age"],
        gender=patient_data["gender"],
        height_cm=patient_data["height_cm"],
        initial_weight_kg=patient_data["initial_weight_kg"],
        current_weight_kg=patient_data["current_weight_kg"],
        medical_history=[MedicalHistory(**mh) for mh in patient_data["medical_history"]],
        treatment_phase=patient_data["treatment_phase"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

class TestPatientAPI:
    async def test_create_patient(self, mock_patient_service, patient_data, sample_patient):
        mock_patient_service.create_patient.side_effect = AsyncMock(return_value=sample_patient.model_dump(by_alias=True))
        
        response = client.post("/api/v1/patients", json=patient_data)
        assert response.status_code == 201
        created_patient = response.json()
        assert created_patient["name"] == patient_data["name"]
        assert created_patient["_id"] == "test_id"
        mock_patient_service.create_patient.assert_called_once()

    async def test_create_patient_duplicate_id(self, mock_patient_service, patient_data):
        mock_patient_service.create_patient.side_effect = ValueError("Patient with this ID already exists")
        
        response = client.post("/api/v1/patients", json=patient_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
        mock_patient_service.create_patient.assert_called_once()

    async def test_get_patient(self, mock_patient_service, sample_patient):
        mock_patient_service.get_patient.side_effect = AsyncMock(return_value=sample_patient.model_dump(by_alias=True))
        
        response = client.get("/api/v1/patients/test_id")
        assert response.status_code == 200
        retrieved_patient = response.json()
        assert retrieved_patient["name"] == sample_patient.name
        assert retrieved_patient["_id"] == sample_patient.id
        mock_patient_service.get_patient.assert_called_once_with("test_id")

    async def test_get_patient_not_found(self, mock_patient_service):
        mock_patient_service.get_patient.side_effect = AsyncMock(return_value=None)
        
        response = client.get("/api/v1/patients/non_existent_id")
        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]
        mock_patient_service.get_patient.assert_called_once_with("non_existent_id")

    async def test_update_patient(self, mock_patient_service, patient_data, sample_patient):
        updated_patient_data = sample_patient.model_copy(update={"current_weight_kg": 70.0})
        mock_patient_service.update_patient.side_effect = AsyncMock(return_value=updated_patient_data.model_dump(by_alias=True))
        
        update_data = {"current_weight_kg": 70.0}
        response = client.put("/api/v1/patients/test_id", json=update_data)
        assert response.status_code == 200
        updated_patient = response.json()
        assert updated_patient["current_weight_kg"] == 70.0
        mock_patient_service.update_patient.assert_called_once()

    async def test_update_patient_not_found(self, mock_patient_service):
        mock_patient_service.update_patient.side_effect = AsyncMock(return_value=None)
        
        update_data = {"current_weight_kg": 70.0}
        response = client.put("/api/v1/patients/non_existent_id", json=update_data)
        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]
        mock_patient_service.update_patient.assert_called_once()

    async def test_delete_patient(self, mock_patient_service):
        mock_patient_service.delete_patient.side_effect = AsyncMock(return_value=True)
        
        response = client.delete("/api/v1/patients/test_id")
        assert response.status_code == 204
        mock_patient_service.delete_patient.assert_called_once_with("test_id")

    async def test_delete_patient_not_found(self, mock_patient_service):
        mock_patient_service.delete_patient.side_effect = AsyncMock(return_value=False)
        
        response = client.delete("/api/v1/patients/non_existent_id")
        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]
        mock_patient_service.delete_patient.assert_called_once_with("non_existent_id")

    async def test_get_all_patients(self, mock_patient_service, sample_patient):
        mock_patient_service.get_all_patients.side_effect = AsyncMock(return_value=[
            sample_patient.model_copy(update={"id": "id1", "name": "Patient One"}).model_dump(by_alias=True),
            sample_patient.model_copy(update={"id": "id2", "name": "Patient Two"}).model_dump(by_alias=True)
        ])
        
        response = client.get("/api/v1/patients")
        assert response.status_code == 200
        patients = response.json()
        assert len(patients) == 2
        assert patients[0]["name"] == "Patient One"
        assert patients[1]["name"] == "Patient Two"
        mock_patient_service.get_all_patients.assert_called_once()
