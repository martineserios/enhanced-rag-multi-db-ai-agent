#!/usr/bin/env python3
"""
Test Data Population Script for GLP-1 Treatment Data

This script populates the MongoDB database with test data for the GLP-1 Treatment application.
It is designed to be idempotent and handle incremental data loading without creating duplicates.
"""

import os
import sys
import logging
import random
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
from bson.objectid import ObjectId
from faker import Faker
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Faker with Spanish locale (Spain) and Spanish text providers
fake = Faker('es_ES')
# Ensure all text is in Spanish
fake.add_provider('es_ES')

load_dotenv()

# MongoDB connection settings
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://glabitai:dev_password@mongodb:27017/')
DB_NAME = os.getenv('MONGO_DB', 'glabitai_glp1_clinical')

# Collection names
PATIENTS_COLLECTION = 'patients'
TREATMENTS_COLLECTION = 'treatments'
APPOINTMENTS_COLLECTION = 'appointments'
NOTES_COLLECTION = 'clinical_notes'

# Number of test records to generate for each collection
DEFAULT_BATCH_SIZE = 5
BATCH_SIZE = os.getenv('TEST_DATA_BATCH_SIZE', DEFAULT_BATCH_SIZE)


class TestDataGenerator:
    def __init__(self):
        """Inicializa el generador de datos de prueba con conexión a MongoDB."""
        logger.info(f"Inicializando TestDataGenerator con MONGO_URI: {MONGO_URI}, DB_NAME: {DB_NAME}")
        try:
            self.client = MongoClient(MONGO_URI)
            # Hacer ping al servidor para verificar la conexión
            self.client.admin.command('ping')
            logger.info("Conexión exitosa al servidor MongoDB.")
            self.db = self.client[DB_NAME]
            self._ensure_indexes()
            logger.info(f"Conectado a la base de datos MongoDB: {DB_NAME} e índices asegurados.")
        except OperationFailure as e:
            logger.error(f"Failed to connect to MongoDB (OperationFailure): {e.details}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB or ensure indexes: {e}")
            sys.exit(1)

    def _ensure_indexes(self):
        """Asegura que existan índices únicos para prevenir duplicados."""
        logger.info("Verificando índices para las colecciones...")
        try:
            # Patients collection indexes
            self.db[PATIENTS_COLLECTION].create_index(
                [("email", ASCENDING)],
                unique=True,
                partialFilterExpression={"email": {"$type": "string"}}
            )
            logger.info(f"Ensured unique index on 'email' for {PATIENTS_COLLECTION}.")
            self.db[PATIENTS_COLLECTION].create_index(
                [("national_id", ASCENDING)],
                unique=True,
                partialFilterExpression={"national_id": {"$type": "string"}}
            )
            logger.info(f"Ensured unique index on 'national_id' for {PATIENTS_COLLECTION}.")

            # Treatments collection indexes
            self.db[TREATMENTS_COLLECTION].create_index(
                [("patient_id", ASCENDING), ("medication_name", ASCENDING), ("start_date", ASCENDING)],
                unique=True
            )
            logger.info(f"Ensured unique index on ('patient_id', 'medication_name', 'start_date') for {TREATMENTS_COLLECTION}.")

            # Appointments collection indexes
            self.db[APPOINTMENTS_COLLECTION].create_index(
                [("patient_id", ASCENDING), ("scheduled_time", ASCENDING)],
                unique=True
            )
            logger.info(f"Ensured unique index on ('patient_id', 'scheduled_time') for {APPOINTMENTS_COLLECTION}.")
            logger.info("All index checks completed.")
        except Exception as e:
            logger.error(f"Error during index creation: {e}")
            raise

    def generate_patient_data(self, count=1):
        """Genera datos de prueba para pacientes."""
        logger.info(f"Iniciando generación de {count} registros de pacientes.")
        patients = []
        for i in range(count):
            try:
                patient = {
                    "first_name": fake.first_name(),
                    "last_name": fake.last_name(),
                    "email": f"usuario_{fake.unique.word()}_{random.randint(1000,9999)}@{fake.domain_name()}", # Asegurando emails únicos
                    "phone": fake.phone_number(),
                    "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%Y-%m-%d'),
                    "gender": random.choice(['masculino', 'femenino', 'otro']),
                    "address": {
                        "street": fake.street_address(),
                        "city": fake.city(),
                        "region": fake.region(),
                        "postal_code": fake.postcode(),  # Using Spanish postal codes
                        "country": 'ES'  # Setting country code to Spain
                    },
                    # DNI español (8 dígitos + letra de control)
                    "national_id": f"{random.randint(10_000_000, 99_999_999)}{'TRWAGMYFPDXBNJZSQVHLCKE'[random.randint(0, 22)]}", # DNI español
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                patients.append(patient)
                logger.debug(f"Generated patient record #{i+1} with email: {patient['email']}")
            except Exception as e: # Catching potential errors from Faker's unique provider if it runs out
                logger.warning(f"Could not generate unique data for patient #{i+1}: {e}. Skipping this record.")
                continue
        logger.info(f"Successfully generated {len(patients)} patient records.")
        return patients

    def generate_treatment_data(self, patient_ids, count_per_patient=1):
        """Genera datos de tratamiento para pacientes."""
        logger.info(f"Iniciando generación de datos de tratamiento para {len(patient_ids)} pacientes, con un objetivo de {count_per_patient} tratamientos por paciente.")
        treatments = []
        medications = [
            'Semaglutida', 'Liraglutida', 'Dulaglutida', 'Exenatida', 'Lixisenatida',
            'Tirzepatida', 'Albiglutida', 'Semaglutida Oral'
        ]
        
        for i, patient_id in enumerate(patient_ids):
            num_treatments_for_patient = random.randint(1, count_per_patient) # Vary number of treatments
            for j in range(num_treatments_for_patient):
                # Add variation to ensure unique start dates
                days_offset = random.randint(0, 30)  # Up to 1 month variation
                # Generate start_date as datetime
                start_date = fake.date_time_between(start_date='-1y', end_date='now') + timedelta(days=days_offset)
                # Ensure end_date is a datetime if it exists
                end_date = None
                if random.random() > 0.7:
                    # Generate end_date as datetime after start_date
                    end_date = fake.date_time_between(start_date=start_date, end_date='+1y')
                    # Ensure end_date is not the same as start_date
                    if end_date <= start_date:
                        end_date = start_date + timedelta(days=1)
                
                treatment = {
                    "patient_id": patient_id,
                    "medication_name": random.choice(medications),
                    "dosage": f"{random.choice([0.25, 0.5, 1.0, 1.7, 2.4])} mg",
                    "frequency": random.choice(['diario', 'semanal', 'quincenal', 'mensual']),
                    "start_date": start_date,
                    "end_date": end_date,
                    "prescribing_doctor": f"{'Dr.' if random.choice([True, False]) else 'Dra.'} {fake.last_name()}",
                    "notes": f"{fake.sentence()} (Generated at {datetime.utcnow().isoformat()})",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "batch_id": str(uuid.uuid4())[:8]  # Add a batch ID for tracking
                }
                treatments.append(treatment)
                logger.debug(f"Generated treatment record #{j+1} for patient ID: {patient_id}")
        logger.info(f"Successfully generated {len(treatments)} treatment records in total.")
        return treatments

    def generate_appointment_data(self, patient_ids, count_per_patient=1):
        """Genera datos de citas para pacientes."""
        logger.info(f"Iniciando generación de datos de citas para {len(patient_ids)} pacientes, con un objetivo de {count_per_patient} citas por paciente.")
        appointments = []
        appointment_types = [
            'Consulta Inicial', 'Seguimiento', 'Ajuste de Dosis',
            'Análisis Clínicos', 'Asesoría Nutricional', 'Control de Progreso'
        ]
        
        for i, patient_id in enumerate(patient_ids):
            num_appointments_for_patient = random.randint(1, count_per_patient)
            for j in range(num_appointments_for_patient):
                # Ensure we're using datetime objects throughout
                scheduled_time = fake.date_time_between(
                    start_date='-30d',
                    end_date='+60d',
                    tzinfo=None # Pymongo handles naive datetime as UTC by default
                )
                appointments.append({
                    "patient_id": patient_id,
                    "scheduled_time": scheduled_time,
                    "duration_minutes": random.choice([15, 30, 45, 60]),
                    "type": random.choice(appointment_types),
                    "status": random.choices(
                        ['programada', 'confirmada', 'completada', 'cancelada', 'reprogramada'],
                        weights=[30, 40, 20, 5, 5],
                        k=1
                    )[0],
                    "notas": fake.paragraph(nb_sentences=3, variable_nb_sentences=True, ext_word_list=[
                        'paciente', 'tratamiento', 'seguimiento', 'análisis', 'resultados',
                        'mejoría', 'síntomas', 'control', 'dosis', 'medicación',
                        'recomendaciones', 'próxima cita', 'evolución', 'constantes', 'prescripción'
                    ]),
                    "tipo_consulta": random.choice(['presencial', 'telemedicina']),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                logger.debug(f"Generated appointment record #{j+1} for patient ID: {patient_id}")
        logger.info(f"Successfully generated {len(appointments)} appointment records in total.")
        return appointments

    def generate_clinical_notes(self, patient_ids, count_per_patient=1):
        """Genera notas clínicas para pacientes con seguimiento de tratamiento GLP-1."""
        logger.info(f"Iniciando generación de notas clínicas para {len(patient_ids)} pacientes, con un objetivo de {count_per_patient} notas por paciente.")
        notes = []
        
        # Síntomas comunes relacionados con GLP-1
        sintomas = [
            "pérdida de apetito", "náuseas", "estreñimiento", "diarrea", "vómitos",
            "dolor abdominal", "fatiga", "acidez", "dolor de cabeza"
        ]
        
        respuestas_positivas = [
            "El paciente reporta una pérdida de peso significativa de {} kg desde la última visita.",
            "Meoría notable en los síntomas de {} reportados por el paciente.",
            "El paciente reporta mejor control de azúcar en sangre y menos antojos.",
            "El paciente indica que tolera bien la medicación con efectos secundarios mínimos.",
            "El paciente reporta mayores niveles de energía y mejor movilidad."
        ]
        
        preocupaciones = [
            "El paciente expresó preocupación por {}. Se brindó tranquilidad y educación.",
            "Se discutieron estrategias para manejar {} con el paciente.",
            "El paciente reporta {}. Se sugirieron modificaciones dietéticas y cambios en el estilo de vida.",
            "Se abordaron las dudas del paciente sobre {} y sus posibles efectos secundarios.",
            "El paciente mostró preocupación por {}. Se brindó asesoramiento adicional sobre la adherencia a la medicación."
        ]
        
        planes_tratamiento = [
            "Continuar con la dosis actual de {} ya que el paciente responde favorablemente.",
            "Dosis aumentada a {} debido a una respuesta limitada.",
            "Dosis reducida a {} debido a efectos secundarios de {}.",
            "Se cambió a {} ya que el paciente reportó respuesta inadecuada a la medicación anterior.",
            "Se agregó asesoramiento nutricional para abordar las preocupaciones sobre {}."
        ]
        
        medicamentos = ['Semaglutida', 'Liraglutida', 'Dulaglutida', 'Tirzepatida']
        
        for i, patient_id in enumerate(patient_ids):
            num_notes_for_patient = random.randint(1, count_per_patient)
            for j in range(num_notes_for_patient):
                note_date = fake.date_time_between(start_date='-1y', end_date='now')
                note_type = random.choices(
                    ['Nota de Evolución', 'Consulta', 'Seguimiento', 'Plan de Tratamiento', 'Evento Adverso'],
                    weights=[0.4, 0.3, 0.2, 0.08, 0.02],
                    k=1
                )[0]
                
                # Generar contenido de la nota según el tipo
                if note_type == 'Nota de Evolución':
                    contenido = random.choice(respuestas_positivas).format(random.choice(sintomas))
                    if random.random() > 0.7:  # 30% de probabilidad de agregar una preocupación
                        contenido += ' ' + random.choice(preocupaciones).format(random.choice(sintomas))
                elif note_type == 'Plan de Tratamiento':
                    medicamento = random.choice(medicamentos)
                    if 'dosis' in random.choice(planes_tratamiento):
                        contenido = random.choice(planes_tratamiento).format(
                            medicamento, 
                            random.choice(['0.5mg', '1.0mg', '1.7mg', '2.4mg']), 
                            random.choice(sintomas)
                        )
                    else:
                        contenido = random.choice(planes_tratamiento).format(medicamento, random.choice(sintomas))
                elif note_type == 'Evento Adverso':
                    sintoma = random.choice(sintomas)
                    contenido = f"El paciente reportó {sintoma}. "
                    contenido += random.choice([
                        "Se recomendó tomar con alimentos y aumentar la ingesta de líquidos.",
                        "Se sugirió medicación de venta libre para aliviar los síntomas.",
                        "Se indicó monitorear y regresar si los síntomas persisten.",
                        "Se ajustó la dosis y se pidió al paciente que monitoree mejoras."
                    ])
                else:  # Consulta o Seguimiento
                    contenido = random.choice([
                        f"Se discutió sobre {random.choice(['la dieta', 'ejercicio', 'adherencia a la medicación', 'manejo de síntomas'])} con el paciente.",
                        f"Se revisaron {random.choice(['análisis de sangre', 'registros de glucosa', 'diario de alimentos'])} con el paciente.",
                        f"Se abordaron las preguntas del paciente sobre {random.choice(['efectos secundarios', 'recomendaciones dietéticas', 'pautas de ejercicio'])}."
                    ])
                
                # Asegurar que el contenido no exceda los 500 caracteres
                if len(contenido) > 500:
                    contenido = contenido[:497] + '...'
                
                # Formato de la nota
                nota = {
                    'patient_id': patient_id,
                    'note_type': note_type,
                    'content': contenido,
                    'author': f"{'Dr.' if random.choice([True, False]) else 'Dra.'} {fake.last_name()}",
                    'created_at': note_date,
                    'updated_at': note_date
                }
                notes.append(nota)
                logger.debug(f"Generated {note_type} note #{j+1} for patient ID: {patient_id}")
        
        logger.info(f"Successfully generated {len(notes)} clinical note records in total.")
        return notes

    def insert_data(self, collection_name, data):
        """Insert data into the specified collection with duplicate handling."""
        if not data:
            logger.info(f"No data provided for insertion into {collection_name}. Skipping.")
            return 0
            
        logger.info(f"Starting insertion of {len(data)} documents into {collection_name}.")
        collection = self.db[collection_name]
        inserted_count = 0
        skipped_count = 0
        
        for i, item in enumerate(data):
            try:
                # Ensure timestamps (created_at, updated_at) are present
                item.setdefault('created_at', datetime.utcnow())
                item.setdefault('updated_at', datetime.utcnow())
                
                # Convert patient_id to ObjectId if it's a string and meant for linking
                if 'patient_id' in item and isinstance(item['patient_id'], str):
                    try:
                        item['patient_id'] = ObjectId(item['patient_id'])
                    except Exception:
                        logger.warning(f"Could not convert patient_id '{item['patient_id']}' to ObjectId for item in {collection_name}. Using as string.")

                result = collection.insert_one(item)
                if result.acknowledged:
                    inserted_count += 1
                    logger.debug(f"Successfully inserted document #{i+1} with ID: {result.inserted_id} into {collection_name}.")
            except DuplicateKeyError as e:
                skipped_count += 1
                logger.debug(f"Skipped duplicate document #{i+1} in {collection_name}. Details: {e.details}")
                continue
            except Exception as e:
                logger.error(f"Error inserting document #{i+1} into {collection_name}: {e}. Document: {item}")
                continue
        
        logger.info(f"Finished insertion for {collection_name}. Successfully inserted: {inserted_count}, Skipped due to duplicate: {skipped_count}.")
        return inserted_count

    def log_random_patient_ids(self, limit=5):
        """Log a sample of patient IDs from the database."""
        try:
            patients = list(self.db[PATIENTS_COLLECTION].aggregate([
                {'$sample': {'size': limit}},
                {'$project': {'_id': 1}}
            ]))
            
            if patients:
                patient_ids = [str(patient['_id']) for patient in patients]
                logger.info(f"Sample of {len(patient_ids)} patient IDs from database: {', '.join(patient_ids)}")
            else:
                logger.warning("No patients found in the database to sample IDs from")
                
        except Exception as e:
            logger.error(f"Error while sampling patient IDs: {str(e)}")
            
    def validate_data_loading(self):
        """Validate that data has been successfully loaded and can be retrieved."""
        logger.info("Starting data validation process...")
        validation_results = {
            'patients': {'count': 0, 'sample': None, 'error': None},
            'treatments': {'count': 0, 'sample': None, 'error': None},
            'appointments': {'count': 0, 'sample': None, 'error': None},
            'clinical_notes': {'count': 0, 'sample': None, 'error': None}
        }
        
        # Validate patients
        try:
            patients_cursor = self.db[PATIENTS_COLLECTION].find().limit(5)
            patients = list(patients_cursor)
            validation_results['patients']['count'] = len(patients)
            if patients:
                # Remove _id field for cleaner output
                patient = dict(patients[0])
                patient.pop('_id', None)
                validation_results['patients']['sample'] = patient
        except Exception as e:
            validation_results['patients']['error'] = str(e)
            
        # Validate treatments
        try:
            treatments_cursor = self.db[TREATMENTS_COLLECTION].find().limit(5)
            treatments = list(treatments_cursor)
            validation_results['treatments']['count'] = len(treatments)
            if treatments:
                treatment = dict(treatments[0])
                treatment.pop('_id', None)
                validation_results['treatments']['sample'] = treatment
        except Exception as e:
            validation_results['treatments']['error'] = str(e)
            
        # Validate appointments
        try:
            appointments_cursor = self.db[APPOINTMENTS_COLLECTION].find().limit(5)
            appointments = list(appointments_cursor)
            validation_results['appointments']['count'] = len(appointments)
            if appointments:
                appointment = dict(appointments[0])
                appointment.pop('_id', None)
                validation_results['appointments']['sample'] = appointment
        except Exception as e:
            validation_results['appointments']['error'] = str(e)
            
        # Validate clinical notes
        try:
            notes_cursor = self.db[NOTES_COLLECTION].find().limit(5)
            notes = list(notes_cursor)
            validation_results['clinical_notes']['count'] = len(notes)
            if notes:
                note = dict(notes[0])
                note.pop('_id', None)
                validation_results['clinical_notes']['sample'] = note
        except Exception as e:
            validation_results['clinical_notes']['error'] = str(e)
            
        # Log validation results
        logger.info("=== Data Validation Results ===")
        all_valid = True
        
        for collection, result in validation_results.items():
            if result.get('error'):
                logger.error(f"{collection.upper()} validation error: {result['error']}")
                all_valid = False
            else:
                logger.info(f"{collection.upper()}: Found {result['count']} documents")
                if result['count'] == 0:
                    logger.warning(f"No documents found in {collection} collection")
                    all_valid = False
                if result['sample']:
                    logger.debug(f"Sample {collection} document: {result['sample']}")
        
        if all_valid:
            logger.info("✅ All collections validated successfully with data")
        else:
            logger.warning("⚠️  Validation completed with warnings or errors")
            
        # Log sample patient IDs after validation
        logger.info("\n--- Sample Patient IDs ---")
        self.log_random_patient_ids(limit=5)
            
        return validation_results

    def clear_existing_data(self):
        """Clear existing test data from collections."""
        logger.info("Clearing existing test data...")
        try:
            self.db[PATIENTS_COLLECTION].drop()
            self.db[TREATMENTS_COLLECTION].drop()
            self.db[APPOINTMENTS_COLLECTION].drop()
            self.db[NOTES_COLLECTION].drop()
            logger.info("Successfully cleared all collections.")
            # Recreate indexes after dropping collections
            self._ensure_indexes()
        except Exception as e:
            logger.error(f"Error clearing collections: {e}")
            raise

    def populate_test_data(self, batch_size=DEFAULT_BATCH_SIZE, clear_existing=True):
        """Populate the database with test data.
        
        Args:
            batch_size: Number of new patients to generate
            clear_existing: If True, clears all existing data before populating
        """
        if clear_existing:
            self.clear_existing_data()
            
        logger.info(f"Starting test data population process (target batch size for new patients: {batch_size})")
        
        total_inserted_patients = 0
        total_inserted_treatments = 0
        total_inserted_appointments = 0
        total_inserted_notes = 0

        try:
            # Generate and insert patients
            logger.info("--- Generating Patient Data ---")
            patients_to_generate = self.generate_patient_data(count=batch_size)
            logger.info("--- Inserting Patient Data ---")
            inserted_patients_count = self.insert_data(PATIENTS_COLLECTION, patients_to_generate)
            total_inserted_patients += inserted_patients_count
            logger.info(f"Successfully inserted {inserted_patients_count} new patients in this batch.")
            
            # Get the IDs of ALL patients (including existing ones) to generate related data
            logger.info("Fetching all patient IDs from database for related data generation...")
            all_patient_docs = list(self.db[PATIENTS_COLLECTION].find({}, {'_id': 1}))
            patient_ids = [p['_id'] for p in all_patient_docs] # Using actual ObjectId
            logger.info(f"Fetched {len(patient_ids)} patient IDs. Sample IDs: {patient_ids[:3]}")

            if not patient_ids:
                logger.warning("No patient IDs found. Skipping generation of treatments, appointments, and notes.")
            else:
                # Generate and insert treatments for patients
                logger.info("--- Generating Treatment Data ---")
                treatments_to_generate = self.generate_treatment_data(
                    patient_ids=patient_ids, # Pass ObjectId list
                    count_per_patient=random.randint(1, 3) # 1-3 treatments per patient
                )
                
                if not treatments_to_generate:
                    logger.warning("No treatments were generated. This might be due to duplicate prevention.")
                else:
                    logger.info("--- Inserting Treatment Data ---")
                    inserted_treatments_count = self.insert_data(TREATMENTS_COLLECTION, treatments_to_generate)
                    total_inserted_treatments += inserted_treatments_count
                    logger.info(f"Successfully inserted {inserted_treatments_count} new treatments in this batch.")
                    
                    if inserted_treatments_count == 0 and treatments_to_generate:
                        logger.warning("No treatments were inserted. This might be due to duplicate prevention.")
                        logger.debug(f"Sample treatment that wasn't inserted: {treatments_to_generate[0]}")
            
                # Generate and insert appointments for patients
                logger.info("--- Generating Appointment Data ---")
                appointments_to_generate = self.generate_appointment_data(
                    patient_ids=patient_ids, # Pass ObjectId list
                    count_per_patient=random.randint(1, 3)  # 1-3 appointments per patient
                )
                logger.info("--- Inserting Appointment Data ---")
                inserted_appointments_count = self.insert_data(APPOINTMENTS_COLLECTION, appointments_to_generate)
                total_inserted_appointments += inserted_appointments_count
                logger.info(f"Successfully inserted {inserted_appointments_count} new appointments in this batch.")
            
                # Generate and insert clinical notes for patients
                logger.info("--- Generating Clinical Notes Data ---")
                notes_to_generate = self.generate_clinical_notes(
                    patient_ids=patient_ids, # Pass ObjectId list
                    count_per_patient=random.randint(1, 4)  # 1-4 notes per patient
                )
                logger.info("--- Inserting Clinical Notes Data ---")
                inserted_notes_count = self.insert_data(NOTES_COLLECTION, notes_to_generate)
                total_inserted_notes += inserted_notes_count
                logger.info(f"Successfully inserted {inserted_notes_count} new clinical notes in this batch.")
            
            total_inserted_overall = total_inserted_patients + total_inserted_treatments + total_inserted_appointments + total_inserted_notes
            logger.info(f"Test data population batch complete. Total new documents inserted in this run: {total_inserted_overall}")

            # Validation: Log current counts in DB
            logger.info("--- Current Database Collection Counts (Validation) ---")
            collections_to_check = [PATIENTS_COLLECTION, TREATMENTS_COLLECTION, APPOINTMENTS_COLLECTION, NOTES_COLLECTION]
            for coll_name in collections_to_check:
                try:
                    count = self.db[coll_name].count_documents({})
                    logger.info(f"Total documents in {coll_name}: {count}")
                except Exception as e:
                    logger.error(f"Could not retrieve count for {coll_name}: {e}")
            
            # Validate data loading
            validation_results = self.validate_data_loading()
            
            # Prepare results
            results = {
                'inserted': {
                    'patients': total_inserted_patients,
                    'treatments': total_inserted_treatments,
                    'appointments': total_inserted_appointments,
                    'clinical_notes': total_inserted_notes,
                    'total': total_inserted_overall
                },
                'validation': {
                    'patients_count': validation_results['patients']['count'],
                    'treatments_count': validation_results['treatments']['count'],
                    'appointments_count': validation_results['appointments']['count'],
                    'clinical_notes_count': validation_results['clinical_notes']['count']
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error during test data population: {e}", exc_info=True)
            raise


def main():
    """Main function to run the test data population."""
    logger.info("<<<<< Starting GLP-1 Test Data Population Script >>>>>")
    try:
        # Get batch size from environment variable or use default
        batch_size_str = os.getenv('BATCH_SIZE', str(DEFAULT_BATCH_SIZE))
        try:
            batch_size = int(batch_size_str)
            if batch_size <= 0:
                logger.warning(f"BATCH_SIZE must be positive. Got {batch_size}. Using default: {DEFAULT_BATCH_SIZE}")
                batch_size = DEFAULT_BATCH_SIZE
        except ValueError:
            logger.warning(f"Invalid BATCH_SIZE: '{batch_size_str}'. Using default: {DEFAULT_BATCH_SIZE}")
            batch_size = DEFAULT_BATCH_SIZE
        
        logger.info(f"Determined batch size for new patients: {batch_size}")
        
        generator = TestDataGenerator()
        logger.info("TestDataGenerator initialized successfully.")
        
        results = generator.populate_test_data(batch_size=batch_size)
        logger.info("populate_test_data method finished.")
        
        # Log insertion and validation summary
        inserted = results.get('inserted', {})
        validation = results.get('validation', {})
        
        logger.info("=== Test Data Population Summary ===")
        logger.info("--- Documents Inserted (This Run) ---")
        logger.info(f"Patients: {inserted.get('patients', 0)}")
        logger.info(f"Treatments: {inserted.get('treatments', 0)}")
        logger.info(f"Appointments: {inserted.get('appointments', 0)}")
        logger.info(f"Clinical Notes: {inserted.get('clinical_notes', 0)}")
        logger.info(f"Total: {inserted.get('total', 0)}")
        
        # Log validation summary
        logger.info("--- Database Validation Results ---")
        logger.info(f"Patients in DB: {validation.get('patients_count', 0)}")
        logger.info(f"Treatments in DB: {validation.get('treatments_count', 0)}")
        logger.info(f"Appointments in DB: {validation.get('appointments_count', 0)}")
        logger.info(f"Clinical Notes in DB: {validation.get('clinical_notes_count', 0)}")
        
        # Check if any collections are empty
        empty_collections = []
        for col, count in validation.items():
            if count == 0 and col.endswith('_count'):
                empty_collections.append(col.replace('_count', ''))
        
        if empty_collections:
            logger.warning(f"The following collections are empty: {', '.join(empty_collections)}")
        else:
            logger.info("All collections contain data.")
            
        logger.info("For detailed validation results and sample documents, check the debug logs.")
        logger.info("<<<<< GLP-1 Test Data Population Script Finished Successfully >>>>>")
        
        return 0
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}", exc_info=True)
        logger.info("<<<<< GLP-1 Test Data Population Script Finished With Errors >>>>>")
        return 1


if __name__ == "__main__":
    sys.exit(main())