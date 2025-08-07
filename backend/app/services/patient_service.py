from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import logging

from app.db.mongodb import get_mongo_client
from app.models.patient import Patient, PatientUpdate

logger = logging.getLogger(__name__)

class PatientService:
    def __init__(self):
        self.client: AsyncIOMotorClient = get_mongo_client()
        self.db = self.client.glabitai_db
        self.patients_collection = self.db.patients
        
    async def create_patient(self, patient: Patient) -> Patient:
        try:
            result = await self.patients_collection.insert_one(patient.model_dump(by_alias=True))
            patient.id = str(result.inserted_id)
            logger.info(f"Patient created with ID: {patient.id}")
            return patient
        except DuplicateKeyError:
            logger.error(f"Patient with ID {patient.id} already exists.")
            raise ValueError(f"Patient with ID {patient.id} already exists.")
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating patient: {e}")
            raise

    async def get_patient(self, patient_id: str) -> Optional[Patient]:
        try:
            patient_data = await self.patients_collection.find_one({"_id": patient_id})
            if patient_data:
                return Patient(**patient_data)
            return None
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting patient {patient_id}: {e}")
            raise

    async def update_patient(self, patient_id: str, patient_update: PatientUpdate) -> Optional[Patient]:
        try:
            update_data = patient_update.model_dump(by_alias=True, exclude_unset=True)
            if not update_data:
                return await self.get_patient(patient_id) # No updates provided

            result = await self.patients_collection.update_one(
                {"_id": patient_id},
                {"$set": update_data}
            )
            if result.modified_count == 1:
                logger.info(f"Patient {patient_id} updated.")
                return await self.get_patient(patient_id)
            return None
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating patient {patient_id}: {e}")
            raise

    async def delete_patient(self, patient_id: str) -> bool:
        try:
            result = await self.patients_collection.delete_one({"_id": patient_id})
            if result.deleted_count == 1:
                logger.info(f"Patient {patient_id} deleted.")
                return True
            return False
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting patient {patient_id}: {e}")
            raise

    async def get_all_patients(self, skip: int = 0, limit: int = 100) -> List[Patient]:
        try:
            patients = []
            cursor = self.patients_collection.find().skip(skip).limit(limit)
            async for patient_data in cursor:
                patients.append(Patient(**patient_data))
            return patients
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting all patients: {e}")
            raise
