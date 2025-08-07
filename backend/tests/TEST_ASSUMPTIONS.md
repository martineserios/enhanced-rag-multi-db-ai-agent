# Test Assumptions and Hardcoded Values

This document outlines assumptions made and hardcoded values used within the test suite. The goal is to provide transparency regarding test design and to highlight areas where tests might be implicitly tied to specific configurations or behaviors.

## General Assumptions

*   **Environment Variables**: It is assumed that necessary environment variables (e.g., API keys for LLM providers) are either set or handled by the `TESTING=True` flag in the `Makefile` which provides dummy values.
*   **External Services Availability**: While mocks are used, the underlying structure and expected responses of external services (LLM APIs, databases) are assumed to be consistent with their real-world counterparts.

## Hardcoded Values and Specific Assumptions by Test File

### `tests/test_conversation_integration.py`

*   **`TestPerformanceIntegration.test_response_time_tracking`**:
    *   **Hardcoded Value**: `response_time_ms: 100` in the mocked `LLMResponse`. This value is hardcoded to ensure the assertion `data["response_time_ms"] > 0` passes, rather than reflecting an actual measured response time.
    *   **Assumption**: The `generate_medical_response` method of the `LLMProviderManager` is successfully mocked, and its return value directly influences the `response_time_ms` in the final API response.
    *   **Assumption**: The `client.post` call to `/api/v1/chat` will always return a `200 OK` status code under the mocked conditions.

### `tests/test_api_chat.py`

*   **Assumption**: The API endpoints defined in `app/api/endpoints/chat.py` are accessible at `/api/v1/chat` and `/api/v1/chat/health`.
*   **Hardcoded Values**:
    *   Test messages like `"Hello, how are you?"`, `"¿Cuáles son los efectos secundarios del Ozempic?"`, etc.
    *   Expected content in responses, e.g., `"Mocked medical response"`.
    *   Expected `session_id` and `language` values in API responses.

### `tests/test_llm_factory.py`

*   **Assumption**: The `get_settings()` function correctly provides configuration, including API keys (or dummy keys in testing).
*   **Assumption**: The `LLMProviderManager` correctly registers providers based on the presence of API keys.
*   **Hardcoded Values**:
    *   Specific `ModelCapability` values (e.g., `ModelCapability.MEDICAL_REASONING`, `ModelCapability.CLINICAL_CONVERSATION`).
    *   Expected number of providers registered when API keys are present.

### `tests/test_llm_providers.py`

*   **Assumption**: The external LLM libraries (`openai`, `anthropic`, `groq`) can be imported, or their import errors are handled gracefully.
*   **Hardcoded Values**:
    *   Dummy API keys used for initializing provider instances.
    *   Specific model names (e.g., `"gpt-4"`, `"claude-3-sonnet-20240229"`, `"llama-3.1-8b-instant"`).
    *   Hardcoded `temperature` and `max_tokens` values in `ModelConfig`.
    *   Specific `confidence_score` values for each provider in `_process_response`.
    *   Hardcoded `dangerous_patterns` and `disclaimer_patterns` in `_validate_medical_response`.

### `tests/test_medical_knowledge.py`

*   **Assumption**: The `MedicalKnowledgeBase` can load its data successfully.
*   **Hardcoded Values**:
    *   Specific knowledge base entries used for testing retrieval.
    *   Expected relevant knowledge based on query.

### `tests/test_patient_api.py`

*   **Assumption**: Patient API endpoints are accessible at `/api/v1/patients` with CRUD operations.
*   **Hardcoded Values**:
    *   Test patient data: `name: "Test Patient"`, `age: 30`, `gender: "male"`, `height_cm: 175.0`
    *   Sample patient ID: `"test_id"` used for testing retrieval operations
    *   Medical history condition: `"Hypertension"` with diagnosis date `"2020-01-01T00:00:00"`
    *   Treatment phase: `"initiation"` for patient creation tests
    *   Weight values: `initial_weight_kg: 80.0`, `current_weight_kg: 75.0` with update to `70.0`
*   **Assumption**: `PatientService` can be mocked and dependency-injected via FastAPI's dependency system.

### `tests/test_conversation_api.py`

*   **Assumption**: Conversation API endpoints are accessible at `/api/v1/chat` and related session endpoints.
*   **Hardcoded Values**:
    *   Test messages in Spanish: `"¿Cómo me inyecto Ozempic?"`, `"¿Y cuándo debo inyectarme?"`
    *   Test messages in English: `"How do I inject Ozempic?"`, `"What is Ozempic?"`
    *   Expected medical responses: `"Para inyectar Ozempic, consulte con su médico..."`, `"Continuando nuestra conversación anterior..."`
    *   Session IDs: `"test-session-123"`, `"existing-session-456"`, `"test-session-789"`
    *   Language codes: `"es"` (Spanish), `"en"` (English), `"fr"` (unsupported)
    *   Context timeout: `30` minutes for expiration testing
    *   Message limit: `10` messages maximum in conversation context
*   **Assumption**: `ConversationContext` class maintains message history with timestamps and role-based structure.
*   **Assumption**: Medical chat service can be mocked and provides health check functionality.

### `tests/test_chat_examples.py`

*   **Assumption**: Integration tests can run against live API endpoints or handle service unavailability gracefully.
*   **Hardcoded Values**:
    *   Spanish test query: `"¿Cuáles son los efectos secundarios de la semaglutida?"`
    *   English test query: `"How does GLP-1 medication work?"`
    *   Message length limit: `1000` characters maximum
    *   Expected error messages: `"Medical chat service unavailable"`, `"Unable to process medical query at this time"`
    *   Language validation: Only `['es', 'en']` supported
*   **Assumption**: Tests expect either `200 OK` for successful responses or `500` for service unavailability.
*   **Assumption**: Response structure includes `message`, `language`, `session_id`, `medical_disclaimer`, and `response_time_ms`.

---

**Note**: This document should be updated whenever new tests are added, existing tests are modified, or hardcoded values/assumptions change.
